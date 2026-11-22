from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _workflow() -> dict:
    return yaml.safe_load((ROOT / ".github" / "workflows" / "e6_retry_watchdog.yml").read_text(encoding="utf-8"))


def _triggers(workflow: dict) -> dict:
    return workflow.get("on", workflow.get(True, {}))


def test_retry_watchdog_is_scoped_to_e6_runs_on_main() -> None:
    triggers = _triggers(_workflow())
    assert triggers["workflow_run"]["workflows"] == ["E6 external fluorescence few-shot adaptation"]
    assert triggers["workflow_run"]["types"] == ["completed"]
    assert triggers["workflow_run"]["branches"] == ["main"]


def test_retry_requires_failure_attempt_limit_and_exact_current_main_sha() -> None:
    job = _workflow()["jobs"]["retry-25pct"]
    condition = " ".join(job["if"].split())
    required = (
        "github.event.workflow_run.conclusion == 'failure'",
        "github.event.workflow_run.run_attempt < 5",
        "github.event.workflow_run.head_branch == 'main'",
        "github.event.workflow_run.head_sha == github.sha",
    )
    for clause in required:
        assert clause in condition, f"retry guard missing: {clause}"
