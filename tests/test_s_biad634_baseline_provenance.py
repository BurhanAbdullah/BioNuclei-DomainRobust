from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml

from scripts.verify_bbbc039_baseline_run import validate_baseline_run


EXPECTED_SHA = "d4a653e94501e8b9f1ec9de09ff71720f90ab340"


def baseline_run(**overrides):
    metadata = {
        "id": 12345,
        "name": "BBBC039 baseline experiment",
        "path": ".github/workflows/bbbc039_baseline.yml",
        "head_branch": "main",
        "head_sha": EXPECTED_SHA,
        "status": "completed",
        "conclusion": "success",
    }
    metadata.update(overrides)
    return metadata


def test_accepts_successful_baseline_from_exact_main_commit():
    assert validate_baseline_run(baseline_run(), EXPECTED_SHA) == {
        "run_id": "12345",
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
        ({"path": ".github/workflows/unrelated.yml"}, "does not use the BBBC039 baseline workflow file"),
        ({"id": 0}, "valid run ID"),
    ],
)
def test_rejects_untrusted_or_stale_baseline_run(overrides, message):
    with pytest.raises(ValueError, match=message):
        validate_baseline_run(baseline_run(**overrides), EXPECTED_SHA)


def test_rejects_the_observed_pr108_baseline_run():
    # Exact provenance of baseline run #42582135791, consumed by current-main
    # zero-shot run #42598700943 before the provenance guard was added.
    pr_baseline = baseline_run(
        id=42582135791,
        head_branch="fix/report-configured-retention-on-pinned-checkpoint-20261109",
        head_sha="73fe9ff4a38295c7372b3d06e052034ff0b0c231",
    )
    with pytest.raises(ValueError, match="must originate from main"):
        validate_baseline_run(pr_baseline, EXPECTED_SHA)


def test_rejects_the_observed_pr109_baseline_run():
    # Exact provenance of baseline run #42771485283, consumed by current-main
    # zero-shot run #42780911279 before the provenance guard was added.
    pr_baseline = baseline_run(
        id=42771485283,
        head_branch="fix/guard-s-biad634-baseline-provenance-20261109",
        head_sha="18980f4ae69ca3e502afc2619c4c345aa0f8694c",
    )
    with pytest.raises(ValueError, match="must originate from main"):
        validate_baseline_run(pr_baseline, EXPECTED_SHA)


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


def test_baseline_workflow_uses_fixed_release_training_recipe() -> None:
    root = Path(__file__).resolve().parents[1]
    trainer_path = root / "scripts" / "train_bbbc039.py"
    trainer_source = trainer_path.read_text(encoding="utf-8")
    tree = ast.parse(trainer_source)
    resolver = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "resolve_seed"
    )
    namespace: dict[str, object] = {}
    isolated = ast.Module(body=[resolver], type_ignores=[])
    exec(compile(isolated, str(trainer_path), "exec"), namespace)
    resolve_seed = namespace["resolve_seed"]
    assert resolve_seed(42, None) == 42
    assert resolve_seed(42, 7) == 7
    with pytest.raises(ValueError, match="non-negative"):
        resolve_seed(42, -1)

    assert 'parser.add_argument("--seed", type=int, default=None' in trainer_source
    assert 'seed = resolve_seed(int(cfg["seed"]), args.seed)' in trainer_source

    baseline_path = root / ".github" / "workflows" / "bbbc039_baseline.yml"
    baseline = yaml.load(baseline_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    train_step = next(
        step for step in baseline["jobs"]["train-evaluate"]["steps"]
        if step.get("name") == "Train boundary-aware U-Net baseline"
    )
    assert (baseline["on"]["workflow_dispatch"] or {}) == {}
    config = yaml.safe_load((root / "configs" / "bbbc039_baseline.yaml").read_text(encoding="utf-8"))
    assert config["training"]["epochs"] == 20
    assert config["seed"] == 42
    assert train_step["env"]["EPOCHS"] == str(config["training"]["epochs"])
    assert train_step["env"]["SEED"] == str(config["seed"])
    assert '--epochs "$EPOCHS"' in train_step["run"]
    assert '--seed "$SEED"' in train_step["run"]


def test_baseline_training_is_restricted_to_main() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow_path = root / ".github" / "workflows" / "bbbc039_baseline.yml"
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert workflow["jobs"]["train-evaluate"]["if"] == "${{ github.ref == 'refs/heads/main' }}"
