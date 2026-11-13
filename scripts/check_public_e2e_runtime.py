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
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from .github_api_auth import github_api_headers
except ImportError:  # Running this file directly from the scripts directory.
    from github_api_auth import github_api_headers

DEFAULT_REPOSITORY = "BurhanAbdullah/BioNuclei-DomainRobust"
DEFAULT_API_BASE = "https://bionuclei-community-analyzer.onrender.com"
SHA_RE = re.compile(r"[0-9a-f]{40}")
EXPECTED_CHECKPOINT_SHA256 = "7209a6990514380804210292ac208b0f3b0b0a054338a145e1916044762d7c92"
RETRYABLE_GITHUB_HTTP_STATUS = {429, 500, 502, 503, 504}
RETRYABLE_RENDER_HTTP_STATUS = {429, 500, 502, 503, 504}
GITHUB_API_MAX_ATTEMPTS = 4
RENDER_HEALTH_MAX_ATTEMPTS = 8
RENDER_ROOT_WARMUP_TIMEOUT_SECONDS = 90.0
RENDER_ROOT_WARMUP_BUDGET_SECONDS = 179.0
RENDER_ROOT_WARMUP_MAX_ATTEMPTS = 2
RENDER_ROOT_WARMUP_RETRY_DELAY_SECONDS = 3.0


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
    reason = revision_mismatch_reason(tested_sha, main_sha)
    if reason:
        return reason
    if not isinstance(health, dict):
        return "Render health did not return a JSON object"
    if health.get("status") != "ok":
        return f"Render health status is not ok: {health.get('status')!r}"
    if health.get("checkpoint_available") is not True:
        return "Render health does not confirm checkpoint availability"
    if health.get("checkpoint_verified") is not True:
        return "Render health does not verify the immutable release checkpoint"
    checkpoint_sha256 = health.get("checkpoint_sha256")
    if checkpoint_sha256 != EXPECTED_CHECKPOINT_SHA256:
        return f"Render checkpoint digest differs from the pinned release: {checkpoint_sha256!r}"
    if health.get("render_git_branch") != "main":
        return f"Render is not serving branch main: {health.get('render_git_branch')!r}"
    deployed_sha = health.get("render_git_commit")
    if not isinstance(deployed_sha, str) or not SHA_RE.fullmatch(deployed_sha):
        return "Render health did not expose a valid deployed Git commit"
    if deployed_sha != main_sha:
        return f"Render runtime SHA mismatch: deployed_sha={deployed_sha}, current_main_sha={main_sha}"
    return None


def _request_json(url: str, timeout_seconds: float) -> dict[str, object]:
    if url.startswith("https://api.github.com/"):
        headers = github_api_headers(
            os.environ.get("GITHUB_TOKEN"),
            user_agent="bionuclei-public-e2e-runtime-preflight",
        )
    else:
        # Never send the GitHub credential to the public Render API.
        headers = {
            "Accept": "application/json",
            "User-Agent": "bionuclei-public-e2e-runtime-preflight",
        }
    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout_seconds) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON response was not an object")
    return payload


def _warm_render_service(api_base: str, attempts: list[dict[str, object]]) -> None:
    """Wake a slow Render instance within one bounded, retryable root-probe budget."""
    deadline = time.monotonic() + RENDER_ROOT_WARMUP_BUDGET_SECONDS
    for index in range(RENDER_ROOT_WARMUP_MAX_ATTEMPTS):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        started = time.monotonic()
        try:
            payload = _request_json(
                f"{api_base}/",
                timeout_seconds=min(RENDER_ROOT_WARMUP_TIMEOUT_SECONDS, remaining),
            )
        except HTTPError as exc:
            attempts.append({
                "attempt": index + 1,
                "error": type(exc).__name__,
                "http_status": exc.code,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            })
            if (
                exc.code not in RETRYABLE_RENDER_HTTP_STATUS
                or index + 1 >= RENDER_ROOT_WARMUP_MAX_ATTEMPTS
            ):
                raise
        except (URLError, TimeoutError) as exc:
            attempts.append({
                "attempt": index + 1,
                "error": type(exc).__name__,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            })
            if index + 1 >= RENDER_ROOT_WARMUP_MAX_ATTEMPTS:
                raise
        else:
            service = payload.get("service")
            status = payload.get("status")
            if service != "bionuclei-community-analyzer" or status != "online":
                attempts.append({
                    "attempt": index + 1,
                    "error": "UnexpectedRootPayload",
                    "service": service,
                    "status": status,
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                })
                raise RuntimeError("Render root did not identify the expected online community analyzer")

            attempts.append({
                "attempt": index + 1,
                "http_status": 200,
                "result": "root_warmup_complete",
                "service": service,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            })
            return

        remaining = deadline - time.monotonic()
        if index + 1 < RENDER_ROOT_WARMUP_MAX_ATTEMPTS and remaining > 0:
            delay = min(RENDER_ROOT_WARMUP_RETRY_DELAY_SECONDS, remaining)
            if attempts:
                attempts[-1]["retry_delay_seconds"] = round(delay, 3)
            if delay > 0:
                time.sleep(delay)

    raise TimeoutError("Render root warm-up exhausted its bounded retry budget")


