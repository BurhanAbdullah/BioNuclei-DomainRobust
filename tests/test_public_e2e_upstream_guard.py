from pathlib import Path

import yaml


def test_public_upload_job_is_restricted_to_upstream_main() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.load(
        (root / ".github/workflows/live-public-agent-e2e.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )

    job = workflow["jobs"]["public-upload-to-agent"]
    assert job["if"] == (
        "${{ github.repository == 'BurhanAbdullah/BioNuclei-DomainRobust' "
        "&& github.ref == 'refs/heads/main' }}"
    )


def test_live_render_validation_is_explicit_opt_in() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.load(
        (root / ".github/workflows/community_analyzer_validation.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )

    allow_live_render = workflow["on"]["workflow_dispatch"]["inputs"]["allow_live_render"]
    assert allow_live_render["default"] == "false"
    assert workflow["jobs"]["live"]["if"] == (
        "${{ github.event_name == 'workflow_dispatch' "
        "&& github.repository == 'BurhanAbdullah/BioNuclei-DomainRobust' "
        "&& github.ref == 'refs/heads/main' && inputs.allow_live_render == true }}"
    )
