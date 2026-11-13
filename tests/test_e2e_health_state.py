import ast
from pathlib import Path

import pytest
import yaml

from scripts.e2e_health_state import clear_recovered_health_errors


def test_successful_health_retry_clears_stale_error_fields() -> None:
    state: dict[str, object] = {
        "api_health_http_status": 200,
        "api_health_request_error": "ReadTimeout",
        "api_health_body": "stale upstream error body",
        "api_health_attempts": [
            {"attempt": 1, "error": "ReadTimeout"},
            {"attempt": 2, "http_status": 200, "result": "http_200"},
        ],
    }

    clear_recovered_health_errors(state)

    assert "api_health_request_error" not in state
    assert "api_health_body" not in state
    assert state["api_health_http_status"] == 200
    attempts = state["api_health_attempts"]
    assert isinstance(attempts, list)
    assert attempts[-1]["result"] == "http_200"


def test_public_upload_is_main_only_and_pr_uses_offline_harness() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load(
        (root / ".github/workflows/live-public-agent-e2e.yml").read_text(encoding="utf-8")
    )
    jobs = workflow["jobs"]

    assert jobs["public-upload-to-agent"]["if"] == "github.ref == 'refs/heads/main'"
    assert jobs["validate-harness"]["if"] == "github.event_name == 'pull_request'"
    assert "scripts/live_public_agent_e2e.py" in jobs["validate-harness"]["steps"][-1]["run"]



def test_e2e_health_readiness_budget_is_bounded_and_cold_start_aware() -> None:
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts/live_public_agent_e2e.py"
    script = script_path.read_text(encoding="utf-8")

    assert "HEALTH_READINESS_BUDGET_SECONDS = 179.0" in script
    assert "deadline = time.monotonic() + HEALTH_READINESS_BUDGET_SECONDS" in script
    assert "timeout=_health_request_timeout(remaining)" in script
    assert "_health_response_within_budget(response_completed_at, deadline)" in script
    assert "clear_recovered_health_errors(state)" in script

    tree = ast.parse(script)
    timeout_helper = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_health_request_timeout"
    )
    deadline_helper = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_health_response_within_budget"
    )
    namespace = {
        "HEALTH_CONNECT_TIMEOUT_SECONDS": 10.0,
        "HEALTH_READ_TIMEOUT_CAP_SECONDS": 150.0,
    }
    isolated = ast.Module(body=[timeout_helper, deadline_helper], type_ignores=[])
    exec(compile(isolated, str(script_path), "exec"), namespace)
    timeout_for = namespace["_health_request_timeout"]
    within_budget = namespace["_health_response_within_budget"]

    assert timeout_for(179.0) == (10.0, 150.0)
    assert timeout_for(134.0) == (10.0, 124.0)
    assert timeout_for(30.0) == (10.0, 20.0)
    assert sum(timeout_for(5.0)) <= 5.0
    assert within_budget(178.999, 179.0) is True
    assert within_budget(179.0, 179.0) is True
    assert within_budget(179.001, 179.0) is False
    with pytest.raises(ValueError, match="budget is exhausted"):
        timeout_for(0.0)
