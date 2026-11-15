from __future__ import annotations

import asyncio
import importlib
import importlib.util
import sys
from typing import Any

import pytest


def _invoke_asgi(app: Any, headers: list[tuple[bytes, bytes]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event: dict[str, Any]) -> None:
        events.append(event)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/mcp",
        "headers": headers,
    }
    asyncio.run(app(scope, receive, send))
    return events


def _status(events: list[dict[str, Any]]) -> int:
    return next(event["status"] for event in events if event["type"] == "http.response.start")


def test_mcp_server_module_imports_without_optional_dependency_failure() -> None:
    module = importlib.import_module("bionuclei.mcp_server")
    assert hasattr(module, "build_server")
    assert hasattr(module, "main")


def test_mcp_server_builds_when_sdk_is_installed() -> None:
    if importlib.util.find_spec("mcp") is None:
        pytest.skip("MCP SDK is an optional dependency")
    from bionuclei.mcp_server import build_server

    server = build_server()
    assert server is not None
    assert server.name == "BioMCP-BioNuclei"


def test_remote_http_bind_requires_a_strong_bearer_token() -> None:
    from bionuclei.mcp_server import _validated_http_token

    assert _validated_http_token("127.0.0.1", None) is None
    assert _validated_http_token("::1", None) is None
    assert _validated_http_token("[::1]", None) is None
    assert _validated_http_token("0.0.0.0", "x" * 32) == "x" * 32

    with pytest.raises(RuntimeError, match="non-loopback"):
        _validated_http_token("0.0.0.0", None)
    with pytest.raises(RuntimeError, match="32 ASCII characters"):
        _validated_http_token("127.0.0.1", "short")
    with pytest.raises(RuntimeError, match="no whitespace"):
        _validated_http_token("0.0.0.0", "x" * 31 + " ")
    with pytest.raises(RuntimeError, match="32 ASCII characters"):
        _validated_http_token("127.0.0.1", "é" * 32)


def test_bearer_middleware_rejects_missing_invalid_and_duplicate_headers() -> None:
    from bionuclei.mcp_server import _BearerTokenASGIMiddleware

    token = "secret-" + "x" * 40
    called = False

    async def endpoint(scope: dict[str, Any], receive: Any, send: Any) -> None:
        nonlocal called
        called = True
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = _BearerTokenASGIMiddleware(endpoint, token)
    for headers in (
        [],
        [(b"authorization", b"Bearer wrong")],
        [
            (b"authorization", f"Bearer {token}".encode()),
            (b"authorization", f"Bearer {token}".encode()),
        ],
    ):
        called = False
        events = _invoke_asgi(middleware, headers)
        assert _status(events) == 401
        assert not called
        body = next(event["body"] for event in events if event["type"] == "http.response.body")
        assert token.encode() not in body


def test_bearer_middleware_accepts_case_insensitive_scheme() -> None:
    from bionuclei.mcp_server import _BearerTokenASGIMiddleware

    token = "secret-" + "y" * 40
    called = False

    async def endpoint(scope: dict[str, Any], receive: Any, send: Any) -> None:
        nonlocal called
        called = True
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    events = _invoke_asgi(
        _BearerTokenASGIMiddleware(endpoint, token),
        [(b"authorization", f"bearer {token}".encode())],
    )
    assert _status(events) == 204
    assert called


def test_main_http_defaults_to_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module("bionuclei.mcp_server")
    captured: dict[str, Any] = {}

    class FakeServer:
        def streamable_http_app(self, **kwargs: Any) -> object:
            captured["app_kwargs"] = kwargs
            return object()

    class FakeUvicorn:
        @staticmethod
        def run(app: Any, *, host: str, port: int) -> None:
            captured.update(app=app, host=host, port=port)

    monkeypatch.setattr(module, "build_server", lambda: FakeServer())
    monkeypatch.setitem(sys.modules, "uvicorn", FakeUvicorn())
    monkeypatch.delenv("BIOMCP_MCP_HOST", raising=False)
    monkeypatch.delenv("BIOMCP_MCP_BEARER_TOKEN", raising=False)
    module.main_http()

    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8001
    assert captured["app_kwargs"] == {"streamable_http_path": "/mcp", "host": "127.0.0.1"}
    assert not isinstance(captured["app"], module._BearerTokenASGIMiddleware)


def test_main_http_refuses_remote_bind_before_server_start(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module("bionuclei.mcp_server")
    monkeypatch.setenv("BIOMCP_MCP_HOST", "0.0.0.0")
    monkeypatch.delenv("BIOMCP_MCP_BEARER_TOKEN", raising=False)
    monkeypatch.setattr(module, "build_server", lambda: pytest.fail("server must not start without auth"))

    with pytest.raises(RuntimeError, match="non-loopback"):
        module.main_http()


def test_main_http_wraps_remote_app_with_bearer_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module("bionuclei.mcp_server")
    captured: dict[str, Any] = {}

    class FakeServer:
        def streamable_http_app(self, **kwargs: Any) -> object:
            return object()

    class FakeUvicorn:
        @staticmethod
        def run(app: Any, *, host: str, port: int) -> None:
            captured.update(app=app, host=host, port=port)

    monkeypatch.setattr(module, "build_server", lambda: FakeServer())
    monkeypatch.setitem(sys.modules, "uvicorn", FakeUvicorn())
    monkeypatch.setenv("BIOMCP_MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("BIOMCP_MCP_BEARER_TOKEN", "z" * 48)
    module.main_http()

    assert captured["host"] == "0.0.0.0"
    assert isinstance(captured["app"], module._BearerTokenASGIMiddleware)
