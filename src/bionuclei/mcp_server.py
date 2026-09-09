"""BioMCP server exposing deterministic BioNuclei operations.

The MCP layer orchestrates validated scientific Python functions; it is not a
measurement engine. Every mutating/computational tool returns structured output
and the underlying BioNuclei functions write their normal artifacts.

The MCP SDK is an optional dependency. Install with ``pip install -e '.[mcp]'``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from mcp.server import MCPServer
except ImportError as exc:  # pragma: no cover - exercised only without optional dep
    MCPServer = None  # type: ignore[assignment,misc]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

from .inference import evaluate, predict
from .metrics import aji_score, boundary_f1, dice_coefficient, iou_score
from .data import decode_instance_mask
import numpy as np
import tifffile
from scipy import ndimage


SERVER_NAME = "BioMCP-BioNuclei"


def _require_sdk() -> Any:
    if MCPServer is None:
        raise RuntimeError(
            "BioMCP requires the optional MCP SDK. Install with: "
            "python -m pip install -e '.[mcp]'"
        ) from _IMPORT_ERROR
    return MCPServer


def build_server() -> Any:
    Server = _require_sdk()
    mcp = Server(SERVER_NAME)

    @mcp.tool()
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

    @mcp.tool()
    def predict_image(input_path: str, checkpoint: str, output_dir: str, device: str = "cpu") -> dict[str, Any]:
        """Run deterministic BioNuclei inference and return the result bundle."""
        if device not in {"cpu", "cuda"}:
            raise ValueError("device must be 'cpu' or 'cuda'")
        return predict(Path(input_path), Path(checkpoint), Path(output_dir), device)

    @mcp.tool()
    def evaluate_image(input_path: str, ground_truth: str, checkpoint: str, output_dir: str, device: str = "cpu") -> dict[str, Any]:
        """Run deterministic BioNuclei inference plus Dice, IoU and Boundary-F1."""
        if device not in {"cpu", "cuda"}:
            raise ValueError("device must be 'cpu' or 'cuda'")
        return evaluate(Path(input_path), Path(ground_truth), Path(checkpoint), Path(output_dir), device)

    @mcp.tool()
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

    @mcp.tool()
    def read_provenance(provenance_path: str) -> dict[str, Any]:
        """Read a machine-readable BioNuclei provenance record."""
        path = Path(provenance_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        return json.loads(path.read_text())

    @mcp.tool()
    def load_result_summary(results_path: str) -> dict[str, Any]:
        """Read a structured BioNuclei results.json file."""
        path = Path(results_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        return json.loads(path.read_text())

    @mcp.resource("bionuclei://protocol")
    def protocol_resource() -> str:
        """Expose the local scientific protocol as a read-only MCP resource."""
        path = Path("docs/RESEARCH_PROTOCOL.md")
        return path.read_text() if path.is_file() else "Research protocol is not available in this working tree."

    @mcp.resource("bionuclei://datasets")
    def datasets_resource() -> str:
        """Expose dataset roles and provenance guidance as a read-only resource."""
        path = Path("docs/DATASETS.md")
        return path.read_text() if path.is_file() else "Dataset documentation is not available in this working tree."

    return mcp


def main() -> None:
    server = build_server()
    server.run()


if __name__ == "__main__":
    main()
