from __future__ import annotations

import asyncio
import importlib
import importlib.util
import sys
from pathlib import Path
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


def test_mcp_streamable_http_app_constructs_when_sdk_is_installed() -> None:
    if importlib.util.find_spec("mcp") is None:
        pytest.skip("MCP SDK is an optional dependency")
    from bionuclei.mcp_server import build_server

    app = build_server().streamable_http_app(streamable_http_path="/mcp", host="127.0.0.1")
    assert callable(app)


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


def test_bearer_auth_wraps_the_actual_streamable_http_mcp_route() -> None:
    if importlib.util.find_spec("mcp") is None:
        pytest.skip("MCP SDK is an optional dependency")
    import json
    import socket
    import threading
    import time
    import urllib.error
    import urllib.request

    import uvicorn

    from bionuclei.mcp_server import _BearerTokenASGIMiddleware, build_server

    token = "actual-http-" + "q" * 40
    app = build_server().streamable_http_app(
        streamable_http_path="/mcp",
        host="127.0.0.1",
    )
    protected_app = _BearerTokenASGIMiddleware(app, token)

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    server = uvicorn.Server(
        uvicorn.Config(
            protected_app,
            host="127.0.0.1",
            port=port,
            log_level="critical",
            lifespan="on",
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.01)
    if not server.started:
        server.should_exit = True
        thread.join(timeout=5)
        pytest.fail("Uvicorn did not start the actual Streamable HTTP MCP app")

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "bionuclei-auth-test", "version": "1.0.0"},
        },
    }
    url = f"http://127.0.0.1:{port}/mcp"

    def post(headers: dict[str, str]) -> tuple[int, Any, bytes]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                **headers,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as response:
            return response.code, response.headers, response.read()

    try:
        unauthorized_status, unauthorized_headers, unauthorized_body = post({})
        assert unauthorized_status == 401
        assert unauthorized_headers.get("Cache-Control") == "no-store"
        assert b"unauthorized" in unauthorized_body

        authorized_status, _authorized_headers, authorized_body = post(
            {"Authorization": f"Bearer {token}"}
        )
        assert authorized_status == 200, authorized_body.decode("utf-8", errors="replace")
        assert b"serverInfo" in authorized_body
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        assert not thread.is_alive(), "Uvicorn test server did not shut down cleanly"


def test_mcp_sdk_dependency_has_redirect_safe_minimum() -> None:
    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    requirements = (root / "pyproject.toml").read_text(encoding="utf-8")
    # GHSA-5h93-6whr-6q8j affects MCP SDK 2.0.0 through 2.1.1.
    assert '"mcp>=2.2,<3"' in requirements


def test_streamable_http_client_discovers_and_calls_real_bionuclei_tools(tmp_path: Path) -> None:
    if importlib.util.find_spec("mcp") is None:
        pytest.skip("MCP SDK is an optional dependency")

    import socket
    import threading
    import time

    import httpx2
    import numpy as np
    import tifffile
    import uvicorn
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    from bionuclei.mcp_server import _BearerTokenASGIMiddleware, build_server

    token = "mcp-sdk-http-" + "r" * 40
    image = np.zeros((32, 32), dtype=np.uint16)
    image[0, 0] = 65535
    image_path = tmp_path / "http-uint16.tif"
    tifffile.imwrite(image_path, image)

    app = build_server().streamable_http_app(
        streamable_http_path="/mcp",
        host="127.0.0.1",
    )
    protected_app = _BearerTokenASGIMiddleware(app, token)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    server = uvicorn.Server(
        uvicorn.Config(
            protected_app,
            host="127.0.0.1",
            port=port,
            log_level="critical",
            lifespan="on",
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.01)
    if not server.started:
        server.should_exit = True
        thread.join(timeout=5)
        pytest.fail("Uvicorn did not start the Streamable HTTP MCP app")

    url = f"http://127.0.0.1:{port}/mcp"
    try:
        async def exercise_client() -> None:
            timeout = httpx2.Timeout(5.0, read=10.0)
            async with httpx2.AsyncClient(
                headers={"Authorization": f"Bearer {token}"},
                timeout=timeout,
                follow_redirects=False,
            ) as http_client:
                async with streamable_http_client(
                    url=url,
                    http_client=http_client,
                    terminate_on_close=False,
                ) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        advertised = await session.list_tools()
                        names = {tool.name for tool in advertised.tools}
                        assert "inspect_image" in names

                        result = await session.call_tool(
                            "inspect_image",
                            arguments={"input_path": str(image_path)},
                        )
                        payload = result.model_dump(by_alias=True)
                        assert not payload.get("isError", payload.get("is_error", False))
                        structured = payload.get("structuredContent") or payload.get("structured_content")
                        assert isinstance(structured, dict)
                        assert structured["dtype"] == "uint16"
                        assert structured["max"] == 65535.0

        asyncio.run(exercise_client())
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        assert not thread.is_alive(), "Uvicorn MCP test server did not shut down cleanly"
