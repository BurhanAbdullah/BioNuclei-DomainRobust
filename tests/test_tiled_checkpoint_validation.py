from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from scripts.validate_tiled_checkpoint import persist_validation_evidence, sha256_file


def _sources(root: Path) -> tuple[Path, Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    archive = root / "results.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("results/results.json", "{}")
        zipped.writestr("results/expert_agents.json", "[]")
    result = root / "results.json"
    result.write_text('{"status":"completed"}', encoding="utf-8")
    specialists = root / "expert_agents.json"
    specialists.write_text('{"agents":[1,2,3,4,5,6,7,8]}', encoding="utf-8")
    return archive, result, specialists


def test_persist_validation_evidence_copies_only_verified_derived_outputs(tmp_path: Path) -> None:
    temporary_root = tmp_path / "disposable-job"
    archive, result, specialists = _sources(temporary_root)
    evidence_dir = tmp_path / "runner-evidence"
    manifest = {
        "specialist_count": 8,
        "source_image_excluded": True,
        "checkpoint_unchanged": True,
        "public_inference": False,
    }

    persisted = persist_validation_evidence(
        evidence_dir,
        temporary_root,
        archive,
        result,
        specialists,
        manifest,
    )

    assert {path.name for path in evidence_dir.iterdir()} == {
        "analysis-results.zip",
        "results.json",
        "expert_agents.json",
        "manifest.json",
    }
    assert sha256_file(evidence_dir / "analysis-results.zip") == sha256_file(archive)
    assert sha256_file(evidence_dir / "results.json") == sha256_file(result)
    assert sha256_file(evidence_dir / "expert_agents.json") == sha256_file(specialists)
    saved = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    assert saved["source_image_excluded"] is True
    assert saved["public_inference"] is False
    assert saved["files"]["analysis-results.zip"]["sha256"] == sha256_file(archive)
    assert persisted["manifest_sha256"] == sha256_file(evidence_dir / "manifest.json")


def test_persist_validation_evidence_rejects_disposable_job_subdirectory(tmp_path: Path) -> None:
    temporary_root = tmp_path / "disposable-job"
    archive, result, specialists = _sources(temporary_root)
    manifest = {
        "specialist_count": 8,
        "source_image_excluded": True,
        "checkpoint_unchanged": True,
        "public_inference": False,
    }

    with pytest.raises(AssertionError, match="outside disposable job storage"):
        persist_validation_evidence(
            temporary_root / "evidence",
            temporary_root,
            archive,
            result,
            specialists,
            manifest,
        )
