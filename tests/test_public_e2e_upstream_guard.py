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