def _request_json_with_retry(
    url: str,
    timeout_seconds: int,
    attempts: list[dict[str, object]],
) -> dict[str, object]:
    """Retry bounded transient GitHub API and Render health failures; keep the gate strict."""
    is_github_api = url.startswith("https://api.github.com/")
    max_attempts = GITHUB_API_MAX_ATTEMPTS if is_github_api else RENDER_HEALTH_MAX_ATTEMPTS
    retryable_statuses = RETRYABLE_GITHUB_HTTP_STATUS if is_github_api else RETRYABLE_RENDER_HTTP_STATUS
    for index in range(max_attempts):
        started = time.monotonic()
        try:
            payload = _request_json(url, timeout_seconds)
        except HTTPError as exc:
            attempts.append({
                "attempt": index + 1,
                "error": type(exc).__name__,
                "http_status": exc.code,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            })
            if exc.code not in retryable_statuses or index + 1 >= max_attempts:
                raise
        except (URLError, TimeoutError) as exc:
            attempts.append({
                "attempt": index + 1,
                "error": type(exc).__name__,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            })
            if index + 1 >= max_attempts:
                raise
        else:
            attempts.append({
                "attempt": index + 1,
                "http_status": 200,
                "result": "http_200",
                "elapsed_seconds": round(time.monotonic() - started, 3),
            })
            return payload
        time.sleep(min(8, 2 ** index))
    raise RuntimeError("GitHub API request exhausted its bounded retry budget")


def _export_expected_main_sha(main_sha: str) -> None:
    """Pass the authenticated, validated SHA to the next step in this workflow."""
    if not SHA_RE.fullmatch(main_sha):
        raise ValueError("Cannot export an invalid current-main SHA")
    github_env = os.environ.get("GITHUB_ENV")
    if github_env:
        with Path(github_env).open("a", encoding="utf-8") as handle:
            handle.write(f"BIONUCLEI_EXPECTED_MAIN_SHA={main_sha}\n")


def main() -> int:
    repository = os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPOSITORY)
    tested_sha = os.environ.get("GITHUB_SHA")
    api_base = os.environ.get("BIONUCLEI_PUBLIC_API_URL", DEFAULT_API_BASE).rstrip("/")
    main_sha: str | None = None
    health: dict[str, object] | None = None
    attempts: list[dict[str, object]] = []
    root_warmup_attempts: list[dict[str, object]] = []
    github_api_attempts: list[dict[str, object]] = []

    def fail(reason: str) -> int:
        payload: dict[str, object] = {
            "status": "FAIL",
            "phase": "runtime_preflight",
            "reason": reason,
            "expected_tested_commit": tested_sha,
            "expected_main_commit": main_sha,
            "render_git_branch": health.get("render_git_branch") if health else None,
            "render_git_commit": health.get("render_git_commit") if health else None,
            "checkpoint_available": health.get("checkpoint_available") if health else None,
            "checkpoint_verified": health.get("checkpoint_verified") if health else None,
            "checkpoint_sha256": health.get("checkpoint_sha256") if health else None,
            "github_api_attempts": github_api_attempts,
            "api_root_warmup_attempts": root_warmup_attempts,
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
        print(reason, file=sys.stderr)
        return 1

    try:
        main_payload = _request_json_with_retry(
            f"https://api.github.com/repos/{repository}/commits/main",
            timeout_seconds=10,
            attempts=github_api_attempts,
        )
        value = main_payload.get("sha")
        main_sha = value if isinstance(value, str) else None
    except Exception as exc:
        return fail(f"Could not resolve current main from GitHub: {type(exc).__name__}")

    reason = revision_mismatch_reason(tested_sha, main_sha)
    if reason:
        return fail(reason)

    try:
        _warm_render_service(api_base, root_warmup_attempts)
    except Exception as exc:
        return fail(f"Render root warm-up failed: {type(exc).__name__}")

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
        return fail(
            f"Render health could not be verified after {len(attempts)} attempts "
            f"(last_error={last_error or 'unknown'})"
        )
    reason = runtime_mismatch_reason(tested_sha, main_sha, health)
    if reason:
        return fail(reason)

    try:
        _export_expected_main_sha(main_sha)
    except Exception as exc:
        return fail(f"Could not pass the authenticated current-main SHA to the E2E step: {type(exc).__name__}")

    print(f"Render runtime preflight passed for current main {main_sha}; browser dependencies may be installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
