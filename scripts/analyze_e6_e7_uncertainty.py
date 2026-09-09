#!/usr/bin/env python3
"""Deterministic image-level uncertainty/failure analysis for release evidence.

This script is descriptive only: it does not perform model selection, tuning, or
hypothesis testing across E6 fractions. It computes image-level bootstrap
intervals and failure/outlier summaries from already-retained machine-readable
E6/E7 evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

E6_METRICS = ("dice", "iou", "aji", "boundary_f1")
E7_METRICS = E6_METRICS


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def bootstrap_mean_ci(values: np.ndarray, rng: np.random.Generator, n_resamples: int) -> list[float]:
    if values.size == 0:
        raise ValueError("Cannot bootstrap an empty sample")
    idx = rng.integers(0, values.size, size=(n_resamples, values.size))
    means = values[idx].mean(axis=1)
    return [float(v) for v in np.quantile(means, [0.025, 0.975])]


def load_json(path: Path) -> dict[str, Any]:
    with path.open() as f:
        return json.load(f)


def summarize_metric(rows: list[dict[str, Any]], key: str, rng: np.random.Generator, n_resamples: int) -> dict[str, Any]:
    x = np.asarray([float(r[key]) for r in rows], dtype=float)
    return {
        "mean": float(x.mean()),
        "median": float(np.median(x)),
        "bootstrap95_mean_ci": bootstrap_mean_ci(x, rng, n_resamples),
        "min": float(x.min()),
        "max": float(x.max()),
        "n": int(x.size),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--e6", action="append", nargs=2, metavar=("LABEL", "METRICS_JSON"), required=True)
    p.add_argument("--e7", required=True)
    p.add_argument("--metadata", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--bootstrap-resamples", type=int, default=10000)
    a = p.parse_args()

    rng = np.random.default_rng(a.seed)
    metadata = load_json(Path(a.metadata))
    out: dict[str, Any] = {
        "analysis": "e6_e7_image_level_uncertainty_and_failure",
        "status": "executed",
        "seed": a.seed,
        "bootstrap_resamples": a.bootstrap_resamples,
        "metadata": metadata,
        "e6": {},
        "e7": {},
    }

    e6_ids_by_label: dict[str, set[str]] = {}
    e6_rows_by_label: dict[str, dict[str, dict[str, Any]]] = {}
    for label, raw in a.e6:
        path = Path(raw)
        obj = load_json(path)
        rows = obj.get("per_image", [])
        if len(rows) != 10:
            raise AssertionError(f"{label}: expected 10 E6 test images, got {len(rows)}")
        if obj.get("n_images") != 10:
            raise AssertionError(f"{label}: n_images != 10")
        ids = {str(r["image"]) for r in rows}
        if len(ids) != 10:
            raise AssertionError(f"{label}: duplicate E6 image IDs")
        e6_ids_by_label[label] = ids
        e6_rows_by_label[label] = {str(r["image"]): r for r in rows}
        summary = {m: summarize_metric(rows, m, rng, a.bootstrap_resamples) for m in E6_METRICS}
        summary["image_ids"] = sorted(ids)
        summary["source_metrics_sha256"] = sha256(path)
        out["e6"][label] = summary

    e6_labels = [label for label, _ in a.e6]
    if e6_labels:
        reference = e6_labels[0]
        for label in e6_labels[1:]:
            if e6_ids_by_label[label] != e6_ids_by_label[reference]:
                raise AssertionError(f"E6 paired comparison {reference}->{label} does not share the exact same 10 test images")
            ids = sorted(e6_ids_by_label[reference])
            paired = {}
            for m in E6_METRICS:
                d = np.asarray([
                    e6_rows_by_label[label][i][m] - e6_rows_by_label[reference][i][m]
                    for i in ids
                ], dtype=float)
                paired[m] = {
                    "reference": reference,
                    "comparison": label,
                    "mean_delta": float(d.mean()),
                    "median_delta": float(np.median(d)),
                    "positive": int((d > 0).sum()),
                    "zero": int((d == 0).sum()),
                    "negative": int((d < 0).sum()),
                    "bootstrap95_mean_delta_ci": bootstrap_mean_ci(d, rng, a.bootstrap_resamples),
                }
            out.setdefault("e6", {}).setdefault("paired_descriptive_changes", {})[f"{reference}_vs_{label}"] = paired

    e7_path = Path(a.e7)
    e7 = load_json(e7_path)
    rows7 = e7.get("per_image", [])
    if len(rows7) != 670 or e7.get("n_images") != 670:
        raise AssertionError(f"E7 expected 670 images, got {len(rows7)}")
    out["e7"]["n_images"] = 670
    out["e7"]["metrics"] = {m: summarize_metric(rows7, m, rng, a.bootstrap_resamples) for m in E7_METRICS}
    out["e7"]["source_metrics_sha256"] = sha256(e7_path)

    def lowest(metric: str, k: int = 20) -> list[dict[str, Any]]:
        return [
            {
                "image_id": r["image_id"],
                "image": r["image"],
                metric: float(r[metric]),
                "target_instances": int(r["target_instances"]),
                "predicted_instances": int(r["predicted_instances"]),
            }
            for r in sorted(rows7, key=lambda z: float(z[metric]))[:k]
        ]

    ratios = []
    for r in rows7:
        target = max(int(r["target_instances"]), 1)
        pred = int(r["predicted_instances"])
        ratios.append({
            "image_id": r["image_id"],
            "image": r["image"],
            "prediction_target_ratio": float(pred / target),
            "target_instances": target,
            "predicted_instances": pred,
        })
    out["e7"]["failure_analysis"] = {
        "lowest_aji": lowest("aji"),
        "lowest_dice": lowest("dice"),
        "lowest_boundary_f1": lowest("boundary_f1"),
        "highest_prediction_target_ratios": sorted(ratios, key=lambda x: x["prediction_target_ratio"], reverse=True)[:20],
        "zero_predicted_instances": sum(1 for r in rows7 if int(r["predicted_instances"]) == 0),
        "target_instance_count_min": min(int(r["target_instances"]) for r in rows7),
        "target_instance_count_max": max(int(r["target_instances"]) for r in rows7),
    }
    out["e7"]["per_image"] = rows7

    out_path = Path(a.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out_path}")


if __name__ == "__main__": main()
