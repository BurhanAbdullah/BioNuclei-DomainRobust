from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _workflow(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def _triggers(payload: dict) -> dict:
    return payload.get("on", payload.get(True, {}))


def test_e6_waits_for_successful_main_e4_run() -> None:
    workflow = _workflow(".github/workflows/e6_external_few_shot.yml")
    triggers = _triggers(workflow)
    assert triggers["workflow_run"]["workflows"] == ["E4 domain-robust method"]
    assert triggers["workflow_run"]["types"] == ["completed"]
    assert triggers["workflow_run"]["branches"] == ["main"]
    assert "push" not in triggers
    assert triggers["workflow_dispatch"]["inputs"]["e4_run_id"]["required"] is True


def test_e6_resolves_artifact_from_exact_source_run_and_checks_archive_digest() -> None:
    workflow = _workflow(".github/workflows/e6_external_few_shot.yml")
    job = workflow["jobs"]["e6_fraction"]
    assert "github.event.workflow_run.id || inputs.e4_run_id" in job["env"]["E4_SOURCE_RUN_ID"]
    checkout = next(step for step in job["steps"] if step.get("name") == "Checkout exact E4 source revision")
    assert checkout["with"]["ref"] == "${{ github.event.workflow_run.head_sha || github.sha }}"
    verify = next(step for step in job["steps"] if step.get("name") == "Resolve and verify exact E4 artifact")
    script = verify["run"]
    assert 'e4-domain-robust-${E4_SOURCE_RUN_ID}' in script
    for required in ("head_sha", "head_branch", "workflow_id", "conclusion"):
        assert required in script
    assert "EXPECTED_E4_DIGEST" in script
    download = next(step for step in job["steps"] if step.get("name") == "Download frozen E4 checkpoint")
    assert "sha256sum e4.zip" in download["run"]
    assert "weights_only=True" in download["run"]


def test_e6_has_no_stale_hard_coded_artifact_identity() -> None:
    for path in (
        ".github/workflows/e6_external_few_shot.yml",
        ".github/workflows/e6_25pct_recovery.yml",
    ):
        text = (ROOT / path).read_text(encoding="utf-8")
        assert "12183110279" not in text
        assert "89e66617e272d30ec46471c8403950c404c772780ad778dd6f0e992fc795df0d" not in text


def test_e6_recovery_requires_an_explicit_verified_e4_run() -> None:
    workflow = _workflow(".github/workflows/e6_25pct_recovery.yml")
    triggers = _triggers(workflow)
    assert triggers["workflow_dispatch"]["inputs"]["e4_run_id"]["required"] is True
    job = workflow["jobs"]["e6_25pct"]
    assert job["env"]["E4_SOURCE_RUN_ID"] == "${{ inputs.e4_run_id }}"
    verify = next(step for step in job["steps"] if step.get("name") == "Resolve and verify exact E4 artifact")
    assert 'e4-domain-robust-${E4_SOURCE_RUN_ID}' in verify["run"]
    assert "EXPECTED_E4_DIGEST" in verify["run"]
