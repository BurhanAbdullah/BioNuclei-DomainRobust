from __future__ import annotations

import hashlib

import pytest
from fastapi import HTTPException

from webapp import app as scientific_app
from webapp import community_app
from webapp.app import RELEASE_CHECKPOINT_SHA256, _checkpoint, _checkpoint_identity


def _configure_checkpoint(tmp_path, monkeypatch, expected: str | None = None):
    path = tmp_path / "checkpoint.pt"
    path.write_bytes(b"deterministic checkpoint fixture")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setenv("BIONUCLEI_CHECKPOINT", str(path))
    monkeypatch.setenv("BIONUCLEI_CHECKPOINT_SHA256", expected or actual)
    return path, actual


def test_checkpoint_identity_and_both_health_endpoints_report_actual_digest(tmp_path, monkeypatch):
    path, actual = _configure_checkpoint(tmp_path, monkeypatch)

    identity_path, digest, verified = _checkpoint_identity()
    assert identity_path == path.resolve()
    assert digest == actual
    assert verified is True
    assert _checkpoint() == path.resolve()

    for payload in (scientific_app.health(), community_app.health()):
        assert payload["status"] == "ok"
        assert payload["checkpoint_available"] is True
        assert payload["checkpoint_verified"] is True
        assert payload["checkpoint_sha256"] == actual


def test_checkpoint_digest_mismatch_blocks_inference_and_degrades_health(tmp_path, monkeypatch):
    path, actual = _configure_checkpoint(tmp_path, monkeypatch, expected="0" * 64)

    identity_path, digest, verified = _checkpoint_identity()
    assert identity_path == path.resolve()
    assert digest == actual
    assert verified is False

    with pytest.raises(HTTPException) as exc_info:
        _checkpoint()
    assert exc_info.value.status_code == 503

    for payload in (scientific_app.health(), community_app.health()):
        assert payload["status"] == "degraded"
        assert payload["checkpoint_available"] is True
        assert payload["checkpoint_verified"] is False
        assert payload["checkpoint_sha256"] == actual


def test_missing_checkpoint_is_not_reported_healthy(tmp_path, monkeypatch):
    monkeypatch.setenv("BIONUCLEI_CHECKPOINT", str(tmp_path / "missing.pt"))
    monkeypatch.setenv("BIONUCLEI_CHECKPOINT_SHA256", RELEASE_CHECKPOINT_SHA256)

    with pytest.raises(HTTPException) as exc_info:
        _checkpoint()
    assert exc_info.value.status_code == 503

    for payload in (scientific_app.health(), community_app.health()):
        assert payload["status"] == "degraded"
        assert payload["checkpoint_available"] is False
        assert payload["checkpoint_verified"] is False
        assert payload["checkpoint_sha256"] is None


def test_invalid_expected_digest_fails_closed(tmp_path, monkeypatch):
    _configure_checkpoint(tmp_path, monkeypatch, expected="not-a-sha256")
    with pytest.raises(HTTPException) as exc_info:
        _checkpoint_identity()
    assert exc_info.value.status_code == 503

    assert scientific_app.health()["status"] == "degraded"
    assert community_app.health()["status"] == "degraded"
