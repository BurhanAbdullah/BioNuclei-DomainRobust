from __future__ import annotations

import json
import hashlib
import zipfile

import pytest

from scripts import validate_tiled_checkpoint as checkpoint


def _write_evidence_inputs(tmp_path):
    archive_path = tmp_path / "analysis-results.zip"
    result_path = tmp_path / "results.json"
    specialist_path = tmp_path / "expert_agents.json"
    result_bytes = b'{"scientific_execution": true}'
    specialist_bytes = b'{"execution": {"status": "completed"}}'
    result_path.write_bytes(result_bytes)
    specialist_path.write_bytes(specialist_bytes)
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("results/analysis_report.html", b"html")
        archive.writestr("results/analysis_report.pdf", b"pdf")
        archive.writestr("results/results.json", result_bytes)
        archive.writestr("results/expert_agents.json", specialist_bytes)
        archive.writestr("results/nuclei_analysis.csv", b"csv")
        archive.writestr("results/segmentation_mask.tif", b"mask")
        archive.writestr("results/overlay.tif", b"overlay")
    return archive_path, result_path, specialist_path


def test_resolve_revision_provenance_distinguishes_source_base_and_tested_merge():
    head_sha = "a" * 40
    base_sha = "b" * 40
    tested_sha = "c" * 40
    payload = {
        "pull_request": {
            "head": {"sha": head_sha},
            "base": {"sha": base_sha},
        }
    }

    provenance = checkpoint.resolve_revision_provenance("pull_request", tested_sha, payload)

    assert provenance == {
        "event_name": "pull_request",
        "head_sha": head_sha,
        "base_sha": base_sha,
        "tested_sha": tested_sha,
    }


def test_resolve_revision_provenance_rejects_missing_or_invalid_pr_sha():
    payload = {
        "pull_request": {
            "head": {"sha": "not-a-full-sha"},
            "base": {"sha": "b" * 40},
        }
    }

    with pytest.raises(ValueError, match="valid source head SHA"):
        checkpoint.resolve_revision_provenance("pull_request", "c" * 40, payload)


def test_persist_validation_evidence_hashes_all_outputs_and_manifest(tmp_path):
    temporary_root = tmp_path / "disposable-worker"
    temporary_root.mkdir()
    archive_path, result_path, specialist_path = _write_evidence_inputs(tmp_path)
    evidence_dir = tmp_path / "runner-evidence"
    manifest = {
        "schema_version": 2,
        "head_sha": "a" * 40,
        "base_sha": "b" * 40,
        "tested_sha": "c" * 40,
        "source_image_excluded": True,
        "checkpoint_unchanged": True,
        "specialist_count": 8,
        "public_inference": False,
    }

    persisted = checkpoint.persist_validation_evidence(
        evidence_dir,
        temporary_root,
        archive_path,
        result_path,
        specialist_path,
        manifest,
    )

    written = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    assert set(persisted["files"]) == {"analysis-results.zip", "results.json", "expert_agents.json"}
    assert written["head_sha"] == "a" * 40
    assert written["base_sha"] == "b" * 40
    assert written["tested_sha"] == "c" * 40
    assert written["files"]["analysis-results.zip"]["sha256"] == hashlib.sha256(
        (evidence_dir / "analysis-results.zip").read_bytes()
    ).hexdigest()
    assert written["files"]["results.json"]["sha256"] == hashlib.sha256(
        (evidence_dir / "results.json").read_bytes()
    ).hexdigest()
    assert written["files"]["expert_agents.json"]["sha256"] == hashlib.sha256(
        (evidence_dir / "expert_agents.json").read_bytes()
    ).hexdigest()
    assert persisted["manifest_sha256"] == hashlib.sha256(
        (evidence_dir / "manifest.json").read_bytes()
    ).hexdigest()


def test_persist_validation_evidence_rejects_unverified_or_public_manifest(tmp_path):
    temporary_root = tmp_path / "disposable-worker"
    temporary_root.mkdir()
    archive_path, result_path, specialist_path = _write_evidence_inputs(tmp_path)
    manifest = {
        "source_image_excluded": False,
        "checkpoint_unchanged": True,
        "specialist_count": 8,
        "public_inference": False,
    }

    with pytest.raises(AssertionError, match="source-image exclusion"):
        checkpoint.persist_validation_evidence(
            tmp_path / "runner-evidence",
            temporary_root,
            archive_path,
            result_path,
            specialist_path,
            manifest,
        )
