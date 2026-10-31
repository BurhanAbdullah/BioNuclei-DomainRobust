from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.github_api_auth import github_api_headers


def test_github_api_headers_require_a_token() -> None:
    with pytest.raises(RuntimeError, match="GITHUB_TOKEN is required"):
        github_api_headers(None, user_agent="bionuclei-test")


def test_github_api_headers_use_bearer_auth_without_mutating_the_token() -> None:
    headers = github_api_headers("  test-token  ", user_agent="bionuclei-test")
    assert headers == {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer test-token",
        "User-Agent": "bionuclei-test",
    }


def test_public_e2e_workflow_passes_read_only_token_only_to_the_harness() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load(
        (root / ".github/workflows/live-public-agent-e2e.yml").read_text(encoding="utf-8")
    )
    steps = workflow["jobs"]["public-upload-to-agent"]["steps"]
    e2e_step = next(
        step for step in steps
        if step.get("name") == "Exercise public upload and real scientific pipeline"
    )

    assert workflow["permissions"]["contents"] == "read"
    assert e2e_step["env"]["GITHUB_TOKEN"] == "${{ github.token }}"

    e2e_source = (root / "scripts/live_public_agent_e2e.py").read_text(encoding="utf-8")
    assert e2e_source.count('os.environ.get("GITHUB_TOKEN")') == 2
    assert e2e_source.count("headers=github_api_headers(") == 2
    # The public Render health probe remains unauthenticated: the GitHub
    # credential is sent only to api.github.com requests.
    assert 'requests.get(f"{API_BASE}/health", timeout=10)' in e2e_source
