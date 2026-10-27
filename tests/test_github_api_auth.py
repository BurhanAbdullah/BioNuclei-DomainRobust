from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts import check_public_e2e_runtime as preflight
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


def test_runtime_preflight_authenticates_github_but_never_render(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    captured: list[tuple[str, str | None]] = []

    class Response:
        status = 200

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"sha": "a" * 40}).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured.append((request.full_url, request.get_header("Authorization")))
        return Response()

    monkeypatch.setattr(preflight, "urlopen", fake_urlopen)
    preflight._request_json(
        "https://api.github.com/repos/example/repo/commits/main",
        timeout_seconds=1,
    )
    preflight._request_json("https://example.test/health", timeout_seconds=1)

    assert captured == [
        ("https://api.github.com/repos/example/repo/commits/main", "Bearer test-token"),
        ("https://example.test/health", None),
    ]


def test_public_e2e_workflow_passes_read_only_token_to_both_github_api_steps() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load(
        (root / ".github/workflows/live-public-agent-e2e.yml").read_text(encoding="utf-8")
    )
    steps = workflow["jobs"]["public-upload-to-agent"]["steps"]
    by_name = {step.get("name"): step for step in steps}

    assert workflow["permissions"]["contents"] == "read"
    assert by_name["Verify deployed runtime before browser dependency installation"]["env"]["GITHUB_TOKEN"] == "${{ github.token }}"
    assert by_name["Exercise public upload and real scientific pipeline"]["env"]["GITHUB_TOKEN"] == "${{ github.token }}"

    e2e_source = (root / "scripts/live_public_agent_e2e.py").read_text(encoding="utf-8")
    assert e2e_source.count('os.environ.get("GITHUB_TOKEN")') == 2
    assert e2e_source.count("headers=github_api_headers(") == 2
