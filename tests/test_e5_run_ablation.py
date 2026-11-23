from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.e5_run_ablation import bind_metrics_digest, verify_metrics_digest


def test_e5_provenance_binds_exact_metrics_bytes(tmp_path: Path) -> None:
    metrics = tmp_path / "outputs" / "e5" / "full_frozen_e4" / "evaluation" / "metrics.json"
    metrics.parent.mkdir(parents=True)
    metrics.write_bytes(b'{"n_images":79,"mean":{"dice":0.3}}\n')
    provenance = bind_metrics_digest(
        {"experiment": "e5_full_frozen_e4"},
        metrics,
    )
    provenance["metrics_file"] = str(metrics.relative_to(tmp_path))

    expected = hashlib.sha256(metrics.read_bytes()).hexdigest()
    assert provenance["metrics_sha256"] == expected
    assert verify_metrics_digest(provenance, root=tmp_path) == expected


def test_e5_provenance_rejects_changed_metrics(tmp_path: Path) -> None:
    metrics = tmp_path / "outputs" / "e5" / "no_contrast" / "evaluation" / "metrics.json"
    metrics.parent.mkdir(parents=True)
    metrics.write_text('{"n_images":79}\n', encoding="utf-8")
    provenance = bind_metrics_digest(
        {"experiment": "e5_no_contrast"},
        metrics,
    )
    provenance["metrics_file"] = str(metrics.relative_to(tmp_path))
    metrics.write_text('{"n_images":78}\n', encoding="utf-8")

    with pytest.raises(RuntimeError, match="metrics SHA-256 mismatch"):
        verify_metrics_digest(provenance, root=tmp_path)


def test_e5_provenance_rejects_missing_or_malformed_digest(tmp_path: Path) -> None:
    metrics = tmp_path / "metrics.json"
    metrics.write_text('{"n_images":79}\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="missing a valid metrics SHA-256"):
        verify_metrics_digest(
            {"metrics_file": str(metrics)},
            root=tmp_path,
        )
