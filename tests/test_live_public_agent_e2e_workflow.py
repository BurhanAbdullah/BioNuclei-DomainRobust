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
