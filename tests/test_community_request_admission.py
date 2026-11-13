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
    response_headers = dict(next(m for m in sent if m["type"] == "http.response.start")["headers"])
    assert response_headers[b"retry-after"] == b"60"
    assert receive_calls == 0
    assert app_called is False


def test_fastapi_admission_runs_before_multipart_parsing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject():
        raise community_app.community_service.JobCapacityError(
            "The analyzer is at capacity."
        )

    monkeypatch.setattr(community_app.community_service, "reserve_job_slot", reject)
    with TestClient(community_app.app) as client:
        response = client.post(
            "/analyze",
            content=b"not a valid multipart body",
            headers={"Content-Type": "multipart/form-data; boundary=missing"},
        )

    assert response.status_code == 429, response.text
    assert response.headers["Retry-After"] == "60"


def test_content_length_limit_rejects_before_reading_and_releases_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reservation = _Reservation()
    monkeypatch.setattr(
        community_app.community_service,
        "reserve_job_slot",
        lambda: reservation,
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
    assert reservation.released is True


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
