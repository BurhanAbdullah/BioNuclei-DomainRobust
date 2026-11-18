from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _workflow(path):
    return yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_zero_shot_only_consumes_main_baseline_runs():
    workflow = _workflow(ROOT / ".github/workflows/s_biad634_zero_shot.yml")
    triggers = workflow["on"]
    assert "push" not in triggers
    assert triggers["workflow_run"]["branches"] == ["main"]
    job_condition = workflow["jobs"]["zero-shot"]["if"]
    assert "github.event.workflow_run.head_branch == 'main'" in job_condition

    select = next(
        step for step in workflow["jobs"]["zero-shot"]["steps"]
        if step.get("name") == "Select and verify exact-main baseline run"
    )
    script = select["run"]
    for required in (
        "commits/main",
        "head_branch",
        "conclusion",
        "head_sha",
        "CURRENT_MAIN_SHA",
        "bbbc039_baseline.yml",
        "Refusing to evaluate",
    ):
        assert required in script, required


def test_baseline_training_is_main_only_and_triggers_transfer_inputs():
    workflow = _workflow(ROOT / ".github/workflows/bbbc039_baseline.yml")
    push = workflow["on"]["push"]
    assert push["branches"] == ["main"]
    paths = push["paths"]
    for required in (
        "scripts/evaluate_s_biad634.py",
        "scripts/metrics_instance.py",
        "scripts/download_s_biad634.py",
        ".github/workflows/s_biad634_zero_shot.yml",
    ):
        assert required in paths


def test_zero_shot_provenance_binds_checkpoint_to_baseline_and_evaluator():
    workflow = _workflow(ROOT / ".github/workflows/s_biad634_zero_shot.yml")
    step = next(
        step for step in workflow["jobs"]["zero-shot"]["steps"]
        if step.get("name") == "Record evaluation provenance"
    )
    script = step["run"]
    for required in (
        "evaluation_commit",
        "baseline_run_sha",
        "baseline_branch",
        "checkpoint_sha256",
    ):
        assert required in script, required
