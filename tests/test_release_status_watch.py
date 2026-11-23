from pathlib import Path

import yaml


def test_release_status_watch_blocks_stale_clean_reproduction() -> None:
    workflow_path = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "release_status_watch.yml"
    )
    workflow = yaml.load(
        workflow_path.read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    step = next(
        item
        for item in workflow["jobs"]["status"]["steps"]
        if item.get("name") == "Resolve latest successful clean reproduction"
    )
    script = step["run"]

    assert ".head_sha // empty" in script
    assert 'repos/${GITHUB_REPOSITORY}/commits/main' in script
    assert '[ "$run_sha" != "$current_main_sha" ]' in script
    assert "Latest clean reproduction is stale for current main" in script
    assert '"clean_reproduction_sha":os.environ["CLEAN_REPRODUCTION_SHA"]' in script

    status_step = next(
        item
        for item in workflow["jobs"]["status"]["steps"]
        if item.get("name") == "Check current artifact identity and report release blockers"
    )
    status_script = status_step["run"]
    assert "scientific_source_run_ids" in status_script
    assert "source_run.get('head_branch') != 'main'" in status_script
    assert "source_run.get('conclusion') != 'success'" in status_script
    assert "source_sha != current_main_sha" in status_script
    assert "scientific_source_run_shas" in status_script
    assert "Clean reproduction became stale for current main" in status_script
