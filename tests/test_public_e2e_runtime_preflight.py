from __future__ import annotations

import json

import pytest

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
