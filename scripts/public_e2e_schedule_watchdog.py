"""Recover a missed scheduled public E2E run without weakening its gates.

The watchdog dispatches the existing workflow only when no current-main E2E is
active and the latest main-branch E2E is stale or targets an older SHA.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

WORKFLOW_FILE = "live-public-agent-e2e.yml"
MAX_AGE_SECONDS = 75 * 60
API_VERSION = "2022-11-28"
EXPECTED_REPOSITORY = "BurhanAbdullah/BioNuclei-DomainRobust"
PUBLIC_API_URL = os.environ.get(
    "BIONUCLEI_PUBLIC_API_URL",
    "https://bionuclei-community-analyzer.onrender.com",
).rstrip("/")
EXPECTED_CHECKPOINT_SHA256 = "7209a6990514380804210292ac208b0f3b0b0a054338a145e1916044762d7c92"
HEALTH_MAX_ATTEMPTS = 8
HEALTH_TIMEOUT_SECONDS = 10
HEALTH_RETRY_DELAYS_SECONDS = (1, 2, 4, 8, 8, 8, 8)


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
    deployed_sha: str | None = None,
) -> tuple[bool, str]:
    """Decide whether an E2E for current main is missing or stale.

    A queued/running exact-main run suppresses a duplicate. A recent exact-main
    run also suppresses a duplicate. Every new dispatch, including a first run
    after main advances, requires Render to report the current main SHA and the
    immutable checkpoint digest as verified. Runs on non-main branches are ignored.
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
        if deployed_sha is None:
            return False, "deployed Render SHA/checkpoint is unverified; refusing dispatch"
        if deployed_sha != main_sha:
            return False, (
                "Render is still behind current main "
                f"(deployed_sha={deployed_sha}, main_sha={main_sha}); refusing dispatch"
            )
        return True, "no main-branch public E2E run exists and Render runtime/checkpoint are verified"

    latest = max(main_runs, key=lambda run: str(run.get("created_at", "")))
    latest_sha = str(latest.get("head_sha", ""))
    try:
        age_seconds = (now - _timestamp(str(latest["created_at"]))).total_seconds()
    except (KeyError, TypeError, ValueError):
        if deployed_sha is None:
            return False, "deployed Render SHA/checkpoint is unverified; refusing dispatch"
        if deployed_sha != main_sha:
            return False, (
                "Render is still behind current main "
                f"(deployed_sha={deployed_sha}, main_sha={main_sha}); refusing dispatch"
            )
        return True, "latest main E2E timestamp is missing or invalid; Render runtime/checkpoint are verified"

    if latest_sha == main_sha and age_seconds < max_age_seconds:
        return False, f"current-main E2E is recent ({int(age_seconds)} seconds old)"

    if deployed_sha is None:
        return False, "deployed Render SHA/checkpoint is unverified; refusing dispatch"
    if deployed_sha != main_sha:
        return False, (
            "Render is still behind current main "
            f"(deployed_sha={deployed_sha}, main_sha={main_sha}); refusing dispatch"
        )

    return True, (
        f"latest E2E is stale for current main "
        f"(latest_sha={latest_sha or 'missing'}, age_seconds={int(age_seconds)})"
    )


