from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "live_public_agent_e2e.py"


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class _Response:
    def __init__(
        self,
        status_code: int,
        text: str = "health",
        *,
        body: bytes | None = None,
        clock: _Clock | None = None,
        seconds_per_chunk: float = 0.0,
    ) -> None:
        self.status_code = status_code
        self._body = body if body is not None else text.encode("utf-8")
        self.clock = clock
        self.seconds_per_chunk = seconds_per_chunk
        self.closed = False
        self.requested_chunk_size: int | None = None

    def iter_content(self, chunk_size: int = 1):
        self.requested_chunk_size = chunk_size
        for offset in range(0, len(self._body), chunk_size):
            if self.clock is not None:
                self.clock.now += self.seconds_per_chunk
            yield self._body[offset : offset + chunk_size]

    def close(self) -> None:
        self.closed = True


class _ReadTimeout(Exception):
    pass


def _health_helpers() -> dict[str, object]:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {
        "HEALTH_READINESS_BUDGET_SECONDS",
        "HEALTH_CONNECT_TIMEOUT_SECONDS",
        "HEALTH_READ_TIMEOUT_CAP_SECONDS",
        "HEALTH_RESPONSE_MAX_BYTES",
        "_health_request_timeout",
        "_probe_api_health",
        "_HealthReadinessBudgetExceeded",
        "_HealthResponseTooLarge",
    }
    selected = [
        node
        for node in tree.body
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id in names
                for target in getattr(node, "targets", [])
            )
        )
        or (isinstance(node, ast.FunctionDef) and node.name in names)
        or (isinstance(node, ast.ClassDef) and node.name in names)
    ]
    namespace: dict[str, object] = {"json": json}
    module = ast.Module(body=selected, type_ignores=[])
    exec(compile(module, str(SCRIPT_PATH), "exec"), namespace)
    return namespace


def test_health_timeout_uses_short_socket_reads_within_remaining_budget() -> None:
    helpers = _health_helpers()
    timeout_for = helpers["_health_request_timeout"]

    assert timeout_for(179.0) == (10.0, 2.0)
    assert timeout_for(134.0) == (10.0, 2.0)
    assert timeout_for(30.0) == (10.0, 2.0)
    assert timeout_for(5.0) == (2.5, 2.0)
    assert sum(timeout_for(5.0)) <= 5.0
    with pytest.raises(ValueError, match="budget is exhausted"):
        timeout_for(0.0)


