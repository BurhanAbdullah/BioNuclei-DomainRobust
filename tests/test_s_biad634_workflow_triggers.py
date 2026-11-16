from pathlib import Path

import yaml


def test_zero_shot_transfer_tracks_all_inference_dependencies() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.load(
        (root / ".github" / "workflows" / "s_biad634_zero_shot.yml").read_text(
            encoding="utf-8"
        ),
        Loader=yaml.BaseLoader,
    )

    required_paths = {
        "scripts/evaluate_s_biad634.py",
        "scripts/metrics_instance.py",
        "scripts/download_s_biad634.py",
        "src/bionuclei/data.py",
        "src/bionuclei/masks.py",
        "src/bionuclei/models.py",
        "src/bionuclei/metrics.py",
        "src/bionuclei/postprocessing.py",
        "pyproject.toml",
    }
    push = workflow["on"]["push"]
    pull_request = workflow["on"]["pull_request"]

    assert push["branches"] == ["main"]
    assert required_paths <= set(push["paths"])
    assert required_paths <= set(pull_request["paths"])
    assert "github.event_name == 'pull_request'" in workflow["jobs"]["zero-shot"]["if"]
    assert workflow["permissions"]["actions"] == "read"
    assert workflow["permissions"]["contents"] == "read"
