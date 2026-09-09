from __future__ import annotations

import importlib.util

import pytest


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
