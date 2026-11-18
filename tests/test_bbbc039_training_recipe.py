from pathlib import Path

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
