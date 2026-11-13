from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from webapp import community_app


class _Reservation:
    def __init__(self) -> None:
        self.released = False

    def release(self) -> None:
        self.released = True


def _scope(headers: list[tuple[bytes, bytes]] | None = None) -> dict:
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/analyze",
        "raw_path": b"/analyze",
        "query_string": b"",
        "headers": headers or [],
        "client": ("testclient", 123),
        "server": ("testserver", 80),
    }


def _status(messages: list[dict]) -> int:
    return next(
        message["status"]
        for message in messages
        if message["type"] == "http.response.start"
    )


def test_full_capacity_rejects_before_consuming_multipart_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject():
        raise community_app.community_service.JobCapacityError(
            "The analyzer is at capacity."
        )

    monkeypatch.setattr(community_app.community_service, "reserve_job_slot", reject)
    app_called = False
    receive_calls = 0
    sent: list[dict] = []

    async def app(_scope, _receive, _send):
        nonlocal app_called
        app_called = True

    async def receive():
        nonlocal receive_calls
        receive_calls += 1
        return {"type": "http.request", "body": b"large upload", "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(
        community_app.AnalyzeAdmissionMiddleware(app, max_body_bytes=8)(
            _scope(), receive, send
        )
    )

    assert _status(sent) == 429
    response_headers = dict(
        next(m for m in sent if m["type"] == "http.response.start")["headers"]
    )
    assert response_headers[b"retry-after"] == b"60"
    assert receive_calls == 0
    assert app_called is False


def test_cors_wraps_preparse_admission_rejections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject():
        raise community_app.community_service.JobCapacityError(
            "The analyzer is at capacity."
        )

    monkeypatch.setattr(community_app.community_service, "reserve_job_slot", reject)

    probe_app = community_app.FastAPI()
    probe_app.add_middleware(community_app.AnalyzeAdmissionMiddleware)
    probe_app.add_middleware(
        community_app.CORSMiddleware,
        allow_origins=community_app.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )

    @probe_app.post("/analyze")
    async def unexpected_route():
        pytest.fail(
            "capacity rejection must happen before the request reaches FastAPI"
        )

    with TestClient(probe_app) as client:
        response = client.post(
            "/analyze",
            content=b"not a valid multipart body",
            headers={
                "Content-Type": "multipart/form-data; boundary=missing",
                "Origin": community_app.PUBLIC_SITE_ORIGIN,
            },
        )

    assert response.status_code == 429, response.text
    assert response.headers["Retry-After"] == "60"
    assert response.headers["Access-Control-Allow-Origin"] in {
        "*",
        community_app.PUBLIC_SITE_ORIGIN,
    }
    middleware_classes = [item.cls for item in community_app.app.user_middleware]
    assert (
        middleware_classes.index(community_app.CORSMiddleware)
        < middleware_classes.index(community_app.AnalyzeAdmissionMiddleware)
    )

def test_content_length_limit_rejects_before_reserving_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reservation = _Reservation()
    reserve_called = False

    def reserve():
        nonlocal reserve_called
        reserve_called = True
        return reservation

    monkeypatch.setattr(
        community_app.community_service,
        "reserve_job_slot",
        reserve,
    )
    app_called = False
    receive_calls = 0
    sent: list[dict] = []

    async def app(_scope, _receive, _send):
        nonlocal app_called
        app_called = True

    async def receive():
        nonlocal receive_calls
        receive_calls += 1
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(
        community_app.AnalyzeAdmissionMiddleware(app, max_body_bytes=8)(
            _scope([(b"content-length", b"9")]), receive, send
        )
    )

    assert _status(sent) == 413
    assert receive_calls == 0
    assert app_called is False
    assert reserve_called is False
    assert reservation.released is False


def test_unreasonably_long_content_length_is_rejected_before_reserving_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reserve_called = False

    def reserve():
        nonlocal reserve_called
        reserve_called = True
        return _Reservation()

    monkeypatch.setattr(
        community_app.community_service,
        "reserve_job_slot",
        reserve,
    )
    app_called = False
    receive_calls = 0
    sent: list[dict] = []

    async def app(_scope, _receive, _send):
        nonlocal app_called
        app_called = True

    async def receive():
        nonlocal receive_calls
        receive_calls += 1
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(
        community_app.AnalyzeAdmissionMiddleware(app, max_body_bytes=8)(
            _scope([(b"content-length", b"9" * 5000)]), receive, send
        )
    )

    assert _status(sent) in {400, 413}
    assert receive_calls == 0
    assert app_called is False
    assert reserve_called is False


def test_streaming_limit_rejects_chunked_body_and_releases_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reservation = _Reservation()
    monkeypatch.setattr(
        community_app.community_service,
        "reserve_job_slot",
        lambda: reservation,
    )
    chunks = [
        {"type": "http.request", "body": b"1234", "more_body": True},
        {"type": "http.request", "body": b"56789", "more_body": True},
    ]
    consumed: list[bytes] = []
    sent: list[dict] = []

    async def receive():
        if chunks:
            return chunks.pop(0)
        return {"type": "http.disconnect"}

    async def app(_scope, inner_receive, inner_send):
        while True:
            message = await inner_receive()
            if message["type"] == "http.disconnect":
                break
            consumed.append(message.get("body", b""))
            if not message.get("more_body"):
                break
        await inner_send(
            {"type": "http.response.start", "status": 200, "headers": []}
        )
        await inner_send({"type": "http.response.body", "body": b"unexpected"})

    async def send(message):
        sent.append(message)

    asyncio.run(
        community_app.AnalyzeAdmissionMiddleware(app, max_body_bytes=8)(
            _scope(), receive, send
        )
    )

    assert _status(sent) == 413
    assert consumed == [b"1234"]
    assert reservation.released is True
    assert not any(
        message.get("status") == 200 for message in sent
    )


def test_worker_ownership_transfers_reservation_past_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reservation = _Reservation()
    monkeypatch.setattr(
        community_app.community_service,
        "reserve_job_slot",
        lambda: reservation,
    )
    sent: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": b"ok", "more_body": False}

    async def app(scope, inner_receive, inner_send):
        message = await inner_receive()
        assert message["body"] == b"ok"
        scope["state"]["bionuclei_job_slot_transferred"] = True
        await inner_send(
            {"type": "http.response.start", "status": 202, "headers": []}
        )
        await inner_send({"type": "http.response.body", "body": b"queued"})

    async def send(message):
        sent.append(message)

    asyncio.run(
        community_app.AnalyzeAdmissionMiddleware(app, max_body_bytes=8)(
            _scope(), receive, send
        )
    )

    assert _status(sent) == 202
    assert reservation.released is False
    reservation.release()
    assert reservation.released is True
