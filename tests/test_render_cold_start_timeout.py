from __future__ import annotations

from pathlib import Path

import yaml


def test_render_root_probe_allows_bounded_cold_start_without_weakening_health_timeout() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load(
        (root / ".github/workflows/community_analyzer_validation.yml").read_text(
            encoding="utf-8"
        )
    )
    steps = workflow["jobs"]["live"]["steps"]
    root_probe = next(step for step in steps if step.get("name") == "Check service root")
    health_probe = next(step for step in steps if step.get("name") == "Check service health")

    assert "--connect-timeout 10" in root_probe["run"]
    assert "--max-time 90" in root_probe["run"]
    assert "--retry 1" in root_probe["run"]
    assert "--max-time 20" in health_probe["run"]
