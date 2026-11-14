from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "e5_ablations.yml"


def test_e5_downloads_target_dataset_once_and_reuses_verified_artifact() -> None:
    workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    triggers = workflow["on"]

    push = triggers["push"]
    assert push["branches"] == ["main"]
    assert ".github/workflows/e5_ablations.yml" in push["paths"]
    assert "scripts/extract_s_biad634_archive.py" in push["paths"]
    assert "workflow_dispatch" in triggers

    jobs = workflow["jobs"]
    prepare = jobs["prepare_target_dataset"]
    download_commands = [
        step["run"]
        for step in prepare["steps"]
        if "run" in step and "scripts/download_s_biad634.py" in step["run"]
    ]
    assert download_commands == [
        "python scripts/download_s_biad634.py --data-root data/raw/S-BIAD634 --keep-archive"
    ]

    publish = next(
        step for step in prepare["steps"]
        if step.get("name") == "Publish shared target dataset artifact"
    )
    assert publish["with"]["name"] == "e5-target-dataset-${{ github.run_id }}"
    assert publish["with"]["retention-days"] == "1"
    assert publish["with"]["compression-level"] == "0"

    variant = jobs["e5_variant"]
    assert variant["needs"] == "prepare_target_dataset"
    gate = jobs["e5_gate"]
    assert set(gate["needs"]) == {"e5_variant", "prepare_target_dataset"}

    for job in (variant, gate):
        download = next(
            step for step in job["steps"]
            if step.get("name") == "Download shared target dataset artifact"
        )
        assert download["uses"] == "actions/download-artifact@v4"
        assert download["with"]["name"] == "e5-target-dataset-${{ github.run_id }}"
        extract = next(
            step for step in job["steps"]
            if step.get("name") == "Verify and extract shared target dataset"
        )
        assert "scripts/extract_s_biad634_archive.py" in extract["run"]

    all_downloads = [
        step["run"]
        for job in jobs.values()
        for step in job.get("steps", [])
        if "run" in step and "scripts/download_s_biad634.py" in step["run"]
    ]
    assert len(all_downloads) == 1, "only the preparation job may contact BioStudies"
