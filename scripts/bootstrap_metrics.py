#!/usr/bin/env python3
"""Compute image-level bootstrap confidence intervals from per-image metrics JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

METRICS = ("dice", "iou", "aji", "boundary_f1")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", type=Path, required=True, help="JSON containing a per_image list")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    payload = json.loads(args.metrics.read_text())
    rows = payload.get("per_image", [])
    if len(rows) < 2:
        raise ValueError("At least two images are required for image-level bootstrap intervals")
    rng = np.random.default_rng(args.seed)
    n = len(rows)
    out = {}
    for metric in METRICS:
        values = np.asarray([float(r[metric]) for r in rows], dtype=np.float64)
        indices = rng.integers(0, n, size=(args.iterations, n))
        samples = values[indices].mean(axis=1)
        out[metric] = {
            "mean": float(values.mean()),
            "lower_95": float(np.quantile(samples, 0.025)),
            "upper_95": float(np.quantile(samples, 0.975)),
        }
    result = {
        "n_images": n,
        "iterations": args.iterations,
        "seed": args.seed,
        "resampling_unit": "image",
        "metrics": out,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