def _github_server_time(value: str | None) -> datetime | None:
    """Parse GitHub's HTTP Date header as the authoritative API clock."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _api_request(
    repo: str,
    path: str,
    token: str,
    *,
    method: str = "GET",
    payload: dict[str, str] | None = None,
    include_server_time: bool = False,
) -> dict[str, object] | tuple[dict[str, object] | None, datetime | None] | None:
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
    date_header: str | None = None
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read()
            date_header = response.headers.get("Date") if getattr(response, "headers", None) else None
    except HTTPError as exc:
        # Do not print request headers or the token.
        detail = exc.read(2048).decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"GitHub API request failed: {exc.reason}") from exc

    parsed: dict[str, object] | None = None
    if raw:
        decoded = json.loads(raw.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise RuntimeError("GitHub API returned an unexpected JSON payload")
        parsed = decoded
    if include_server_time:
        return parsed, _github_server_time(date_header)
    return parsed


def _deployed_runtime_sha() -> str | None:
    """Return Render's main SHA only after a bounded cold-start retry and pin check."""
    last_error = "health endpoint did not return a response"
    for attempt in range(1, HEALTH_MAX_ATTEMPTS + 1):
        request = Request(
            f"{PUBLIC_API_URL}/health",
            headers={
                "Accept": "application/json",
                "User-Agent": "bionuclei-public-e2e-schedule-watchdog",
            },
        )
        try:
            with urlopen(request, timeout=HEALTH_TIMEOUT_SECONDS) as response:
                status = getattr(response, "status", None)
                if status != 200:
                    last_error = f"health endpoint returned HTTP {status}"
                else:
                    raw = response.read(16_384)
        except (URLError, OSError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        else:
            if status == 200:
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    last_error = f"health endpoint returned invalid JSON: {type(exc).__name__}"
                else:
                    if not isinstance(payload, dict):
                        print("Render health preflight: refusing non-object health payload")
                        return None
                    if payload.get("render_git_branch") != "main":
                        print("Render health preflight: refusing non-main runtime branch")
                        return None
                    if (
                        payload.get("status") != "ok"
                        or payload.get("checkpoint_available") is not True
                        or payload.get("checkpoint_verified") is not True
                        or payload.get("checkpoint_sha256") != EXPECTED_CHECKPOINT_SHA256
                    ):
                        print(
                            "Render health preflight: refusing unhealthy or unpinned checkpoint "
                            "identity"
                        )
                        return None
                    sha = str(payload.get("render_git_commit") or "")
                    if len(sha) != 40 or any(
                        char not in "0123456789abcdef" for char in sha
                    ):
                        print("Render health preflight: refusing invalid Render commit SHA")
                        return None
                    return sha

        if attempt < HEALTH_MAX_ATTEMPTS:
            delay = HEALTH_RETRY_DELAYS_SECONDS[attempt - 1]
            print(
                f"Render health preflight attempt {attempt}/{HEALTH_MAX_ATTEMPTS} "
                f"did not complete ({last_error}); retrying in {delay}s"
            )
            time.sleep(delay)

    print(
        f"Render health preflight failed after {HEALTH_MAX_ATTEMPTS} attempts "
        f"({last_error}); refusing dispatch"
    )
    return None

def main() -> int:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GH_TOKEN", "")
    if not repo or "/" not in repo:
        print("GITHUB_REPOSITORY is missing or invalid", file=sys.stderr)
        return 2
    if repo.casefold() != EXPECTED_REPOSITORY.casefold():
        print(
            "Public E2E watchdog: refusing to run outside upstream repository "
            f"({repo})",
            file=sys.stderr,
        )
        return 0
    if not token:
        print("GH_TOKEN is required; no dispatch attempted", file=sys.stderr)
        return 2

    commit = _api_request(repo, "commits/main", token)
    runs_result = _api_request(
        repo,
        f"actions/workflows/{WORKFLOW_FILE}/runs?branch=main&per_page=50",
        token,
        include_server_time=True,
    )
    if not commit or not isinstance(runs_result, tuple):
        raise RuntimeError("GitHub API omitted the main commit or workflow-run payload")
    runs_payload, github_now = runs_result
    if not runs_payload:
        raise RuntimeError("GitHub API omitted the workflow-run payload")
    if github_now is None:
        print("Public E2E watchdog: GitHub API server time is unavailable; refusing dispatch")
        return 0

    main_sha = str(commit.get("sha", ""))
    runs = runs_payload.get("workflow_runs", [])
    if not main_sha or not isinstance(runs, list):
        raise RuntimeError("GitHub API returned malformed main SHA or workflow runs")

    # Never dispatch any public E2E until Render proves the current revision
    # and immutable checkpoint identity, including after a main SHA advances.
    deployed_sha = _deployed_runtime_sha()
    dispatch, reason = should_dispatch(main_sha, runs, now=github_now, deployed_sha=deployed_sha)
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
