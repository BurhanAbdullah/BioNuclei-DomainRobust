from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_bbbc039_workflow_default_epochs_match_committed_recipe() -> None:
    workflow = yaml.load(
        (ROOT / ".github/workflows/bbbc039_baseline.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    config = yaml.safe_load(
        (ROOT / "configs/bbbc039_baseline.yaml").read_text(encoding="utf-8")
    )
    expected_epochs = str(config["training"]["epochs"])

    inputs = workflow["on"]["workflow_dispatch"]["inputs"]
    assert inputs["epochs"]["default"] == expected_epochs

    training = next(
        step for step in workflow["jobs"]["train-evaluate"]["steps"]
        if step.get("name") == "Train boundary-aware U-Net baseline"
    )
    assert training["env"]["EPOCHS"] == "${{ inputs.epochs || '100' }}"


def test_checkpoint_recipe_guard_rejects_20_epoch_main_baseline() -> None:
    from scripts.verify_bbbc039_checkpoint import validate_checkpoint_metadata

    config = yaml.safe_load(
        (ROOT / "configs/bbbc039_baseline.yaml").read_text(encoding="utf-8")
    )
    observed = {"config": config, "seed": config["seed"], "epochs_run": 20}
    with pytest.raises(ValueError, match="epochs_run does not match"):
        validate_checkpoint_metadata(observed, config)

    canonical = {**observed, "epochs_run": config["training"]["epochs"]}
    assert validate_checkpoint_metadata(canonical, config) == {
        "seed": config["seed"],
        "epochs_run": 100,
    }


def test_checkpoint_verifier_runs_before_zero_shot_evaluation() -> None:
    baseline = yaml.load(
        (ROOT / ".github/workflows/bbbc039_baseline.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    assert "scripts/verify_bbbc039_checkpoint.py" in baseline["on"]["push"]["paths"]

    workflow = yaml.load(
        (ROOT / ".github/workflows/s_biad634_zero_shot.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    steps = workflow["jobs"]["zero-shot"]["steps"]
    locate = next(step for step in steps if step.get("name") == "Locate checkpoint")
    verify = next(step for step in steps if step.get("name") == "Verify baseline checkpoint training recipe")
    provenance = next(step for step in steps if step.get("name") == "Record evaluation provenance")
    evaluate = next(step for step in steps if step.get("name") == "Run zero-shot transfer evaluation")
    assert steps.index(locate) < steps.index(verify) < steps.index(provenance) < steps.index(evaluate)
    assert "--checkpoint baseline_artifact/last.pt" in verify["run"]
    assert "--config configs/bbbc039_baseline.yaml" in verify["run"]


def test_checkpoint_verifier_uses_safe_weights_only_loading() -> None:
    script = (ROOT / "scripts/verify_bbbc039_checkpoint.py").read_text(encoding="utf-8")
    assert "weights_only=True" in script
