from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
import yaml

from scripts.validate_tiled_checkpoint import (
    persist_validation_evidence,
    resolve_revision_provenance,
    sha256_file,
)


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


def test_constrained_memory_validation_uses_production_image_thread_defaults() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.load(
        (root / ".github" / "workflows" / "tiled-checkpoint-validation.yml").read_text(
            encoding="utf-8"
        ),
        Loader=yaml.BaseLoader,
    )
    triggers = workflow["on"]
    for event in ("pull_request", "push"):
        assert "webapp/community.Dockerfile" in triggers[event]["paths"]

    steps = workflow["jobs"]["released-checkpoint"]["steps"]
    build_step = next(
        step for step in steps
        if step.get("name") == "Build production community image for constrained-memory validation"
    )
    assert "--file webapp/community.Dockerfile" in build_step["run"]

    memory_step = next(
        step for step in steps
        if step.get("name") == "Run real checkpoint worker with a 480 MiB hard memory limit"
    )
    command = memory_step["run"]
    # Keep the validation harness outside the production image while mounting
    # only the single read-only validator at the path it expects under /app.
    assert 'VALIDATOR_DIR="$RUNNER_TEMP/bionuclei-validation-scripts"' in command
    assert 'cp scripts/validate_tiled_checkpoint.py "$VALIDATOR_DIR/validate_tiled_checkpoint.py"' in command
    assert '--volume "$VALIDATOR_DIR:/app/scripts:ro"' in command
    assert "python scripts/validate_tiled_checkpoint.py" in command
    for variable in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        assert f"--env {variable}=1" not in command
    assert "for variable in OMP_NUM_THREADS MKL_NUM_THREADS OPENBLAS_NUM_THREADS NUMEXPR_NUM_THREADS; do" in command
    assert 'value="$(printenv "$variable" 2>/dev/null || true)"' in command
    assert 'if [ "$value" != "1" ]; then' in command
    assert "--memory=503316480" in command
    assert '[ "$memory_peak" -le 492830720 ]' in command


def test_both_production_images_use_the_same_single_thread_defaults() -> None:
    root = Path(__file__).resolve().parents[1]
    variables = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS")
    for relative in ("webapp/Dockerfile", "webapp/community.Dockerfile"):
        env_block = (root / relative).read_text(encoding="utf-8").split("\n\n", 2)[1]
        for variable in variables:
            assert f"{variable}=1" in env_block, f"{relative} is missing {variable}=1"


def test_pull_request_manifest_binds_source_base_and_tested_merge_commits() -> None:
    source_sha = "a" * 40
    base_sha = "b" * 40
    merge_sha = "c" * 40

    provenance = resolve_revision_provenance(
        "pull_request",
        merge_sha,
        {
            "pull_request": {
                "head": {"sha": source_sha},
                "base": {"sha": base_sha},
            }
        },
    )

    assert provenance == {
        "event_name": "pull_request",
        "head_sha": source_sha,
        "base_sha": base_sha,
        "tested_sha": merge_sha,
    }


def test_push_manifest_uses_the_pushed_commit_as_source_and_tested_sha() -> None:
    pushed_sha = "d" * 40

    provenance = resolve_revision_provenance("push", pushed_sha)

    assert provenance == {
        "event_name": "push",
        "head_sha": pushed_sha,
        "base_sha": None,
        "tested_sha": pushed_sha,
    }


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"pull_request": {"head": {"sha": "a" * 40}}},
        {
            "pull_request": {
                "head": {"sha": "not-a-sha"},
                "base": {"sha": "b" * 40},
            }
        },
    ],
)
def test_pull_request_provenance_fails_closed_without_valid_head_and_base(payload) -> None:
    with pytest.raises(ValueError):
        resolve_revision_provenance("pull_request", "c" * 40, payload)


def test_revision_provenance_rejects_invalid_workflow_sha() -> None:
    with pytest.raises(ValueError, match="GITHUB_SHA"):
        resolve_revision_provenance("push", "not-a-sha")
