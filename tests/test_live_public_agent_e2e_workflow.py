from pathlib import Path

import yaml


def test_public_upload_job_is_restricted_to_main_ref() -> None:
    workflow_path = Path(__file__).resolve().parents[1] / ".github/workflows/live-public-agent-e2e.yml"
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

    assert workflow["jobs"]["public-upload-to-agent"]["if"] == "github.ref == 'refs/heads/main'"
    assert workflow["jobs"]["validate-pr"]["if"] == "github.event_name == 'pull_request'"
    assert workflow["on"]["push"]["branches"] == ["main"]
    assert "schedule" in workflow["on"]
    assert "workflow_dispatch" in workflow["on"]
    assert ".github/workflows/live-public-agent-e2e.yml" in workflow["on"]["pull_request"]["paths"]


def test_runtime_preflight_precedes_browser_dependency_install() -> None:
    workflow_path = Path(__file__).resolve().parents[1] / ".github/workflows/live-public-agent-e2e.yml"
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    steps = workflow["jobs"]["public-upload-to-agent"]["steps"]
    names = [step["name"] for step in steps]

    preflight_index = names.index("Verify deployed runtime before browser dependency installation")
    install_index = names.index("Install browser E2E dependencies")
    assert preflight_index < install_index
    preflight = steps[preflight_index]
    assert preflight["run"] == "python scripts/check_public_e2e_runtime.py"
    assert preflight["env"]["GITHUB_SHA"] == "${{ github.sha }}"

def test_runtime_build_inputs_trigger_public_e2e_on_main_push() -> None:
    workflow_path = Path(__file__).resolve().parents[1] / ".github/workflows/live-public-agent-e2e.yml"
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    push_paths = set(workflow["on"]["push"]["paths"])

    # These are copied into the Render images or configure their build/runtime.
    # A change must trigger the public gate immediately rather than wait for cron.
    assert {
        "webapp/**",
        "src/**",
        "pyproject.toml",
        "README.md",
        "configs/**",
        "render.yaml",
        "docs/RESEARCH_PROTOCOL.md",
        "docs/DATASETS.md",
    }.issubset(push_paths)
