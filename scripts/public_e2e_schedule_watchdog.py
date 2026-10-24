"""Recover a missed scheduled public E2E run without weakening its gates.

The watchdog dispatches the existing workflow only when no current-main E2E is
active and the latest main-branch E2E is stale or targets an older SHA.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

WORKFLOW_FILE = "live-public-agent-e2e.yml"
MAX_AGE_SECONDS = 75 * 60
API_VERSION = "2022-11-28"


def _timestamp(value: str) -> datetime:
    """Parse a GitHub ISO-8601 timestamp as an aware UTC datetime."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def should_dispatch(
    main_sha: str,
    workflow_runs: list[dict[str, object]],
    *,
    now: datetime | None = None,
    max_age_seconds: int = MAX_AGE_SECONDS,
) -> tuple[bool, str]:
    """Decide whether an E2E for current main is missing or stale.

    A queued/running exact-main run suppresses a duplicate. A recent completed
    run for an older SHA does not satisfy current-main acceptance. Runs on
    non-main branches are ignored.
    """
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    main_runs = [run for run in workflow_runs if run.get("head_branch") == "main"]

    active_current = [
        run
        for run in main_runs
        if run.get("head_sha") == main_sha
        and run.get("status") in {"queued", "in_progress", "waiting", "requested", "pending"}
    ]
    if active_current:
        return False, "an exact-current-main E2E is already queued or running"

    if not main_runs:
        return True, "no main-branch public E2E run exists"

    latest = max(main_runs, key=lambda run: str(run.get("created_at", "")))
    latest_sha = str(latest.get("head_sha", ""))
    try:
        age_seconds = (now - _timestamp(str(latest["created_at"]))).total_seconds()
    except (KeyError, TypeError, ValueError):
        return True, "latest main E2E timestamp is missing or invalid"

    if latest_sha == main_sha and age_seconds < max_age_seconds:
        return False, f"current-main E2E is recent ({int(age_seconds)} seconds old)"

    return True, (
        f"latest E2E is stale for current main "
        f"(latest_sha={latest_sha or 'missing'}, age_seconds={int(age_seconds)})"
    )


def _api_request(
    repo: str,
    path: str,
    token: str,
    *,
    method: str = "GET",
    payload: dict[str, str] | None = None,
) -> dict[str, object] | None:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"https://api.github.com/repos/{repo}/{path}",
        data=body,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "bionuclei-public-e2e-schedule-watchdog",
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read()
    except HTTPError as exc:
        # Do not print request headers or the token.
        detail = exc.read(2048).decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"GitHub API request failed: {exc.reason}") from exc

    if not raw:
        return None
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise RuntimeError("GitHub API returned an unexpected JSON payload")
    return parsed


def main() -> int:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GH_TOKEN", "")
    if not repo or "/" not in repo:
        print("GITHUB_REPOSITORY is missing or invalid", file=sys.stderr)
        return 2
    if not token:
        print("GH_TOKEN is required; no dispatch attempted", file=sys.stderr)
        return 2

    commit = _api_request(repo, "commits/main", token)
    runs_payload = _api_request(
        repo,
        f"actions/workflows/{WORKFLOW_FILE}/runs?branch=main&per_page=50",
        token,
    )
    if not commit or not runs_payload:
        raise RuntimeError("GitHub API omitted the main commit or workflow-run payload")

    main_sha = str(commit.get("sha", ""))
    runs = runs_payload.get("workflow_runs", [])
    if not main_sha or not isinstance(runs, list):
        raise RuntimeError("GitHub API returned malformed main SHA or workflow runs")

    dispatch, reason = should_dispatch(main_sha, runs)
    print(f"Public E2E watchdog: {reason}")
    if not dispatch:
        return 0

    print(f"Dispatching existing public E2E workflow for current main {main_sha}")
    _api_request(
        repo,
        f"actions/workflows/{WORKFLOW_FILE}/dispatches",
        token,
        method="POST",
        payload={"ref": "main"},
    )
    print("Dispatch request accepted; the E2E parity guard remains unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
