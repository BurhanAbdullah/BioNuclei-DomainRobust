"""Catch YAML syntax regressions across GitHub Actions workflows."""
from pathlib import Path

import yaml


def test_every_github_actions_workflow_parses_as_yaml() -> None:
    workflow_dir = Path(".github/workflows")
    workflow_files = sorted(
        path
        for path in workflow_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".yml", ".yaml"}
    )
    assert workflow_files, "No GitHub Actions workflow YAML files found"

    for path in workflow_files:
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise AssertionError(f"Invalid workflow YAML in {path}: {exc}") from exc

        assert isinstance(document, dict), f"{path} must contain a YAML mapping"
        assert isinstance(document.get("name"), str) and document["name"].strip(), (
            f"{path} must declare a workflow name"
        )
        assert isinstance(document.get("jobs"), dict) and document["jobs"], (
            f"{path} must declare at least one job"
        )


def test_main_ci_uses_and_verifies_cpu_only_pytorch() -> None:
    workflow = yaml.safe_load(
        Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    )
    steps = workflow["jobs"]["tests"]["steps"]

    install = next(
        step
        for step in steps
        if step.get("name") == "Install package and web test dependencies"
    )
    assert "--constraint deploy/render-cpu-constraints.txt" in install["run"]

    verify = next(
        step for step in steps if step.get("name") == "Verify CPU-only PyTorch"
    )
    assert "torch.version.cuda" in verify["run"]
    assert "is not None" in verify["run"]

    constraints = Path("deploy/render-cpu-constraints.txt").read_text(
        encoding="utf-8"
    ).splitlines()
    assert any(line.startswith("torch==") and line.endswith("+cpu") for line in constraints)
    assert any(
        line.startswith("torchvision==") and line.endswith("+cpu")
        for line in constraints
    )
