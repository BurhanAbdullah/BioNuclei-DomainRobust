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
