#!/usr/bin/env python3
"""Fail closed unless a BBBC039 baseline belongs to this exact main revision."""
from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any


_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def validate_baseline_run(
    metadata: Mapping[str, Any], expected_sha: str
) -> dict[str, str]:
    """Validate run identity before consuming its checkpoint artifact."""
    if not _SHA_RE.fullmatch(expected_sha):
        raise ValueError("expected SHA must be a full lowercase 40-character commit")
    if metadata.get("name") != "BBBC039 baseline experiment":
        raise ValueError("selected run is not the BBBC039 baseline workflow")
    if metadata.get("path") != ".github/workflows/bbbc039_baseline.yml":
        raise ValueError("selected run does not use the BBBC039 baseline workflow file")
    if metadata.get("head_branch") != "main":
        raise ValueError("baseline run must originate from main")
    if metadata.get("head_sha") != expected_sha:
        raise ValueError(
            "baseline run commit does not match the zero-shot evaluation commit"
        )
    if metadata.get("status") != "completed" or metadata.get("conclusion") != "success":
        raise ValueError("baseline run must have completed successfully")
    run_id = metadata.get("id")
    if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id <= 0:
        raise ValueError("baseline run metadata has no valid run ID")
    return {"run_id": str(run_id), "baseline_sha": expected_sha}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--github-output", type=Path, required=True)
    args = parser.parse_args()

    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    outputs = validate_baseline_run(metadata, args.expected_sha)
    with args.github_output.open("a", encoding="utf-8") as stream:
        for key, value in outputs.items():
            stream.write(f"{key}={value}\n")
    print(
        "Verified BBBC039 baseline provenance: "
        f"run_id={outputs['run_id']}, head_sha={outputs['baseline_sha']}, branch=main."
    )


if __name__ == "__main__":
    main()
