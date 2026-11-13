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


def test_browser_dependency_failure_is_recorded_before_public_harness() -> None:
    workflow_path = Path(".github/workflows/live-public-agent-e2e.yml")
    workflow = yaml.load(
        workflow_path.read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    job = workflow["jobs"]["public-upload-to-agent"]
    assert job.get("if") == (
        "${{ github.repository == 'BurhanAbdullah/BioNuclei-DomainRobust' "
        "&& github.ref == 'refs/heads/main' }}"
    )
    steps = job["steps"]
    install_index = next(
        index for index, step in enumerate(steps)
        if step.get("name") == "Install browser E2E dependencies"
    )
    install = steps[install_index]
    record = steps[install_index + 1]
    upload = next(step for step in steps if step.get("name") == "Upload browser failure evidence")

    assert install.get("id") == "install_browser_e2e_deps"
    assert "set -euo pipefail" in install.get("run", "")
    assert "tee browser-setup.log" in install.get("run", "")
    assert "tee -a browser-setup.log" in install.get("run", "")
    assert record.get("if") == (
        "failure() && steps.install_browser_e2e_deps.outcome == 'failure'"
    )
    assert "browser_dependency_install" in record.get("run", "")
    assert "public_upload_attempted" in record.get("run", "")
    assert "public_inference_attempted" in record.get("run", "")
    assert upload.get("if") == "failure()"
    upload_paths = upload.get("with", {}).get("path", "")
    assert "live-agent-e2e-failure.json" in upload_paths
    assert "browser-setup.log" in upload_paths
