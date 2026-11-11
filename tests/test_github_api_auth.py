from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts import check_public_e2e_runtime as preflight
from scripts.github_api_auth import github_api_headers
from scripts.write_e2e_setup_failure import (
    build_setup_failure_payload,
    write_setup_failure_artifact,
)


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


def test_public_e2e_workflow_preflights_runtime_before_browser_dependencies() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load(
        (root / ".github/workflows/live-public-agent-e2e.yml").read_text(encoding="utf-8")
    )
    steps = workflow["jobs"]["public-upload-to-agent"]["steps"]
    names = [step.get("name") for step in steps]

    preflight_index = names.index("Verify deployed runtime before browser dependency installation")
    install_index = names.index("Install browser E2E dependencies")
    assert preflight_index < install_index

    preflight_step = steps[preflight_index]
    assert preflight_step["run"] == "python scripts/check_public_e2e_runtime.py"
    assert preflight_step["env"]["GITHUB_REPOSITORY"] == "$" + "{{ github.repository }}"
    assert preflight_step["env"]["GITHUB_SHA"] == "$" + "{{ github.sha }}"
    assert preflight_step["env"]["GITHUB_TOKEN"] == "$" + "{{ github.token }}"

    assert workflow["permissions"]["contents"] == "read"
    assert workflow["jobs"]["public-upload-to-agent"]["if"] == "github.ref == 'refs/heads/main'"
    assert workflow["jobs"]["validate-harness"]["if"] == "github.event_name == 'pull_request'"
    e2e_step = next(
        step for step in steps
        if step.get("name") == "Exercise public upload and real scientific pipeline"
    )
    assert e2e_step["env"]["GITHUB_TOKEN"] == "$" + "{{ github.token }}"

    e2e_source = (root / "scripts/live_public_agent_e2e.py").read_text(encoding="utf-8")
    assert e2e_source.count('os.environ.get("GITHUB_TOKEN")') == 2
    assert e2e_source.count("headers=github_api_headers(") == 2
    # The public Render health probe remains unauthenticated: the GitHub
    # credential is sent only to api.github.com requests.
    assert 'requests.get(f"{API_BASE}/health", timeout=10)' in e2e_source


def test_setup_failure_payload_never_claims_public_inference() -> None:
    payload = build_setup_failure_payload(
        "browser_dependency_installation",
        {
            "GITHUB_RUN_ID": "123",
            "GITHUB_RUN_ATTEMPT": "2",
            "GITHUB_SHA": "a" * 40,
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_EVENT_NAME": "schedule",
            "RUNNER_OS": "Linux",
            "GITHUB_TOKEN": "must-not-be-copied",
        },
    )

    assert payload["status"] == "FAIL"
    assert payload["failure_kind"] == "setup"
    assert payload["failure_stage"] == "browser_dependency_installation"
    assert payload["run_id"] == "123"
    assert payload["run_attempt"] == "2"
    assert payload["public_upload_attempted"] is False
    assert payload["inference_started"] is False
    assert payload["cleanup_attempted"] is False
    assert "GITHUB_TOKEN" not in payload
    assert "must-not-be-copied" not in str(payload)


def test_setup_failure_artifact_preserves_existing_harness_evidence(tmp_path: Path) -> None:
    output = tmp_path / "live-agent-e2e-failure.json"
    existing = '{"status":"FAIL","failure_stage":"public_inference"}'
    output.write_text(existing, encoding="utf-8")

    created = write_setup_failure_artifact(
        output,
        "browser_dependency_installation",
        {"GITHUB_RUN_ID": "123"},
    )

    assert created is False
    assert output.read_text(encoding="utf-8") == existing


def test_setup_failure_artifact_is_written_when_harness_evidence_is_absent(tmp_path: Path) -> None:
    output = tmp_path / "live-agent-e2e-failure.json"

    created = write_setup_failure_artifact(
        output,
        "browser_dependency_installation",
        {
            "GITHUB_RUN_ID": "123",
            "GITHUB_SHA": "a" * 40,
            "GITHUB_EVENT_NAME": "schedule",
            "RUNNER_OS": "Linux",
        },
    )

    assert created is True
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["run_id"] == "123"
    assert payload["failure_stage"] == "browser_dependency_installation"
    assert payload["public_upload_attempted"] is False


def test_live_e2e_workflow_records_browser_setup_failure_before_artifact_upload() -> None:
    workflow = yaml.safe_load(
        Path(".github/workflows/live-public-agent-e2e.yml").read_text(encoding="utf-8")
    )
    steps = workflow["jobs"]["public-upload-to-agent"]["steps"]
    install = next(step for step in steps if step.get("name") == "Install browser E2E dependencies")
    fallback = next(step for step in steps if step.get("name") == "Record browser dependency failure evidence")
    upload = next(step for step in steps if step.get("name") == "Upload browser failure evidence")

    assert install["id"] == "browser_deps"
    assert fallback["if"] == "${{ failure() && steps.browser_deps.outcome == 'failure' }}"
    assert "scripts/write_e2e_setup_failure.py" in fallback["run"]
    assert steps.index(fallback) < steps.index(upload)
    assert "live-agent-e2e-failure.json" in upload["with"]["path"]
