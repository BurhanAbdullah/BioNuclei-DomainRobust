from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.e2e_failure_artifact import persist_failure_payload, serialize_failure_payload


def test_failure_artifact_matches_the_logged_payload(tmp_path: Path) -> None:
    state = {
        "api_health_request_error": "ReadTimeout",
        "api_health_attempts": [{"attempt": 1, "error": "ReadTimeout"}],
        "guest_token_seen": False,
    }
    payload_text = serialize_failure_payload(state)
    path = tmp_path / "live-agent-e2e-failure.json"

    persist_failure_payload(path, payload_text)

    assert path.read_text(encoding="utf-8") == payload_text
    payload = json.loads(payload_text)
    assert payload["status"] == "FAIL"
    assert payload["api_health_request_error"] == "ReadTimeout"


def test_failure_artifact_write_errors_are_not_silenced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_write(self, data, encoding=None, errors=None, newline=None):
        raise PermissionError("synthetic write failure")

    monkeypatch.setattr(Path, "write_text", fail_write)
    with pytest.raises(PermissionError, match="synthetic write failure"):
        persist_failure_payload(tmp_path / "failure.json", '{"status":"FAIL"}\n')


def test_failure_artifact_readback_mismatch_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "failure.json"
    original_read = Path.read_text

    def altered_read(self, encoding=None, errors=None):
        content = original_read(self, encoding=encoding, errors=errors)
        return content.replace("ReadTimeout", "Timeout", 1) if self == path else content

    monkeypatch.setattr(Path, "read_text", altered_read)
    with pytest.raises(OSError, match="differs from the logged payload"):
        persist_failure_payload(path, '{"error":"ReadTimeout"}\n')
