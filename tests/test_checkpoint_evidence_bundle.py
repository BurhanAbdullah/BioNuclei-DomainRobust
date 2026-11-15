from __future__ import annotations

import json
import hashlib
import zipfile

import pytest

from scripts import validate_tiled_checkpoint as checkpoint


def _write_archive(
    archive_path,
    *,
    omitted=(),
    empty=(),
    extra=None,
    result_bytes=b'{"scientific_execution": true}',
    specialist_bytes=b'{"execution": {"status": "completed"}}',
):
    entries = {
        "results/analysis_report.html": b"html",
        "results/analysis_report.json": b"{}",
        "results/analysis_report.pdf": b"pdf",
        "results/measurements.csv": b"id,intensity\n1,65535\n",
        "results/results.json": result_bytes,
        "results/expert_agents.json": specialist_bytes,
        "results/nuclei_analysis.csv": b"csv",
        "results/segmentation_mask.tif": b"mask",
        "results/overlay.tif": b"overlay",
        "results/provenance.json": b"{}",
    }
    omitted = set(omitted)
    empty = set(empty)
    with zipfile.ZipFile(archive_path, "w") as archive:
        for name, payload in entries.items():
            if name not in omitted:
                archive.writestr(name, b"" if name in empty else payload)
        for name, payload in (extra or {}).items():
            archive.writestr(name, payload)


def _write_evidence_inputs(tmp_path):
    archive_path = tmp_path / "analysis-results.zip"
    result_path = tmp_path / "results.json"
    specialist_path = tmp_path / "expert_agents.json"
    result_bytes = b'{"scientific_execution": true}'
    specialist_bytes = b'{"execution": {"status": "completed"}}'
    result_path.write_bytes(result_bytes)
    specialist_path.write_bytes(specialist_bytes)
    _write_archive(archive_path, result_bytes=result_bytes, specialist_bytes=specialist_bytes)
    return archive_path, result_path, specialist_path



def test_validate_result_archive_requires_all_downloadable_deliverables(tmp_path):
    archive_path = tmp_path / "complete.zip"
    _write_archive(archive_path)

    names = set(
        checkpoint.validate_result_archive(
            archive_path,
            "live-uint16-sentinel.tif",
            hashlib.sha256(b"uploaded source bytes").hexdigest(),
        )
    )

    assert {
        "results/measurements.csv",
        "results/analysis_report.json",
        "results/provenance.json",
    }.issubset(names)


@pytest.mark.parametrize(
    "missing",
    [
        "results/measurements.csv",
        "results/analysis_report.json",
        "results/provenance.json",
    ],
)
def test_validate_result_archive_rejects_missing_required_deliverables(tmp_path, missing):
    archive_path = tmp_path / "incomplete.zip"
    _write_archive(archive_path, omitted={missing})

    with pytest.raises(AssertionError, match="ZIP missing required artifacts"):
        checkpoint.validate_result_archive(
            archive_path,
            "live-uint16-sentinel.tif",
            hashlib.sha256(b"uploaded source bytes").hexdigest(),
        )


def test_validate_result_archive_rejects_empty_required_deliverable(tmp_path):
    archive_path = tmp_path / "empty-output.zip"
    _write_archive(archive_path, empty={"results/measurements.csv"})

    with pytest.raises(AssertionError, match="ZIP contains empty required artifacts"):
        checkpoint.validate_result_archive(
            archive_path,
            "live-uint16-sentinel.tif",
            hashlib.sha256(b"uploaded source bytes").hexdigest(),
        )


def test_validate_result_archive_rejects_source_image_and_corrupt_zip(tmp_path):
    archive_path = tmp_path / "source-leak.zip"
    _write_archive(
        archive_path,
        extra={"results/live-uint16-sentinel.tif": b"source image"},
    )

    with pytest.raises(AssertionError, match="uploaded source image"):
        checkpoint.validate_result_archive(
            archive_path,
            "live-uint16-sentinel.tif",
            hashlib.sha256(b"source image").hexdigest(),
        )

    corrupt_path = tmp_path / "corrupt.zip"
    _write_archive(corrupt_path)
    data = bytearray(corrupt_path.read_bytes())
    data[-8] ^= 0xFF
    corrupt_path.write_bytes(data)
    with pytest.raises((AssertionError, zipfile.BadZipFile)):
        checkpoint.validate_result_archive(
            corrupt_path,
            "live-uint16-sentinel.tif",
            hashlib.sha256(b"uploaded source bytes").hexdigest(),
        )


def test_validate_result_archive_rejects_source_bytes_under_a_renamed_member(tmp_path):
    source_bytes = b"exact uploaded source image bytes"
    archive_path = tmp_path / "renamed-source.zip"
    _write_archive(
        archive_path,
        extra={"results/renamed-upload.bin": source_bytes},
    )

    with pytest.raises(AssertionError, match="uploaded source image bytes"):
        checkpoint.validate_result_archive(
            archive_path,
            "live-uint16-sentinel.tif",
            hashlib.sha256(source_bytes).hexdigest(),
        )


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
