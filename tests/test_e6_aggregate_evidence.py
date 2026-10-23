from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.aggregate_e6_fraction_evidence import aggregate_evidence


FRACTIONS = (("01pct", 0.01, 1), ("05pct", 0.05, 2), ("10pct", 0.10, 3), ("25pct", 0.25, 8))


def _write_run(root: Path, label: str, fraction: float, count: int) -> Path:
    # Match the nested paths produced by upload-artifact when multiple paths
    # (outputs/... and data/...) establish the repository as their common root.
    run = root / f"e6-fraction-{label}-12345" / "outputs" / "e6_external_few_shot" / label
    evaluation = run / "evaluation"
    evaluation.mkdir(parents=True)
    metrics_path = evaluation / "test_metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "n_images": 10,
                "mean": {"dice": 0.9, "iou": 0.8, "aji": 0.7, "boundary_f1": 0.6},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    provenance = {
        "fraction": fraction,
        "n_adaptation_images": count,
        "seed": 42,
        "epochs": 20,
        "s_biad634_used_for_adaptation": False,
        "test_images_used_for_adaptation": False,
        "development_images_used_for_training_or_selection": False,
        "dataset_archive_sha256": "a" * 64,
        "train_command": "python train.py --seed 42",
        "evaluation_command": "python evaluate.py",
        "test_metrics_sha256": hashlib.sha256(metrics_path.read_bytes()).hexdigest(),
    }
    (run / "provenance.json").write_text(
        json.dumps(provenance, sort_keys=True) + "\n", encoding="utf-8"
    )
    return run


def _fixture(root: Path) -> Path:
    for label, fraction, count in FRACTIONS:
        _write_run(root, label, fraction, count)
    return root


def test_aggregates_nested_downloaded_artifact_layout(tmp_path: Path) -> None:
    root = _fixture(tmp_path / "evidence")

    result = aggregate_evidence(root)

    assert result["all_four_fractions_verified"] is True
    assert [row["label"] for row in result["fractions"]] == [item[0] for item in FRACTIONS]
    assert [row["n_adaptation_images"] for row in result["fractions"]] == [1, 2, 3, 8]


def test_missing_fraction_fails_closed(tmp_path: Path) -> None:
    root = _fixture(tmp_path / "evidence")
    (root / "e6-fraction-25pct-12345" / "outputs" / "e6_external_few_shot" / "25pct" / "provenance.json").unlink()

    with pytest.raises(ValueError, match="Expected exactly one provenance record"):
        aggregate_evidence(root)


def test_duplicate_fraction_fails_closed(tmp_path: Path) -> None:
    root = _fixture(tmp_path / "evidence")
    duplicate = root / "duplicate-artifact" / "outputs" / "e6_external_few_shot" / "another-25pct"
    duplicate.mkdir(parents=True)
    source = root / "e6-fraction-25pct-12345" / "outputs" / "e6_external_few_shot" / "25pct"
    (duplicate / "provenance.json").write_bytes((source / "provenance.json").read_bytes())

    with pytest.raises(ValueError, match="Expected exactly one provenance record"):
        aggregate_evidence(root)


def test_metrics_digest_mismatch_fails_closed(tmp_path: Path) -> None:
    root = _fixture(tmp_path / "evidence")
    metrics = root / "e6-fraction-01pct-12345" / "outputs" / "e6_external_few_shot" / "01pct" / "evaluation" / "test_metrics.json"
    metrics.write_text('{"n_images":10,"mean":{"dice":0.1}}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="test-metrics SHA-256"):
        aggregate_evidence(root)
