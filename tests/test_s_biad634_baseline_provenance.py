from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.verify_bbbc039_baseline_run import validate_baseline_run


EXPECTED_SHA = "d4a653e94501e8b9f1ec9de09ff71720f90ab340"


def baseline_run(**overrides):
    metadata = {
        "id": 42582135791,
        "name": "BBBC039 baseline experiment",
        "head_branch": "main",
        "head_sha": EXPECTED_SHA,
        "status": "completed",
        "conclusion": "success",
    }
    metadata.update(overrides)
    return metadata


def test_accepts_successful_baseline_from_exact_main_commit():
    assert validate_baseline_run(baseline_run(), EXPECTED_SHA) == {
        "run_id": "42582135791",
        "baseline_sha": EXPECTED_SHA,
    }


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"head_branch": "fix/untrusted-pr"}, "must originate from main"),
        ({"head_sha": "b" * 40}, "does not match"),
        ({"conclusion": "failure"}, "completed successfully"),
        ({"status": "in_progress"}, "completed successfully"),
        ({"name": "unrelated workflow"}, "not the BBBC039 baseline"),
        ({"id": 0}, "valid run ID"),
    ],
)
def test_rejects_untrusted_or_stale_baseline_run(overrides, message):
    with pytest.raises(ValueError, match=message):
        validate_baseline_run(baseline_run(**overrides), EXPECTED_SHA)


def test_rejects_malformed_expected_commit_sha():
    with pytest.raises(ValueError, match="full lowercase 40-character commit"):
        validate_baseline_run(baseline_run(), "not-a-commit")


def test_zero_shot_workflow_only_accepts_main_baseline_and_records_its_identity():
    workflow_path = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "s_biad634_zero_shot.yml"
    )
    workflow = yaml.load(
        workflow_path.read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )

    assert "push" not in workflow["on"]
    assert workflow["on"]["workflow_run"]["branches"] == ["main"]
    job = workflow["jobs"]["zero-shot"]
    condition = job["if"]
    assert "github.ref == 'refs/heads/main'" in condition
    assert "github.event.workflow_run.head_branch == 'main'" in condition
    assert "github.event.workflow_run.head_sha == github.sha" in condition

    steps = job["steps"]
    selection = next(step for step in steps if step.get("name") == "Select baseline run")
    assert "verify_bbbc039_baseline_run.py" in selection["run"]
    assert "head_sha=$GITHUB_SHA" in selection["run"]

    provenance = next(step for step in steps if step.get("name") == "Record evaluation provenance")
    assert "baseline_commit_sha" in provenance["run"]
    assert "baseline_checkpoint_sha256" in provenance["run"]
