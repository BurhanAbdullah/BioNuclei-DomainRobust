from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.validate_bbbc039_baseline import (
    is_baseline_input_change,
    validate_baseline_provenance,
)

REPOSITORY = "BurhanAbdullah/BioNuclei-DomainRobust"
BASELINE_SHA = "1" * 40
EVALUATION_SHA = "2" * 40
ARTIFACT_DIGEST = "sha256:" + "a" * 64


def valid_inputs():
    run = {
        "id": 12345,
        "name": "BBBC039 baseline experiment",
        "path": ".github/workflows/bbbc039_baseline.yml@refs/heads/main",
        "head_branch": "main",
        "head_sha": BASELINE_SHA,
        "status": "completed",
        "conclusion": "success",
        "event": "push",
        "created_at": "2026-11-01T12:00:00Z",
        "html_url": "https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/12345",
        "repository": {"full_name": REPOSITORY},
        "head_repository": {"full_name": REPOSITORY},
    }
    artifacts = {
        "artifacts": [
            {
                "id": 67890,
                "name": "bbbc039-baseline-12345",
                "size_in_bytes": 1024,
                "expired": False,
                "digest": ARTIFACT_DIGEST,
            }
        ]
    }
    comparison = {
        "status": "ahead",
        "merge_base_commit": {"sha": BASELINE_SHA},
        "files": [
            {"filename": "scripts/evaluate_s_biad634.py"},
            {"filename": "docs/RESEARCH_PROTOCOL.md"},
        ],
    }
    return run, artifacts, comparison


def test_accepts_main_ancestor_with_only_downstream_changes() -> None:
    run, artifacts, comparison = valid_inputs()

    result = validate_baseline_provenance(
        run,
        artifacts,
        comparison,
        expected_sha=EVALUATION_SHA,
        repository=REPOSITORY,
    )

    assert result["baseline_run_id"] == 12345
    assert result["baseline_head_branch"] == "main"
    assert result["baseline_head_sha"] == BASELINE_SHA
    assert result["baseline_artifact_id"] == 67890
    assert result["baseline_artifact_digest"] == ARTIFACT_DIGEST
    assert result["baseline_training_inputs_unchanged"] is True
    assert result["evaluation_commit"] == EVALUATION_SHA


def test_rejects_baseline_run_from_pull_request_branch() -> None:
    run, artifacts, comparison = valid_inputs()
    run["head_branch"] = "security/secure-hosted-biomcp-http-20261115-1417"

    with pytest.raises(ValueError, match="must come from main"):
        validate_baseline_provenance(
            run, artifacts, comparison,
            expected_sha=EVALUATION_SHA, repository=REPOSITORY,
        )


def test_rejects_non_ancestor_baseline() -> None:
    run, artifacts, comparison = valid_inputs()
    comparison["status"] = "diverged"

    with pytest.raises(ValueError, match="not an ancestor"):
        validate_baseline_provenance(
            run, artifacts, comparison,
            expected_sha=EVALUATION_SHA, repository=REPOSITORY,
        )


def test_rejects_baseline_when_training_inputs_changed() -> None:
    run, artifacts, comparison = valid_inputs()
    comparison["files"].append({"filename": "src/bionuclei/models.py"})

    with pytest.raises(ValueError, match="training/evaluation inputs changed"):
        validate_baseline_provenance(
            run, artifacts, comparison,
            expected_sha=EVALUATION_SHA, repository=REPOSITORY,
        )


def test_unrelated_main_branch_scripts_do_not_invalidate_baseline() -> None:
    unrelated_paths = (
        "scripts/aggregate_e6_fraction_evidence.py",
        "scripts/download_aitslab_bioimaging1.py",
        "scripts/live_public_agent_e2e.py",
        "scripts/public_e2e_schedule_watchdog.py",
        "scripts/download_s_biad634.py",
    )
    for path in unrelated_paths:
        assert is_baseline_input_change(path) is False, path


def test_unknown_script_changes_fail_closed() -> None:
    assert is_baseline_input_change("scripts/new_training_pipeline.py") is True
    assert is_baseline_input_change("scripts/train_bbbc039.py") is True
    assert is_baseline_input_change("scripts/evaluate_s_biad634.py") is False
    assert is_baseline_input_change(".github/workflows/bbbc039_baseline.yml") is True


def test_rejects_expired_or_unverifiable_artifact() -> None:
    run, artifacts, comparison = valid_inputs()
    artifacts["artifacts"][0]["expired"] = True

    with pytest.raises(ValueError, match="expired"):
        validate_baseline_provenance(
            run, artifacts, comparison,
            expected_sha=EVALUATION_SHA, repository=REPOSITORY,
        )

    artifacts["artifacts"][0]["expired"] = False
    artifacts["artifacts"][0]["digest"] = None
    with pytest.raises(ValueError, match="SHA-256 digest"):
        validate_baseline_provenance(
            run, artifacts, comparison,
            expected_sha=EVALUATION_SHA, repository=REPOSITORY,
        )


def test_zero_shot_workflow_is_main_only() -> None:
    workflow_path = Path(".github/workflows/s_biad634_zero_shot.yml")
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

    assert workflow["on"]["push"]["branches"] == ["main"]
    assert workflow["on"]["workflow_run"]["branches"] == ["main"]
    assert "refs/heads/main" in workflow["jobs"]["zero-shot"]["if"]
