from pathlib import Path

import yaml


def test_public_upload_job_is_skipped_for_pull_requests() -> None:
    workflow_path = Path(__file__).resolve().parents[1] / ".github/workflows/live-public-agent-e2e.yml"
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

    assert workflow["jobs"]["public-upload-to-agent"]["if"] == "github.event_name != 'pull_request'"
    assert workflow["jobs"]["validate-pr"]["if"] == "github.event_name == 'pull_request'"
    assert ".github/workflows/live-public-agent-e2e.yml" in workflow["on"]["pull_request"]["paths"]
