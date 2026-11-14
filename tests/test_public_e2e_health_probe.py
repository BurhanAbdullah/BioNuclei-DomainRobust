from __future__ import annotations

import ast
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
    def __init__(self, status_code: int, text: str = "health") -> None:
        self.status_code = status_code
        self.text = text

    def json(self) -> dict[str, str]:
        return {"status": "ok"}


class _ReadTimeout(Exception):
    pass


def _health_helpers() -> dict[str, object]:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {
        "HEALTH_READINESS_BUDGET_SECONDS",
        "HEALTH_CONNECT_TIMEOUT_SECONDS",
        "HEALTH_READ_TIMEOUT_CAP_SECONDS",
        "_health_request_timeout",
        "_health_response_within_budget",
        "_probe_api_health",
    }
    selected = [
        node
        for node in tree.body
        if isinstance(node, (ast.Assign, ast.FunctionDef))
        and (
            any(
                isinstance(target, ast.Name) and target.id in names
                for target in getattr(node, "targets", [])
            )
            or getattr(node, "name", None) in names
        )
    ]
    namespace: dict[str, object] = {}
    module = ast.Module(body=selected, type_ignores=[])
    exec(compile(module, str(SCRIPT_PATH), "exec"), namespace)
    return namespace


def test_health_timeout_is_bounded_by_remaining_budget() -> None:
    helpers = _health_helpers()
    timeout_for = helpers["_health_request_timeout"]

    assert timeout_for(179.0) == (10.0, 150.0)
    assert timeout_for(134.0) == (10.0, 124.0)
    assert timeout_for(30.0) == (10.0, 20.0)
    assert sum(timeout_for(5.0)) <= 5.0
    with pytest.raises(ValueError, match="budget is exhausted"):
        timeout_for(0.0)


def test_health_probe_accepts_a_real_response_after_observed_cold_start() -> None:
    helpers = _health_helpers()
    clock = _Clock()
    response = _Response(200)

    def get(_url: str, *, timeout: tuple[float, float]) -> _Response:
        assert timeout == (10.0, 150.0)
        clock.now += 134.0
        return response

    result, attempts, request_error, body = helpers["_probe_api_health"](
        "https://api.example.test",
        request_get=get,
        request_exception=_ReadTimeout,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    assert result is response
    assert len(attempts) == 1
    assert attempts[0]["result"] == "http_200"
    assert attempts[0]["elapsed_seconds"] == 134.0
    assert request_error is None
    assert body is None


def test_health_probe_rejects_a_response_after_the_deadline() -> None:
    helpers = _health_helpers()
    clock = _Clock()

    def late_get(_url: str, *, timeout: tuple[float, float]) -> _Response:
        clock.now += 180.0
        return _Response(200)

    result, attempts, request_error, _body = helpers["_probe_api_health"](
        "https://api.example.test",
        request_get=late_get,
        request_exception=_ReadTimeout,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    assert result is None
    assert attempts[-1]["error"] == "ReadinessBudgetExceeded"
    assert request_error == "ReadinessBudgetExceeded"


def test_health_probe_clears_stale_timeout_after_recovery() -> None:
    helpers = _health_helpers()
    clock = _Clock()
    calls = 0
    response = _Response(200)

    def get(_url: str, *, timeout: tuple[float, float]) -> _Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            clock.now += 10.0
            raise _ReadTimeout("temporary cold start")
        clock.now += 2.0
        return response

    result, attempts, request_error, body = helpers["_probe_api_health"](
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


def test_health_probe_stops_at_one_total_budget() -> None:
    helpers = _health_helpers()
    clock = _Clock()

    def timeout_get(_url: str, *, timeout: tuple[float, float]) -> _Response:
        clock.now += sum(timeout)
        raise _ReadTimeout("still starting")

    result, attempts, request_error, _body = helpers["_probe_api_health"](
        "https://api.example.test",
        request_get=timeout_get,
        request_exception=_ReadTimeout,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    assert result is None
    assert request_error == "_ReadTimeout"
    assert len(attempts) == 2
    assert clock.now == pytest.approx(179.0)


def test_public_e2e_fails_closed_without_the_immutable_checkpoint_health_contract() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "EXPECTED_CHECKPOINT_SHA256 = " in source
    verified_gate = 'require(\n                health.get("checkpoint_verified") is True'
    digest_gate = 'require(\n                health.get("checkpoint_sha256") == EXPECTED_CHECKPOINT_SHA256'
    assert verified_gate in source
    assert digest_gate in source
    assert source.index(verified_gate) < source.index('page.locator("#guestButton").click')
    assert source.index(digest_gate) < source.index('page.locator("#analyzeButton").click')