def test_health_probe_recovers_after_realistic_cold_start_retries() -> None:
    helpers = _health_helpers()
    clock = _Clock()
    calls = 0
    response = _Response(200, body=b'{"status":"ok"}')

    def get(_url: str, *, timeout: tuple[float, float], stream: bool, allow_redirects: bool) -> _Response:
        nonlocal calls
        calls += 1
        assert stream is True
        assert timeout[1] <= 2.0
        if calls <= 9:
            clock.now += sum(timeout)
            raise _ReadTimeout("service still starting")
        clock.now += 0.1
        return response

    result, attempts, request_error, body, payload = helpers["_probe_api_health"](
        "https://api.example.test",
        request_get=get,
        request_exception=_ReadTimeout,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    assert result is response
    assert len(attempts) == 10
    assert attempts[-1]["result"] == "http_200"
    assert request_error is None
    assert body is None
    assert payload == {"status": "ok"}
    assert response.requested_chunk_size == 1
    assert response.closed
    assert clock.now < 179.0


def test_health_probe_rejects_a_response_after_the_deadline() -> None:
    helpers = _health_helpers()
    clock = _Clock()
    response = _Response(200, body=b'{"status":"ok"}')

    def late_get(_url: str, *, timeout: tuple[float, float], stream: bool, allow_redirects: bool) -> _Response:
        clock.now += 180.0
        return response

    result, attempts, request_error, _body, payload = helpers["_probe_api_health"](
        "https://api.example.test",
        request_get=late_get,
        request_exception=_ReadTimeout,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    assert result is None
    assert attempts[-1]["error"] == "ReadinessBudgetExceeded"
    assert request_error == "ReadinessBudgetExceeded"
    assert payload is None
    assert response.closed


def test_health_probe_stops_slow_trickle_body_at_total_deadline() -> None:
    helpers = _health_helpers()
    clock = _Clock()
    response = _Response(
        200,
        body=b"x" * 256,
        clock=clock,
        seconds_per_chunk=1.0,
    )

    def get(_url: str, *, timeout: tuple[float, float], stream: bool, allow_redirects: bool) -> _Response:
        return response

    result, attempts, request_error, _body, payload = helpers["_probe_api_health"](
        "https://api.example.test",
        request_get=get,
        request_exception=_ReadTimeout,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    assert result is None
    assert clock.now == pytest.approx(179.0)
    assert attempts[-1]["error"] == "ReadinessBudgetExceeded"
    assert request_error == "ReadinessBudgetExceeded"
    assert payload is None
    assert response.closed


def test_health_probe_rejects_oversized_response_body() -> None:
    helpers = _health_helpers()
    response = _Response(200, body=b"x" * (64 * 1024 + 1))

    def get(_url: str, *, timeout: tuple[float, float], stream: bool, allow_redirects: bool) -> _Response:
        return response

    result, attempts, request_error, _body, payload = helpers["_probe_api_health"](
        "https://api.example.test",
        request_get=get,
        request_exception=_ReadTimeout,
        monotonic=lambda: 0.0,
        sleep=lambda _seconds: None,
    )

    assert result is None
    assert attempts[-1]["error"] == "HealthResponseTooLarge"
    assert request_error == "HealthResponseTooLarge"
    assert payload is None
    assert response.closed


def test_health_probe_clears_stale_timeout_after_recovery() -> None:
    helpers = _health_helpers()
    clock = _Clock()
    calls = 0
    response = _Response(200, body=b'{"status":"ok"}')

    def get(_url: str, *, timeout: tuple[float, float], stream: bool, allow_redirects: bool) -> _Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            clock.now += sum(timeout)
            raise _ReadTimeout("temporary cold start")
        clock.now += 0.1
        return response

    result, attempts, request_error, body, payload = helpers["_probe_api_health"](
        "https://api.example.test",
        request_get=get,
        request_exception=_ReadTimeout,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    assert result is response
    assert len(attempts) == 2
    assert attempts[0]["error"] == "_ReadTimeout"
    assert request_error is None
    assert body is None
    assert payload == {"status": "ok"}
    assert response.closed


def test_health_probe_stops_at_one_total_budget() -> None:
    helpers = _health_helpers()
    clock = _Clock()

    def timeout_get(
        _url: str,
        *,
        timeout: tuple[float, float],
        stream: bool,
        allow_redirects: bool,
    ) -> _Response:
        assert stream is True
        assert allow_redirects is False
        clock.now += sum(timeout)
        raise _ReadTimeout("still starting")

    result, attempts, request_error, _body, payload = helpers["_probe_api_health"](
        "https://api.example.test",
        request_get=timeout_get,
        request_exception=_ReadTimeout,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    assert result is None
    assert request_error == "ReadinessBudgetExceeded"
    assert len(attempts) > 2
    assert clock.now == pytest.approx(179.0)
    assert attempts[-1]["readiness_budget_exhausted"] is True
    assert payload is None

def test_http_response_clears_stale_timeout_even_when_service_is_not_ready() -> None:
    helpers = _health_helpers()
    clock = _Clock()
    calls = 0
    response_503 = _Response(503, "service unavailable")
    response_200 = _Response(200, body=b'{"status":"ok"}')

    def get(
        _url: str,
        *,
        timeout: tuple[float, float],
        stream: bool,
        allow_redirects: bool,
    ) -> _Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            clock.now += sum(timeout)
            raise _ReadTimeout("temporary cold start")
        clock.now += 0.1
        return response_503 if calls == 2 else response_200

    result, attempts, request_error, body, payload = helpers["_probe_api_health"](
        "https://api.example.test",
        request_get=get,
        request_exception=_ReadTimeout,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        budget_seconds=30.0,
    )

    assert result is response_200 and result.status_code == 200
    assert len(attempts) == 3
    assert attempts[0]["error"] == "_ReadTimeout"
    assert attempts[1]["http_status"] == 503
    assert "error" not in attempts[1]
    assert request_error is None
    assert body is None
    assert payload == {"status": "ok"}
    assert response_503.closed
    assert response_200.closed

def test_invalid_health_json_fails_closed_and_closes_response() -> None:
    helpers = _health_helpers()
    response = _Response(200, body=b"not-json")

    def get(_url: str, *, timeout: tuple[float, float], stream: bool, allow_redirects: bool) -> _Response:
        return response

    result, attempts, request_error, _body, payload = helpers["_probe_api_health"](
        "https://api.example.test",
        request_get=get,
        request_exception=_ReadTimeout,
        monotonic=lambda: 0.0,
        sleep=lambda _seconds: None,
    )

    assert result is None
    assert attempts[-1]["error"] == "InvalidHealthJSON"
    assert request_error == "InvalidHealthJSON"
    assert payload is None
    assert response.closed


def test_invalid_health_json_after_503_reports_the_latest_http_response() -> None:
    helpers = _health_helpers()
    clock = _Clock()
    response_503 = _Response(503, "service unavailable")
    response_200 = _Response(200, body=b"not-json")
    calls = 0

    def get(_url: str, *, timeout: tuple[float, float], stream: bool, allow_redirects: bool) -> _Response:
        nonlocal calls
        calls += 1
        return response_503 if calls == 1 else response_200

    result, attempts, request_error, body, payload = helpers["_probe_api_health"](
        "https://api.example.test",
        request_get=get,
        request_exception=_ReadTimeout,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        budget_seconds=30.0,
    )

    assert result is response_200
    assert [attempt["http_status"] for attempt in attempts] == [503, 200]
    assert attempts[-1]["error"] == "InvalidHealthJSON"
    assert request_error == "InvalidHealthJSON"
    assert body is None
    assert payload is None
    assert response_503.closed
    assert response_200.closed


def test_public_e2e_fails_closed_without_the_immutable_checkpoint_health_contract() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "EXPECTED_CHECKPOINT_SHA256 = " in source
    verified_gate = 'require(\n                health.get("checkpoint_verified") is True'
    digest_gate = 'require(\n                health.get("checkpoint_sha256") == EXPECTED_CHECKPOINT_SHA256'
    assert verified_gate in source
    assert digest_gate in source
    assert source.index(verified_gate) < source.index('page.locator("#guestButton").click')
    assert source.index(digest_gate) < source.index('page.locator("#analyzeButton").click')


def test_live_e2e_workflow_never_contacts_public_service_from_a_pull_request() -> None:
    import yaml

    workflow_path = ROOT / ".github" / "workflows" / "live-public-agent-e2e.yml"
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    jobs = workflow["jobs"]

    assert jobs["validate-harness"]["if"] == "github.event_name == 'pull_request'"
    public_condition = jobs["public-upload-to-agent"]["if"]
    assert "github.event_name != 'pull_request'" in public_condition
    assert "github.repository == 'BurhanAbdullah/BioNuclei-DomainRobust'" in public_condition
    assert "github.ref == 'refs/heads/main'" in public_condition
