#!/usr/bin/env python3
"""Fail fast before browser installation when Render is not serving current main."""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

DEFAULT_REPOSITORY = "BurhanAbdullah/BioNuclei-DomainRobust"
DEFAULT_API_BASE = "https://bionuclei-community-analyzer.onrender.com"
SHA_RE = re.compile(r"[0-9a-f]{40}")


def revision_mismatch_reason(tested_sha: str | None, main_sha: str | None) -> str | None:
    """Require this workflow run and the live default branch to identify one revision."""
    if not isinstance(tested_sha, str) or not SHA_RE.fullmatch(tested_sha):
        return "GITHUB_SHA is missing or is not a full lowercase commit SHA"
    if not isinstance(main_sha, str) or not SHA_RE.fullmatch(main_sha):
        return "GitHub did not return a valid current-main commit SHA"
    if tested_sha != main_sha:
        return f"workflow revision is stale: tested_sha={tested_sha}, current_main_sha={main_sha}"
    return None


def runtime_mismatch_reason(
    tested_sha: str | None,
    main_sha: str | None,
    health: dict[str, object] | None,
) -> str | None:
    """Fail closed unless health and deployed source identify the exact current main."""
    revision_reason = revision_mismatch_reason(tested_sha, main_sha)
    if revision_reason:
        return revision_reason
    if not isinstance(health, dict):
        return "Render health did not return a JSON object"
    if health.get("status") != "ok":
        return f"Render health status is not ok: {health.get('status')!r}"
    if health.get("checkpoint_available") is not True:
        return "Render health does not confirm checkpoint availability"
    if health.get("render_git_branch") != "main":
        return f"Render is not serving branch main: {health.get('render_git_branch')!r}"
    deployed_sha = health.get("render_git_commit")
    if not isinstance(deployed_sha, str) or not SHA_RE.fullmatch(deployed_sha):
        return "Render health did not expose a valid deployed Git commit"
    if deployed_sha != main_sha:
        return f"Render runtime SHA mismatch: deployed_sha={deployed_sha}, current_main_sha={main_sha}"
    return None


def _request_json(url: str, timeout_seconds: int) -> dict[str, object]:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "bionuclei-public-e2e-runtime-preflight",
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        raw = response.read(65536)
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON response was not an object")
    return payload


def _write_failure(
    *,
    reason: str,
    tested_sha: str | None,
    main_sha: str | None,
    health: dict[str, object] | None,
    attempts: list[dict[str, object]],
) -> None:
    payload: dict[str, object] = {
        "status": "FAIL",
        "phase": "runtime_preflight",
        "reason": reason,
        "expected_tested_commit": tested_sha,
        "expected_main_commit": main_sha,
        "render_git_branch": health.get("render_git_branch") if health else None,
        "render_git_commit": health.get("render_git_commit") if health else None,
        "checkpoint_available": health.get("checkpoint_available") if health else None,
        "api_health_attempts": attempts,
        "public_upload_attempted": False,
        "guest_token_seen": False,
        "job_id_seen": False,
        "cleanup_attempted": False,
        "cleanup_verified": False,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    Path("live-agent-e2e-failure.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    repository = os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPOSITORY)
    tested_sha = os.environ.get("GITHUB_SHA")
    api_base = os.environ.get("BIONUCLEI_PUBLIC_API_URL", DEFAULT_API_BASE).rstrip("/")
    main_sha: str | None = None
    health: dict[str, object] | None = None
    attempts: list[dict[str, object]] = []

    try:
        main_payload = _request_json(
            f"https://api.github.com/repos/{repository}/commits/main",
            timeout_seconds=10,
        )
        value = main_payload.get("sha")
        main_sha = value if isinstance(value, str) else None
    except Exception as exc:
        reason = f"Could not resolve current main from GitHub: {type(exc).__name__}"
        _write_failure(
            reason=reason,
            tested_sha=tested_sha,
            main_sha=main_sha,
            health=health,
            attempts=attempts,
        )
        print(reason, file=sys.stderr)
        return 1

    reason = revision_mismatch_reason(tested_sha, main_sha)
    if reason:
        _write_failure(
            reason=reason,
            tested_sha=tested_sha,
            main_sha=main_sha,
            health=health,
            attempts=attempts,
        )
        print(reason, file=sys.stderr)
        return 1

    last_error: str | None = None
    for attempt in range(8):
        started = time.monotonic()
        try:
            health = _request_json(f"{api_base}/health", timeout_seconds=10)
            attempts.append({
                "attempt": attempt + 1,
                "result": "json_response",
                "elapsed_seconds": round(time.monotonic() - started, 3),
            })
            break
        except Exception as exc:
            last_error = type(exc).__name__
            attempts.append({
                "attempt": attempt + 1,
                "error": last_error,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            })
            if attempt < 7:
                time.sleep(min(8, 2 ** attempt))

    if health is None:
        reason = (
            f"Render health could not be verified after {len(attempts)} attempts "
            f"(last_error={last_error or 'unknown'})"
        )
    else:
        reason = runtime_mismatch_reason(tested_sha, main_sha, health)

    if reason:
        _write_failure(
            reason=reason,
            tested_sha=tested_sha,
            main_sha=main_sha,
            health=health,
            attempts=attempts,
        )
        print(reason, file=sys.stderr)
        return 1

    print(f"Render runtime preflight passed for current main {main_sha}; browser dependencies may be installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
