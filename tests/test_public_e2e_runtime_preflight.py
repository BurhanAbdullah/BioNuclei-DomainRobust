from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError

import pytest
import yaml

from scripts import check_public_e2e_runtime as preflight
from scripts.check_public_e2e_runtime import revision_mismatch_reason, runtime_mismatch_reason


MAIN_SHA = "a" * 40
STALE_SHA = "b" * 40
PINNED_CHECKPOINT_SHA256 = "7209a6990514380804210292ac208b0f3b0b0a054338a145e1916044762d7c92"


def healthy_runtime(**overrides: object) -> dict[str, object]:
    return {
        "status": "ok",
        "checkpoint_available": True,
        "checkpoint_verified": True,
        "checkpoint_sha256": PINNED_CHECKPOINT_SHA256,
        "render_git_branch": "main",
        "render_git_commit": MAIN_SHA,
        **overrides,
    }


def test_runtime_preflight_accepts_only_exact_current_main() -> None:
    assert revision_mismatch_reason(MAIN_SHA, MAIN_SHA) is None
    assert runtime_mismatch_reason(MAIN_SHA, MAIN_SHA, healthy_runtime()) is None


def test_runtime_preflight_rejects_stale_workflow_revision() -> None:
    reason = revision_mismatch_reason(STALE_SHA, MAIN_SHA)
    assert reason is not None
    assert "workflow revision is stale" in reason


def test_runtime_preflight_rejects_stale_render_deployment() -> None:
    reason = runtime_mismatch_reason(MAIN_SHA, MAIN_SHA, healthy_runtime(render_git_commit=STALE_SHA))
    assert reason is not None
    assert "Render runtime SHA mismatch" in reason


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"render_git_branch": "preview"}, "not serving branch main"),
        ({"checkpoint_available": False}, "checkpoint availability"),
        ({"checkpoint_verified": False}, "does not verify the immutable release checkpoint"),
        ({"checkpoint_sha256": "0" * 64}, "differs from the pinned release"),
        ({"status": "starting"}, "health status is not ok"),
        ({"render_git_commit": "not-a-sha"}, "valid deployed Git commit"),
    ],
)
def test_runtime_preflight_rejects_unready_or_unverifiable_render(
    overrides: dict[str, object],
    message: str,
) -> None:
    reason = runtime_mismatch_reason(MAIN_SHA, MAIN_SHA, healthy_runtime(**overrides))
    assert reason is not None
    assert message in reason


def test_runtime_preflight_fails_closed_on_missing_health_payload() -> None:
    reason = runtime_mismatch_reason(MAIN_SHA, MAIN_SHA, None)
    assert reason == "Render health did not return a JSON object"


def test_runtime_preflight_fails_closed_when_checkpoint_identity_is_missing() -> None:
    health = healthy_runtime()
    health.pop("checkpoint_verified")
    reason = runtime_mismatch_reason(MAIN_SHA, MAIN_SHA, health)
    assert reason == "Render health does not verify the immutable release checkpoint"


def test_main_records_fail_closed_runtime_mismatch_without_upload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "example/repo")
    monkeypatch.setenv("GITHUB_SHA", MAIN_SHA)
    monkeypatch.chdir(tmp_path)
    requests: list[str] = []

    def fake_request_json(url: str, timeout_seconds: int) -> dict[str, object]:
        requests.append(url)
        if url.startswith("https://api.github.com/"):
            return {"sha": MAIN_SHA}
        return healthy_runtime(render_git_commit=STALE_SHA)

    monkeypatch.setattr(preflight, "_request_json", fake_request_json)

    assert preflight.main() == 1
    assert len(requests) == 2
    payload = json.loads((tmp_path / "live-agent-e2e-failure.json").read_text(encoding="utf-8"))
    assert payload["phase"] == "runtime_preflight"
    assert "Render runtime SHA mismatch" in payload["reason"]
    assert payload["public_upload_attempted"] is False
    assert payload["guest_token_seen"] is False
    assert payload["job_id_seen"] is False
    assert payload["cleanup_attempted"] is False
    assert payload["cleanup_verified"] is False


def test_request_json_reads_complete_response(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status = 200

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"sha": MAIN_SHA, "padding": "x" * 70000}).encode("utf-8")

    monkeypatch.setattr(preflight, "urlopen", lambda _request, timeout: Response())
    payload = preflight._request_json("https://example.test/health", timeout_seconds=1)

    assert payload["sha"] == MAIN_SHA
    assert len(payload["padding"]) == 70000


def test_request_json_with_retry_recovers_from_github_504(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def fake_request_json(url: str, timeout_seconds: int) -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise HTTPError(url, 504, "Gateway Timeout", None, None)
        return {"sha": MAIN_SHA}

    monkeypatch.setattr(preflight, "_request_json", fake_request_json)
    monkeypatch.setattr(preflight.time, "sleep", lambda _delay: None)
    attempts: list[dict[str, object]] = []

    payload = preflight._request_json_with_retry(
        "https://api.github.com/repos/example/repo/commits/main",
        timeout_seconds=10,
        attempts=attempts,
    )

    assert payload["sha"] == MAIN_SHA
    assert calls == 2
    assert attempts[0]["http_status"] == 504
    assert attempts[1]["http_status"] == 200


def test_request_json_with_retry_does_not_retry_non_transient_github_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def fail_forbidden(url: str, timeout_seconds: int) -> dict[str, object]:
        nonlocal calls
        calls += 1
        raise HTTPError(url, 403, "Forbidden", None, None)

    monkeypatch.setattr(preflight, "_request_json", fail_forbidden)
    monkeypatch.setattr(preflight.time, "sleep", lambda _delay: None)
    attempts: list[dict[str, object]] = []

    with pytest.raises(HTTPError):
        preflight._request_json_with_retry(
            "https://api.github.com/repos/example/repo/commits/main",
            timeout_seconds=10,
            attempts=attempts,
        )

    assert calls == 1
    assert attempts[0]["http_status"] == 403


def test_export_expected_main_sha_to_github_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    github_env = tmp_path / "github_env"
    monkeypatch.setenv("GITHUB_ENV", str(github_env))

    preflight._export_expected_main_sha(MAIN_SHA)

    assert github_env.read_text(encoding="utf-8") == f"BIONUCLEI_EXPECTED_MAIN_SHA={MAIN_SHA}\\n"


def test_live_e2e_reuses_the_authenticated_preflight_sha() -> None:
    root = Path(__file__).resolve().parents[1]
    e2e_source = (root / "scripts/live_public_agent_e2e.py").read_text(encoding="utf-8")

    assert 'os.environ.get("BIONUCLEI_EXPECTED_MAIN_SHA", "")' in e2e_source
    assert 'state["expected_main_commit_source"] = "authenticated_runtime_preflight"' in e2e_source
    assert 'os.environ.get("GITHUB_ACTIONS") != "true"' in e2e_source


def test_render_build_inputs_trigger_main_public_e2e() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.load(
        (root / ".github/workflows/live-public-agent-e2e.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    push_paths = set(workflow["on"]["push"]["paths"])

    # These files/directories are copied into the Render images and must
    # trigger the public E2E when main changes them.
    assert {
        "webapp/**",
        "src/**",
        "pyproject.toml",
        "README.md",
        "configs/**",
        "render.yaml",
        "docs/RESEARCH_PROTOCOL.md",
        "docs/DATASETS.md",
    } <= push_paths
