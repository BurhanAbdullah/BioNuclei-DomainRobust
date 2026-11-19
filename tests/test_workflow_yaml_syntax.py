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


def test_live_render_endpoint_requires_explicit_main_dispatch_opt_in() -> None:
    workflow = yaml.safe_load(
        Path(".github/workflows/community_analyzer_validation.yml").read_text(encoding="utf-8")
    )
    triggers = workflow.get("on", workflow.get(True))
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert inputs["allow_live_render"]["default"] is False
    condition = workflow["jobs"]["live"]["if"]
    assert "github.repository == 'BurhanAbdullah/BioNuclei-DomainRobust'" in condition
    assert "github.event_name == 'workflow_dispatch'" in condition
    assert "github.ref == 'refs/heads/main'" in condition
    assert "inputs.allow_live_render == true" in condition
    assert "ephemeral guest-session creation" in inputs["allow_live_render"]["description"]
