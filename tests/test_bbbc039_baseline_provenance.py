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
        "base_commit": {"sha": BASELINE_SHA},
        "merge_base_commit": {"sha": BASELINE_SHA},
        "total_commits": 1,
        "commits": [{"sha": EVALUATION_SHA}],
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


@pytest.mark.parametrize("event", ["pull_request", "workflow_dispatch"])
def test_rejects_non_push_baseline_events_even_when_branch_and_repository_match(event: str) -> None:
    run, artifacts, comparison = valid_inputs()
    run["event"] = event

    with pytest.raises(ValueError, match="event must be a reproducible main-branch push"):
        validate_baseline_provenance(
            run, artifacts, comparison,
            expected_sha=EVALUATION_SHA, repository=REPOSITORY,
        )


def test_rejects_missing_or_foreign_head_repository() -> None:
    run, artifacts, comparison = valid_inputs()
    run["head_repository"] = None

    with pytest.raises(ValueError, match="head repository mismatch"):
        validate_baseline_provenance(
            run, artifacts, comparison,
            expected_sha=EVALUATION_SHA, repository=REPOSITORY,
        )

    run["head_repository"] = {"full_name": "untrusted/fork"}
    with pytest.raises(ValueError, match="head repository mismatch"):
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


def test_rejects_comparison_for_a_different_evaluation_commit() -> None:
    run, artifacts, comparison = valid_inputs()
    comparison["commits"][-1]["sha"] = "3" * 40

    with pytest.raises(ValueError, match="head does not match"):
        validate_baseline_provenance(
            run, artifacts, comparison,
            expected_sha=EVALUATION_SHA, repository=REPOSITORY,
        )


def test_rejects_truncated_comparison_commit_list() -> None:
    run, artifacts, comparison = valid_inputs()
    comparison["total_commits"] = 250

    with pytest.raises(ValueError, match="truncated commit details"):
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


def test_actual_main_baseline_remains_eligible_after_nontraining_changes() -> None:
    baseline_sha = "bb6a9d27537e12b85768c7fead1467253b2423ba"
    evaluation_sha = "d4a653e94501e8b9f1ec9de09ff71720f90ab340"
    run = {
        "id": 39988978232,
        "name": "BBBC039 baseline experiment",
        "path": ".github/workflows/bbbc039_baseline.yml",
        "head_branch": "main",
        "head_sha": baseline_sha,
        "status": "completed",
        "conclusion": "success",
        "event": "push",
        "created_at": "2026-10-23T16:42:17Z",
        "html_url": "https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/actions/runs/39988978232",
        "repository": {"full_name": REPOSITORY},
        "head_repository": {"full_name": REPOSITORY},
    }
    artifacts = {
        "artifacts": [
            {
                "id": 12521621402,
                "name": "bbbc039-baseline-39988978232",
                "size_in_bytes": 7122879,
                "expired": False,
                "digest": "sha256:9d50a5e1a6488bf9032c591f3f3bab862bc46faff6b1f2999cd7e0fdecd4d4fe",
            }
        ]
    }
    comparison = {
        "status": "ahead",
        "base_commit": {"sha": baseline_sha},
        "merge_base_commit": {"sha": baseline_sha},
        "total_commits": 12,
        "commits": [{"sha": f"{i:040x}"} for i in range(1, 12)] + [{"sha": evaluation_sha}],
        "files": [
            {"filename": ".github/workflows/e6_e7_uncertainty_analysis.yml"},
            {"filename": ".github/workflows/e6_external_few_shot.yml"},
            {"filename": ".github/workflows/e6_retry_watchdog.yml"},
            {"filename": ".github/workflows/live-public-agent-e2e.yml"},
            {"filename": ".github/workflows/public-e2e-schedule-watchdog.yml"},
            {"filename": "docs/ANALYZER_WORKER_ARCHITECTURE.md"},
            {"filename": "scripts/aggregate_e6_fraction_evidence.py"},
            {"filename": "scripts/download_aitslab_bioimaging1.py"},
            {"filename": "scripts/live_public_agent_e2e.py"},
            {"filename": "scripts/public_e2e_schedule_watchdog.py"},
            {"filename": "tests/test_aitslab_download.py"},
            {"filename": "tests/test_community_cors.py"},
            {"filename": "tests/test_community_failure_cleanup.py"},
            {"filename": "tests/test_community_progress.py"},
            {"filename": "tests/test_e6_aggregate_evidence.py"},
            {"filename": "tests/test_public_e2e_schedule_watchdog.py"},
            {"filename": "webapp/community.py"},
            {"filename": "webapp/community_app.py"},
        ],
    }

    result = validate_baseline_provenance(
        run,
        artifacts,
        comparison,
        expected_sha=evaluation_sha,
        repository=REPOSITORY,
    )

    assert result["baseline_run_id"] == 39988978232
    assert result["baseline_head_sha"] == baseline_sha
    assert result["baseline_artifact_id"] == 12521621402
    assert result["baseline_artifact_digest"] == artifacts["artifacts"][0]["digest"]
    assert result["baseline_training_inputs_unchanged"] is True
    assert len(result["baseline_changed_paths"]) == 18


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


