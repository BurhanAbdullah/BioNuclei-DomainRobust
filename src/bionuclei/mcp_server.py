"""BioMCP server exposing deterministic BioNuclei operations.

BioMCP is the interoperability layer; BioNuclei remains the scientific
measurement engine. The MCP server only validates inputs, invokes the existing
scientific functions, and exposes read-only research resources.
"""
from __future__ import annotations

import hmac
import ipaddress
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import tifffile
from scipy import ndimage

try:
    from mcp.server.mcpserver import MCPServer
except ImportError as exc:  # pragma: no cover
    MCPServer = None  # type: ignore[assignment,misc]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

from .data import decode_instance_mask
from .inference import evaluate, predict
from .metrics import aji_score, boundary_f1, dice_coefficient, iou_score

SERVER_NAME = "BioMCP-BioNuclei"


def _is_loopback_host(host: str) -> bool:
    """Return True only for a literal loopback IP address."""
    candidate = host.strip()
    if candidate.startswith("[") and candidate.endswith("]"):
        candidate = candidate[1:-1]
    try:
        return ipaddress.ip_address(candidate).is_loopback
    except ValueError:
        return False


def _validated_http_token(host: str, token: str | None) -> str | None:
    """Require a strong bearer token whenever Streamable HTTP binds off-loopback."""
    if not token:
        if not _is_loopback_host(host):
            raise RuntimeError(
                "Refusing a non-loopback BioMCP HTTP bind without "
                "BIOMCP_MCP_BEARER_TOKEN"
            )
        return None
    if len(token) < 32 or not token.isascii() or any(character.isspace() for character in token):
        raise RuntimeError(
            "BIOMCP_MCP_BEARER_TOKEN must contain at least 32 ASCII characters "
            "and no whitespace"
        )
    return token


class _BearerTokenASGIMiddleware:
    """Protect every hosted MCP HTTP request with one configured bearer token."""

    def __init__(self, app: Any, token: str):
        self.app = app
        self._token = token.encode("utf-8")

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        authorization = [
            value for name, value in scope.get("headers", ()) if name.lower() == b"authorization"
        ]
        authorized = False
        if len(authorization) == 1:
            parts = authorization[0].split()
            authorized = (
                len(parts) == 2
                and parts[0].lower() == b"bearer"
                and hmac.compare_digest(parts[1], self._token)
            )
        if not authorized:
            body = b'{"error":"unauthorized"}'
            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode("ascii")),
                        (b"cache-control", b"no-store"),
                        (b"www-authenticate", b"Bearer"),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return

        await self.app(scope, receive, send)


def _require_sdk() -> Any:
    if MCPServer is None:
        raise RuntimeError(
            "BioMCP requires the optional MCP SDK. Install with: "
            "python -m pip install -e '.[mcp]'"
        ) from _IMPORT_ERROR
    return MCPServer


