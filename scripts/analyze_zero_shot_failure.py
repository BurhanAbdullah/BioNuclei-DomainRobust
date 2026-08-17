#!/usr/bin/env python3
"""Summarize verified failure modes from S-BIAD634 zero-shot metrics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def pearson(x: list[float], y: list[float]) -> float:
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/s_biad634_zero_shot/failure_analysis.json"))
    args = parser.parse_args()

    payload = json.loads(args.metrics.read_text())
    rows = payload["per_image"]
    if not rows:
        raise ValueError("metrics JSON contains no per-image records")

    dice = np.asarray([r["dice"] for r in rows], dtype=float)
    ratios = np.asarray(
        [r["n_pred_instances"] / max(r["n_target_instances"], 1) for r in rows],
        dtype=float,
    )
    heights = np.asarray([r["height"] for r in rows], dtype=float)
    widths = np.asarray([r["width"] for r in rows], dtype=float)

    worst = sorted(rows, key=lambda r: r["dice"])[:10]
    summary = {
        "experiment": payload.get("experiment"),
        "n_images": len(rows),
        "mean_dice": float(np.mean(dice)),
        "median_dice": float(np.median(dice)),
        "dice_quantiles": {
            "p10": float(np.quantile(dice, 0.10)),
            "p25": float(np.quantile(dice, 0.25)),
            "p50": float(np.quantile(dice, 0.50)),
            "p75": float(np.quantile(dice, 0.75)),
            "p90": float(np.quantile(dice, 0.90)),
        },
        "pred_to_target_instance_ratio": {
            "mean": float(np.mean(ratios)),
            "median": float(np.median(ratios)),
            "p90": float(np.quantile(ratios, 0.90)),
        },
        "correlation_with_dice": {
            "pred_to_target_instance_ratio": pearson(ratios.tolist(), dice.tolist()),
            "height": pearson(heights.tolist(), dice.tolist()),
            "width": pearson(widths.tolist(), dice.tolist()),
        },
        "worst_10_by_dice": [
            {
                "image": r["image"],
                "dice": r["dice"],
                "iou": r["iou"],
                "aji": r["aji"],
                "boundary_f1": r["boundary_f1"],
                "n_target_instances": r["n_target_instances"],
                "n_pred_instances": r["n_pred_instances"],
                "pred_to_target_instance_ratio": r["n_pred_instances"] / max(r["n_target_instances"], 1),
                "height": r["height"],
                "width": r["width"],
            }
            for r in worst
        ],
        "interpretation": [
            "The instance-count ratio is a diagnostic of over-segmentation; it is not itself a performance metric.",
            "Correlations are descriptive and do not establish causality.",
            "The analysis uses only the verified per-image zero-shot artifact and does not tune the model.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