def test_only_known_unrelated_workflows_are_exempt() -> None:
    unrelated_workflows = (
        ".github/workflows/e6_e7_uncertainty_analysis.yml",
        ".github/workflows/e6_external_few_shot.yml",
        ".github/workflows/e6_retry_watchdog.yml",
        ".github/workflows/live-public-agent-e2e.yml",
        ".github/workflows/public-e2e-schedule-watchdog.yml",
        ".github/workflows/s_biad634_zero_shot.yml",
    )
    for path in unrelated_workflows:
        assert is_baseline_input_change(path) is False, path

    assert is_baseline_input_change(".github/workflows/new_training_workflow.yml") is True


def test_inference_postprocessing_is_downstream_but_model_changes_fail_closed() -> None:
    assert is_baseline_input_change("src/bionuclei/postprocessing.py") is False
    assert is_baseline_input_change("src/bionuclei/models.py") is True


def test_zero_shot_reruns_when_shared_postprocessing_changes() -> None:
    workflow_path = Path(".github/workflows/s_biad634_zero_shot.yml")
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert "src/bionuclei/postprocessing.py" in workflow["on"]["push"]["paths"]


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
    download = next(
        step for step in workflow["jobs"]["zero-shot"]["steps"]
        if step.get("name") == "Download baseline artifact"
    )
    assert download["uses"] == "actions/download-artifact@v8"
    assert download["with"]["digest-mismatch"] == "error"



def test_zero_shot_fallback_selects_only_completed_main_push_baselines() -> None:
    workflow_path = Path(".github/workflows/s_biad634_zero_shot.yml")
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    selection = next(
        step for step in workflow["jobs"]["zero-shot"]["steps"]
        if step.get("name") == "Select and validate main-branch baseline provenance"
    )

    assert "status=completed" in selection["run"]
    assert '.event == "push"' in selection["run"]
    assert '.head_branch == "main"' in selection["run"]
    assert '.conclusion == "success"' in selection["run"]


def test_zero_shot_checkpoint_loader_uses_weights_only(monkeypatch, tmp_path):
    from scripts import evaluate_s_biad634

    checkpoint_path = tmp_path / "baseline.pt"
    expected = {"model": {"weight": object()}, "config": {"model": {}}}
    observed = {}

    def safe_load(path, *, map_location, weights_only):
        observed.update(
            {
                "path": Path(path),
                "map_location": map_location,
                "weights_only": weights_only,
            }
        )
        return expected

    monkeypatch.setattr(evaluate_s_biad634.torch, "load", safe_load)

    assert evaluate_s_biad634.load_checkpoint(checkpoint_path) is expected
    assert observed == {
        "path": checkpoint_path,
        "map_location": "cpu",
        "weights_only": True,
    }
