from __future__ import annotations

import json
import zipfile
from types import SimpleNamespace

import pytest

from scripts import validate_tiled_checkpoint as checkpoint


def _write_results_archive(path):
    with zipfile.ZipFile(path, "w") as archive:
        for name in (
            "results/analysis_report.html",
            "results/analysis_report.pdf",
            "results/results.json",
            "results/expert_agents.json",
            "results/nuclei_analysis.csv",
            "results/segmentation_mask.tif",
            "results/overlay.tif",
        ):
            archive.writestr(name, b"validated")


def test_workflow_identity_distinguishes_source_base_and_tested_merge(monkeypatch, tmp_path):
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps({
            "pull_request": {
                "head": {"sha": "source-head"},
                "base": {"sha": "target-base"},
            }
        }),
        encoding="utf-8",
    )
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    monkeypatch.setenv("GITHUB_SHA", "github-merge")
    monkeypatch.setenv("GITHUB_RUN_ID", "12345")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_REF", "refs/pull/146/merge")
    monkeypatch.setattr(
        checkpoint.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="tested-merge\n"),
    )

    identity = checkpoint.workflow_identity()

    assert identity["schema_version"] == 2
    assert identity["head_sha"] == "source-head"
    assert identity["base_sha"] == "target-base"
    assert identity["tested_sha"] == "tested-merge"
    assert identity["github_sha"] == "github-merge"
    assert identity["run_id"] == "12345"
    assert identity["run_attempt"] == "2"


def test_persist_evidence_bundle_hashes_and_preserves_source_free_results(tmp_path):
    source = tmp_path / "analysis-results.zip"
    _write_results_archive(source)
    evidence_dir = tmp_path / "evidence"

    payload = checkpoint.persist_evidence_bundle(
        evidence_dir,
        source,
        {
            "status": "PASS",
            "head_sha": "source-head",
            "base_sha": "target-base",
            "tested_sha": "tested-merge",
            "source_image_excluded": True,
        },
    )

    copied = evidence_dir / "analysis-results.zip"
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    assert copied.read_bytes() == source.read_bytes()
    assert payload["results_zip_sha256"] == checkpoint.sha256_file(copied)
    assert manifest["results_zip_sha256"] == checkpoint.sha256_file(copied)
    assert manifest["head_sha"] == "source-head"
    assert manifest["base_sha"] == "target-base"
    assert manifest["tested_sha"] == "tested-merge"
    assert manifest["source_image_excluded"] is True
    assert "results/results.json" in manifest["results_zip_entries"]


def test_persist_evidence_bundle_rejects_source_image(tmp_path):
    source = tmp_path / "unsafe-results.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("results/results.json", b"validated")
        archive.writestr("results/input.tif", b"source pixels")

    with pytest.raises(AssertionError, match="contains the source image"):
        checkpoint.persist_evidence_bundle(tmp_path / "evidence", source, {"status": "PASS"})
