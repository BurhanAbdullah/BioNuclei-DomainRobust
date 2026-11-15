#!/usr/bin/env python3
"""Fail closed unless a zero-shot run uses a reproducible main-branch BBBC039 baseline."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

_SHA_RE = re.compile(r"[0-9a-f]{40}")
_ARTIFACT_DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")
_BASELINE_WORKFLOW = ".github/workflows/bbbc039_baseline.yml"
_SAFE_PREFIXES = ("tests/", "docs/", "webapp/")
_SAFE_PATHS = frozenset(
    {
        "CHANGELOG.md",
        "LICENSE",
        "README.md",
        "render.yaml",
        ".github/workflows/e6_e7_uncertainty_analysis.yml",
        ".github/workflows/e6_external_few_shot.yml",
        ".github/workflows/e6_retry_watchdog.yml",
        ".github/workflows/live-public-agent-e2e.yml",
        ".github/workflows/public-e2e-schedule-watchdog.yml",
        ".github/workflows/s_biad634_zero_shot.yml",
        "scripts/aggregate_e6_fraction_evidence.py",
        "scripts/download_aitslab_bioimaging1.py",
        "scripts/download_s_biad634.py",
        "scripts/evaluate_s_biad634.py",
        "scripts/live_public_agent_e2e.py",
        "scripts/metrics_instance.py",
        "scripts/public_e2e_schedule_watchdog.py",
        "scripts/validate_bbbc039_baseline.py",
    }
)


def is_baseline_input_change(path: str) -> bool:
    """Unknown paths fail closed; only explicitly known downstream paths are exempt."""
    if not isinstance(path, str) or not path:
        return True
    if path == _BASELINE_WORKFLOW:
        return True
    if path in _SAFE_PATHS or path.startswith(_SAFE_PREFIXES):
        return False
    return True


def validate_baseline_provenance(
    run: dict[str, Any],
    artifacts_payload: dict[str, Any],
    comparison: dict[str, Any],
    *,
    expected_sha: str,
    repository: str,
) -> dict[str, Any]:
    """Validate run identity, exact compare endpoints, ancestry, inputs, and artifact identity."""
    if not _SHA_RE.fullmatch(expected_sha):
        raise ValueError("evaluation commit must be a lowercase 40-character SHA")

    if run.get("name") != "BBBC039 baseline experiment":
        raise ValueError("selected run is not the BBBC039 baseline workflow")
    workflow_path = str(run.get("path") or "").split("@", 1)[0]
    if workflow_path != _BASELINE_WORKFLOW:
        raise ValueError(f"unexpected baseline workflow path: {workflow_path!r}")
    if run.get("head_branch") != "main":
        raise ValueError(
            f"baseline run must come from main, not {run.get('head_branch')!r}"
        )
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        raise ValueError("baseline run must be completed successfully")

    if run.get("event") not in {"push", "workflow_dispatch"}:
        raise ValueError(
            f"baseline event must be push or workflow_dispatch, got {run.get('event')!r}"
        )

    run_repository = (run.get("repository") or {}).get("full_name")
    if run_repository != repository:
        raise ValueError(
            f"baseline repository mismatch: expected {repository!r}, got {run_repository!r}"
        )
    head_repository = run.get("head_repository")
    if not isinstance(head_repository, dict) or head_repository.get("full_name") != repository:
        actual_head_repository = (
            head_repository.get("full_name") if isinstance(head_repository, dict) else None
        )
        raise ValueError(
            f"baseline head repository mismatch: expected {repository!r}, got {actual_head_repository!r}"
        )

    baseline_sha = str(run.get("head_sha") or "")
    if not _SHA_RE.fullmatch(baseline_sha):
        raise ValueError("baseline run has no valid head SHA")

    compare_status = comparison.get("status")
    if compare_status not in {"ahead", "identical"}:
        raise ValueError(
            f"baseline commit is not an ancestor of evaluation commit: {compare_status!r}"
        )
    base_commit_sha = (comparison.get("base_commit") or {}).get("sha")
    if base_commit_sha != baseline_sha:
        raise ValueError(
            f"GitHub comparison base mismatch: baseline={baseline_sha}, base={base_commit_sha!r}"
        )
    merge_base_sha = (comparison.get("merge_base_commit") or {}).get("sha")
    if merge_base_sha != baseline_sha:
        raise ValueError(
            f"baseline commit is not the merge base: baseline={baseline_sha}, merge_base={merge_base_sha!r}"
        )

    commits = comparison.get("commits")
    total_commits = comparison.get("total_commits")
    if (
        not isinstance(commits, list)
        or not isinstance(total_commits, int)
        or total_commits != len(commits)
        or total_commits >= 250
    ):
        raise ValueError("GitHub comparison omitted or may have truncated commit details")
    if compare_status == "identical":
        if baseline_sha != expected_sha or commits:
            raise ValueError("identical comparison does not match the requested evaluation commit")
    elif not commits or not isinstance(commits[-1], dict) or commits[-1].get("sha") != expected_sha:
        raise ValueError("GitHub comparison head does not match the evaluation commit")

    changed_files = comparison.get("files")
    if not isinstance(changed_files, list) or len(changed_files) >= 300:
        raise ValueError("GitHub comparison omitted or may have truncated changed-file details")
    changed_paths: list[str] = []
    for entry in changed_files:
        path = entry.get("filename") if isinstance(entry, dict) else None
        if not isinstance(path, str) or not path:
            raise ValueError("GitHub comparison returned a malformed changed-file entry")
        changed_paths.append(path)
    changed_baseline_inputs = sorted(
        path for path in changed_paths if is_baseline_input_change(path)
    )
    if changed_baseline_inputs:
        raise ValueError(
            "BBBC039 training/evaluation inputs changed after the selected baseline: "
            f"{changed_baseline_inputs}"
        )

    artifact_list = artifacts_payload.get("artifacts")
    if not isinstance(artifact_list, list):
        raise ValueError("baseline run artifact response is malformed")
    expected_artifact_name = f"bbbc039-baseline-{run.get('id')}"
    matching_artifacts = [
        item for item in artifact_list
        if isinstance(item, dict) and item.get("name") == expected_artifact_name
    ]
    if len(matching_artifacts) != 1:
        raise ValueError(
            f"expected exactly one {expected_artifact_name!r} artifact; "
            f"found {len(matching_artifacts)}"
        )
    artifact = matching_artifacts[0]
    if artifact.get("expired") is not False:
        raise ValueError("baseline artifact is expired or its expiry state is unknown")
    if not isinstance(artifact.get("size_in_bytes"), int) or artifact["size_in_bytes"] <= 0:
        raise ValueError("baseline artifact is empty or has an invalid size")
    digest = artifact.get("digest")
    if not isinstance(digest, str) or not _ARTIFACT_DIGEST_RE.fullmatch(digest):
        raise ValueError("baseline artifact is missing a valid SHA-256 digest")
    artifact_id = artifact.get("id")
    if not isinstance(artifact_id, int) or artifact_id <= 0:
        raise ValueError("baseline artifact has no valid artifact ID")

    return {
        "baseline_run_id": int(run["id"]),
        "baseline_run_url": run.get("html_url"),
        "baseline_created_at": run.get("created_at"),
        "baseline_event": run.get("event"),
        "baseline_head_branch": "main",
        "baseline_head_sha": baseline_sha,
        "baseline_workflow_path": _BASELINE_WORKFLOW,
        "baseline_artifact_id": artifact_id,
        "baseline_artifact_name": expected_artifact_name,
        "baseline_artifact_digest": digest,
        "baseline_artifact_size_bytes": artifact["size_in_bytes"],
        "baseline_compare_status": compare_status,
        "baseline_merge_base_sha": merge_base_sha,
        "baseline_changed_paths": sorted(changed_paths),
        "baseline_training_inputs_unchanged": True,
        "evaluation_commit": expected_sha,
        "repository": repository,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-json", type=Path, required=True)
    parser.add_argument("--artifacts-json", type=Path, required=True)
    parser.add_argument("--compare-json", type=Path, required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    run = json.loads(args.run_json.read_text(encoding="utf-8"))
    artifacts = json.loads(args.artifacts_json.read_text(encoding="utf-8"))
    comparison = json.loads(args.compare_json.read_text(encoding="utf-8"))
    provenance = validate_baseline_provenance(
        run,
        artifacts,
        comparison,
        expected_sha=args.expected_sha,
        repository=args.repository,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "baseline_run_id": provenance["baseline_run_id"],
                "baseline_head_sha": provenance["baseline_head_sha"],
                "baseline_artifact_id": provenance["baseline_artifact_id"],
                "baseline_artifact_digest": provenance["baseline_artifact_digest"],
                "baseline_training_inputs_unchanged": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
