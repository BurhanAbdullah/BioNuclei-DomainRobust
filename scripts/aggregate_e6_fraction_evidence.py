#!/usr/bin/env python3
"""Validate and aggregate E6 fraction evidence from downloaded Actions artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_FRACTIONS = (
    ("01pct", 0.01, 1),
    ("05pct", 0.05, 2),
    ("10pct", 0.10, 3),
    ("25pct", 0.25, 8),
)
REQUIRED_METRICS = ("dice", "iou", "aji", "boundary_f1")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read valid JSON evidence at {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object at {path}")
    return value


def _find_fraction_run(root: Path, fraction: float) -> tuple[Path, dict[str, Any]]:
    """Find one run by its provenance, independent of artifact directory layout."""
    matches: list[tuple[Path, dict[str, Any]]] = []
    for provenance_path in root.rglob("provenance.json"):
        provenance = _read_json(provenance_path)
        if provenance.get("fraction") == fraction:
            matches.append((provenance_path.parent, provenance))
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one provenance record for fraction {fraction}; "
            f"found {len(matches)} under {root}"
        )
    return matches[0]


def aggregate_evidence(root: Path) -> dict[str, Any]:
    """Validate each preregistered fraction and return a deterministic summary."""
    if not root.is_dir():
        raise ValueError(f"Evidence root does not exist: {root}")

    rows: list[dict[str, Any]] = []
    for label, fraction, image_count in EXPECTED_FRACTIONS:
        run, provenance = _find_fraction_run(root, fraction)
        expected = {
            "fraction": fraction,
            "n_adaptation_images": image_count,
            "seed": 42,
            "epochs": 20,
        }
        for key, value in expected.items():
            if provenance.get(key) != value:
                raise ValueError(
                    f"{label}: provenance {key}={provenance.get(key)!r}; expected {value!r}"
                )
        for key in (
            "s_biad634_used_for_adaptation",
            "test_images_used_for_adaptation",
            "development_images_used_for_training_or_selection",
        ):
            if provenance.get(key) is not False:
                raise ValueError(f"{label}: leakage guard {key} must be false")
        if not provenance.get("dataset_archive_sha256"):
            raise ValueError(f"{label}: missing dataset archive digest")
        if not provenance.get("train_command") or not provenance.get("evaluation_command"):
            raise ValueError(f"{label}: missing training/evaluation command provenance")

        metrics_path = run / "evaluation" / "test_metrics.json"
        metrics = _read_json(metrics_path)
        if metrics.get("n_images") != 10:
            raise ValueError(f"{label}: expected 10 test images")
        means = metrics.get("mean")
        if not isinstance(means, dict) or not all(key in means for key in REQUIRED_METRICS):
            raise ValueError(f"{label}: missing required test metrics")
        metrics_digest = hashlib.sha256(metrics_path.read_bytes()).hexdigest()
        if metrics_digest != provenance.get("test_metrics_sha256"):
            raise ValueError(f"{label}: test-metrics SHA-256 does not match provenance")

        provenance_path = run / "provenance.json"
        rows.append(
            {
                "label": label,
                "fraction": fraction,
                "n_adaptation_images": image_count,
                "mean": means,
                "metrics_sha256": metrics_digest,
                "provenance_sha256": hashlib.sha256(provenance_path.read_bytes()).hexdigest(),
            }
        )

    return {
        "protocol": "E6_cross_dataset_few_shot",
        "fractions": rows,
        "all_four_fractions_verified": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = aggregate_evidence(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("E6 aggregate evidence cross-check: PASS")


if __name__ == "__main__":
    main()