def build_server() -> Any:
    """Construct a fresh MCP server with the BioNuclei tool/resource registry."""
    Server = _require_sdk()
    server = Server(SERVER_NAME, instructions="Use validated BioNuclei tools; do not invent scientific measurements.")

    @server.tool()
    def inspect_image(input_path: str) -> dict[str, Any]:
        """Inspect a 2-D fluorescence TIFF without running a model."""
        path = Path(input_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        image = np.asarray(tifffile.imread(path))
        if image.ndim != 2:
            raise ValueError(f"Expected a 2-D fluorescence image; got shape {image.shape}")
        return {
            "path": str(path),
            "shape": list(image.shape),
            "dtype": str(image.dtype),
            "min": float(np.min(image)),
            "max": float(np.max(image)),
            "mean": float(np.mean(image)),
            "p99_5": float(np.percentile(image, 99.5)),
        }

    @server.tool()
    def predict_image(input_path: str, checkpoint: str, output_dir: str, device: str = "cpu") -> dict[str, Any]:
        """Run deterministic BioNuclei inference and return its structured result bundle."""
        if device not in {"cpu", "cuda"}:
            raise ValueError("device must be 'cpu' or 'cuda'")
        return predict(Path(input_path), Path(checkpoint), Path(output_dir), device)

    @server.tool()
    def evaluate_image(input_path: str, ground_truth: str, checkpoint: str, output_dir: str, device: str = "cpu") -> dict[str, Any]:
        """Run BioNuclei inference plus Dice, IoU and Boundary-F1."""
        if device not in {"cpu", "cuda"}:
            raise ValueError("device must be 'cpu' or 'cuda'")
        return evaluate(Path(input_path), Path(ground_truth), Path(checkpoint), Path(output_dir), device)

    @server.tool()
    def compute_instance_metrics(prediction_mask: str, ground_truth_mask: str) -> dict[str, float]:
        """Compute Dice, IoU, AJI and Boundary-F1 from integer instance masks."""
        pred = np.asarray(tifffile.imread(Path(prediction_mask).expanduser()))
        target = decode_instance_mask(np.asarray(tifffile.imread(Path(ground_truth_mask).expanduser())))
        if pred.shape != target.shape:
            raise ValueError(f"Prediction/ground-truth shape mismatch: {pred.shape} vs {target.shape}")
        pred_boundary = (pred > 0) & ~ndimage.binary_erosion(pred > 0, structure=np.ones((3, 3), dtype=np.uint8))
        target_boundary = (target > 0) & ~ndimage.binary_erosion(target > 0, structure=np.ones((3, 3), dtype=np.uint8))
        return {
            "dice": dice_coefficient(pred > 0, target > 0),
            "iou": iou_score(pred > 0, target > 0),
            "aji": aji_score(pred, target),
            "boundary_f1": boundary_f1(pred_boundary, target_boundary),
        }

    @server.tool()
    def read_provenance(provenance_path: str) -> dict[str, Any]:
        """Read a machine-readable BioNuclei provenance record."""
        path = Path(provenance_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        payload = json.loads(path.read_text())
        if not isinstance(payload, dict):
            raise ValueError("provenance must be a JSON object")
        return payload

    @server.tool()
    def load_result_summary(results_path: str) -> dict[str, Any]:
        """Read a structured BioNuclei results.json file."""
        path = Path(results_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        payload = json.loads(path.read_text())
        if not isinstance(payload, dict):
            raise ValueError("result summary must be a JSON object")
        return payload

    @server.resource("bionuclei://protocol")
    def protocol_resource() -> str:
        """Expose the research protocol as a read-only resource."""
        path = Path("docs/RESEARCH_PROTOCOL.md")
        return path.read_text() if path.is_file() else "Research protocol is unavailable in this working tree."

    @server.resource("bionuclei://datasets")
    def datasets_resource() -> str:
        """Expose dataset roles and provenance guidance as a read-only resource."""
        path = Path("docs/DATASETS.md")
        return path.read_text() if path.is_file() else "Dataset documentation is unavailable in this working tree."

    return server


mcp = build_server() if MCPServer is not None else None


def main() -> None:
    """Run the MCP server over stdio."""
    build_server().run()


def main_http() -> None:
    """Run Streamable HTTP locally or behind a bearer-token-protected remote bind."""
    host = os.getenv("BIOMCP_MCP_HOST", "127.0.0.1")
    port = int(os.getenv("BIOMCP_MCP_PORT", "8001"))
    path = os.getenv("BIOMCP_STREAMABLE_HTTP_PATH", "/mcp")
    token = _validated_http_token(host, os.getenv("BIOMCP_MCP_BEARER_TOKEN"))

    server = build_server()
    app = server.streamable_http_app(streamable_http_path=path, host=host)
    if token is not None:
        app = _BearerTokenASGIMiddleware(app, token)

    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - deployment dependency
        raise RuntimeError(
            "Hosted BioMCP requires uvicorn. Install with: "
            "python -m pip install -e '.[mcp]'"
        ) from exc
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
