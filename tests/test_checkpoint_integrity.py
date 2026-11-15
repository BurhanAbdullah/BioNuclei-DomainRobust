from __future__ import annotations

import hashlib

import pytest
from fastapi import HTTPException

from webapp import app as scientific_app
from webapp import community_app
from webapp.app import _checkpoint, _checkpoint_identity


def _configure_checkpoint(
    tmp_path,
    monkeypatch,
    *,
    pinned_sha256: str | None = None,
    configured_sha256: str | None = None,
):
    path = tmp_path / "checkpoint.pt"
    path.write_bytes(b"deterministic checkpoint fixture")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(
        scientific_app,
        "RELEASE_CHECKPOINT_SHA256",
        pinned_sha256 or actual,
    )
    monkeypatch.setenv("BIONUCLEI_CHECKPOINT", str(path))
    if configured_sha256 is None:
        monkeypatch.delenv("BIONUCLEI_CHECKPOINT_SHA256", raising=False)
    else:
        monkeypatch.setenv("BIONUCLEI_CHECKPOINT_SHA256", configured_sha256)
    return path, actual


def test_checkpoint_identity_and_both_health_endpoints_report_actual_digest(
    tmp_path,
    monkeypatch,
):
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


def test_checkpoint_digest_mismatch_blocks_inference_and_degrades_health(
    tmp_path,
    monkeypatch,
):
    path, actual = _configure_checkpoint(
        tmp_path,
        monkeypatch,
        pinned_sha256="0" * 64,
        configured_sha256="0" * 64,
    )

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


def test_environment_digest_cannot_override_pinned_release(tmp_path, monkeypatch):
    path, actual = _configure_checkpoint(
        tmp_path,
        monkeypatch,
        pinned_sha256="0" * 64,
        configured_sha256=None,
    )
    monkeypatch.setenv("BIONUCLEI_CHECKPOINT_SHA256", actual)

    identity_path, digest, verified = _checkpoint_identity()
    assert identity_path == path.resolve()
    assert digest == actual
    assert verified is False

    with pytest.raises(HTTPException) as exc_info:
        _checkpoint()
    assert exc_info.value.status_code == 503


def test_prefixed_environment_digest_is_accepted_only_when_it_matches_release(
    tmp_path,
    monkeypatch,
):
    path, actual = _configure_checkpoint(
        tmp_path,
        monkeypatch,
        configured_sha256=f"sha256:{hashlib.sha256(b'deterministic checkpoint fixture').hexdigest()}",
    )

    identity_path, digest, verified = _checkpoint_identity()
    assert identity_path == path.resolve()
    assert digest == actual
    assert verified is True


def test_invalid_environment_digest_fails_closed(tmp_path, monkeypatch):
    path, actual = _configure_checkpoint(
        tmp_path,
        monkeypatch,
        configured_sha256="not-a-sha256",
    )

    identity_path, digest, verified = _checkpoint_identity()
    assert identity_path == path.resolve()
    assert digest == actual
    assert verified is False
    assert scientific_app.health()["status"] == "degraded"
    assert community_app.health()["checkpoint_verified"] is False


def test_missing_checkpoint_is_not_reported_healthy(tmp_path, monkeypatch):
    monkeypatch.setenv("BIONUCLEI_CHECKPOINT", str(tmp_path / "missing.pt"))
    monkeypatch.delenv("BIONUCLEI_CHECKPOINT_SHA256", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        _checkpoint()
    assert exc_info.value.status_code == 503

    for payload in (scientific_app.health(), community_app.health()):
        assert payload["status"] == "degraded"
        assert payload["checkpoint_available"] is False
        assert payload["checkpoint_verified"] is False
        assert payload["checkpoint_sha256"] is None


def test_checkpoint_digest_cache_reuses_stable_file_and_rehashes_after_change(
    tmp_path,
    monkeypatch,
):
    path, actual = _configure_checkpoint(tmp_path, monkeypatch)
    scientific_app._checkpoint_sha256.cache_clear()
    try:
        assert _checkpoint_identity()[1] == actual
        assert _checkpoint_identity()[1] == actual
        assert scientific_app._checkpoint_sha256.cache_info().hits == 1

        path.write_bytes(b"modified checkpoint fixture")
        changed_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        identity_path, digest, verified = _checkpoint_identity()
        assert identity_path == path.resolve()
        assert digest == changed_digest
        assert digest != actual
        assert verified is False
        assert scientific_app._checkpoint_sha256.cache_info().misses == 2
    finally:
        scientific_app._checkpoint_sha256.cache_clear()
