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
