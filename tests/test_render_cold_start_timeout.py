from __future__ import annotations

import ast
from pathlib import Path

import pytest

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


def test_live_public_e2e_upload_job_is_main_only() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load(
        (root / ".github/workflows/live-public-agent-e2e.yml").read_text(
            encoding="utf-8"
        )
    )
    assert workflow["jobs"]["public-upload-to-agent"]["if"] == "github.ref == 'refs/heads/main'"

def test_live_public_e2e_requires_verified_pinned_checkpoint_health() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts/live_public_agent_e2e.py").read_text(encoding="utf-8")
    assert "checkpoint_verified" in script
    assert "checkpoint_sha256" in script
    assert "health.get(\"checkpoint_verified\") is True" in script
    assert "health.get(\"checkpoint_sha256\") == EXPECTED_CHECKPOINT_SHA256" in script
    assert "7209a6990514380804210292ac208b0f3b0b0a054338a145e1916044762d7c92" in script



def test_e2e_health_probe_waits_for_cold_start_within_one_total_budget() -> None:
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts/live_public_agent_e2e.py"
    script = script_path.read_text(encoding="utf-8")

    assert "HEALTH_READINESS_BUDGET_SECONDS = 119.0" in script
    assert "deadline = time.monotonic() + HEALTH_READINESS_BUDGET_SECONDS" in script
    assert "timeout=_health_request_timeout(remaining)" in script
    assert 'state.pop("api_health_request_error", None)' in script

    tree = ast.parse(script)
    helper = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_health_request_timeout"
    )
    namespace = {
        "HEALTH_CONNECT_TIMEOUT_SECONDS": 10.0,
        "HEALTH_READ_TIMEOUT_CAP_SECONDS": 90.0,
    }
    isolated = ast.Module(body=[helper], type_ignores=[])
    exec(compile(isolated, str(script_path), "exec"), namespace)
    timeout_for = namespace["_health_request_timeout"]

    assert timeout_for(119.0) == (10.0, 90.0)
    assert timeout_for(30.0) == (10.0, 20.0)
    assert sum(timeout_for(5.0)) <= 5.0
    with pytest.raises(ValueError, match="budget is exhausted"):
        timeout_for(0.0)
