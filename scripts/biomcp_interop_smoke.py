#!/usr/bin/env python3
"""Exercise the real BioMCP client against the installed BioNuclei MCP server."""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import numpy as np
import tifffile
from biomcp.mcp_client import call_tool, discover_tools


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="bionuclei-biomcp-") as tmp:
        root = Path(tmp)
        image = np.full((512, 512), 512, dtype=np.uint16)
        image[0, 0] = 0
        image[0, 1] = 65535
        image[256, 256] = 4096
        image_path = root / "deterministic-uint16.tif"
        tifffile.imwrite(image_path, image)

        advertised = discover_tools("bionuclei")
        names = {item["name"] for item in advertised}
        required = {"inspect_image", "compute_instance_metrics"}
        missing = sorted(required - names)
        if missing:
            raise AssertionError(f"BioNuclei MCP server did not advertise required tools: {missing}")

        inspected = call_tool("bionuclei", "inspect_image", {"input_path": str(image_path)})
        if inspected.get("is_error"):
            raise AssertionError(f"inspect_image returned an MCP error: {inspected}")
        measured = inspected.get("structured_content")
        if not isinstance(measured, dict):
            raise AssertionError("inspect_image did not return structured scientific measurements")
        if measured.get("shape") != [512, 512] or measured.get("dtype") != "uint16":
            raise AssertionError(f"Image shape/dtype changed across BioMCP: {measured}")
        if float(measured.get("min", -1)) != 0.0 or float(measured.get("max", -1)) != 65535.0:
            raise AssertionError(f"Full uint16 dynamic range did not survive BioMCP: {measured}")

        prediction = np.zeros((64, 64), dtype=np.uint16)
        prediction[8:32, 11:40] = 7
        target = prediction.copy()
        prediction_path = root / "prediction-mask.tif"
        target_path = root / "target-mask.tif"
        tifffile.imwrite(prediction_path, prediction)
        tifffile.imwrite(target_path, target)

        metrics_result = call_tool(
            "bionuclei",
            "compute_instance_metrics",
            {"prediction_mask": str(prediction_path), "ground_truth_mask": str(target_path)},
        )
        if metrics_result.get("is_error"):
            raise AssertionError(f"compute_instance_metrics returned an MCP error: {metrics_result}")
        metrics = metrics_result.get("structured_content")
        if not isinstance(metrics, dict):
            raise AssertionError("compute_instance_metrics did not return structured metrics")
        for key in ("dice", "iou", "aji", "boundary_f1"):
            if key not in metrics or not math.isclose(float(metrics[key]), 1.0, rel_tol=0.0, abs_tol=1e-9):
                raise AssertionError(f"Expected identical-mask {key}=1.0, got {metrics.get(key)!r}")

        print(json.dumps({
            "status": "PASS",
            "client": "BioMCP",
            "server": "BioNuclei",
            "transport": inspected["provenance"]["transport"],
            "discovered_tools": sorted(names),
            "uint16_measurements": {
                "shape": measured["shape"],
                "dtype": measured["dtype"],
                "min": measured["min"],
                "max": measured["max"],
            },
            "identical_mask_metrics": metrics,
            "no_model_or_training_invoked": True,
        }, sort_keys=True))


if __name__ == "__main__":
    main()
