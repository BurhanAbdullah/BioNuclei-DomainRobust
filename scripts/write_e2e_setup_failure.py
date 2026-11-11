#!/usr/bin/env python3
"""Write a minimal, non-sensitive artifact when browser setup fails before E2E starts."""
from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping
from pathlib import Path


def build_setup_failure_payload(stage: str, environment: Mapping[str, str]) -> dict[str, object]:
    """Describe a setup failure without claiming that upload or inference ran."""
    normalized_stage = stage.strip()
    if not normalized_stage:
        raise ValueError("failure stage must be non-empty")
    return {
        "status": "FAIL",
        "failure_kind": "setup",
        "failure_stage": normalized_stage,
        "failure_step_outcome": "failure",
        "run_id": environment.get("GITHUB_RUN_ID"),
        "run_attempt": environment.get("GITHUB_RUN_ATTEMPT"),
        "commit": environment.get("GITHUB_SHA"),
        "ref": environment.get("GITHUB_REF"),
        "event": environment.get("GITHUB_EVENT_NAME"),
        "runner_os": environment.get("RUNNER_OS"),
        "public_upload_attempted": False,
        "inference_started": False,
        "cleanup_attempted": False,
        "reason": "Browser dependency installation failed before the public E2E harness executed.",
    }


def write_setup_failure_artifact(
    output: Path,
    stage: str,
    environment: Mapping[str, str],
) -> bool:
    """Create fallback evidence only when the harness has not already written it."""
    if output.exists():
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_setup_failure_payload(stage, environment)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + chr(10), encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", required=True)
    args = parser.parse_args()
    created = write_setup_failure_artifact(args.output, args.stage, os.environ)
    print("Wrote setup failure evidence." if created else "Preserved existing E2E failure evidence.")


if __name__ == "__main__":
    main()
