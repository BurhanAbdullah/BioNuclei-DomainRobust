from pathlib import Path

import yaml


def test_live_render_validation_requires_explicit_upstream_opt_in() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.load(
        (root / ".github/workflows/community_analyzer_validation.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )

    inputs = workflow["on"]["workflow_dispatch"]["inputs"]
    assert inputs["allow_live_render"]["default"] == "false"
    assert workflow["jobs"]["live"]["if"] == (
        "${{ github.event_name == 'workflow_dispatch' "
        "&& github.repository == 'BurhanAbdullah/BioNuclei-DomainRobust' "
        "&& github.ref == 'refs/heads/main' && inputs.allow_live_render == true }}"
    )
