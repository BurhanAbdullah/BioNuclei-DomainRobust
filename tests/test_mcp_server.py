from __future__ import annotations

import asyncio
import importlib.util
import json
import sys

import numpy as np
import pytest
import tifffile


def test_mcp_server_module_imports_without_optional_dependency_failure() -> None:
    module = __import__("bionuclei.mcp_server", fromlist=["build_server"])
    assert hasattr(module, "build_server")
    assert hasattr(module, "main")


def test_mcp_server_builds_when_sdk_is_installed() -> None:
    if importlib.util.find_spec("mcp") is None:
        pytest.skip("MCP SDK is an optional dependency")
    from bionuclei.mcp_server import build_server

    server = build_server()
    assert server is not None
    assert server.name == "BioMCP-BioNuclei"


def test_mcp_stdio_client_lists_tools_and_preserves_uint16(tmp_path) -> None:
    if importlib.util.find_spec("mcp") is None:
        pytest.skip("MCP SDK is an optional dependency")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    image = np.zeros((32, 32), dtype=np.uint16)
    image[8:12, 8:12] = 65535
    image[20:22, 20:22] = 1024
    image_path = tmp_path / "uint16-fixture.tif"
    tifffile.imwrite(image_path, image)

    async def exercise_protocol() -> None:
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "bionuclei.mcp_server"],
        )
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                tool_names = {tool.name for tool in tools.tools}
                assert {
                    "inspect_image",
                    "predict_image",
                    "evaluate_image",
                    "compute_instance_metrics",
                    "read_provenance",
                    "load_result_summary",
                }.issubset(tool_names)

                result = await session.call_tool(
                    "inspect_image",
                    {"input_path": str(image_path)},
                )
                assert not getattr(result, "isError", getattr(result, "is_error", False))

                payload = getattr(
                    result,
                    "structuredContent",
                    getattr(result, "structured_content", None),
                )
                if not isinstance(payload, dict):
                    text_blocks = [
                        getattr(block, "text", None)
                        for block in getattr(result, "content", [])
                    ]
                    payload = json.loads(next(text for text in text_blocks if text))

                assert payload["shape"] == [32, 32]
                assert payload["dtype"] == "uint16"
                assert payload["min"] == 0.0
                assert payload["max"] == 65535.0

    asyncio.run(exercise_protocol())
