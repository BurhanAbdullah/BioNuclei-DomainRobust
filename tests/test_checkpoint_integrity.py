from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml
from fastapi import HTTPException
from fastapi.testclient import TestClient

from webapp import app as scientific_app
from webapp import community_app
from webapp.app import RELEASE_CHECKPOINT_SHA256, _checkpoint, _checkpoint_identity


def _configure_checkpoint(tmp_path, monkeypatch, expected: str | None = None):
    path = tmp_path / "checkpoint.pt"
    path.write_bytes(b"deterministic checkpoint fixture")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(scientific_app, "RELEASE_CHECKPOINT_SHA256", actual)
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


def test_environment_digest_cannot_override_pinned_release(tmp_path, monkeypatch):
    path = tmp_path / "checkpoint.pt"
    path.write_bytes(b"checkpoint that is not the pinned release")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setenv("BIONUCLEI_CHECKPOINT", str(path))
    monkeypatch.setenv("BIONUCLEI_CHECKPOINT_SHA256", actual)
    monkeypatch.setattr(scientific_app, "RELEASE_CHECKPOINT_SHA256", "0" * 64)

    identity_path, digest, verified = _checkpoint_identity()
    assert identity_path == path.resolve()
    assert digest == actual
    assert verified is False

    with pytest.raises(HTTPException) as exc_info:
        _checkpoint()
    assert exc_info.value.status_code == 503

    for payload in (scientific_app.health(), community_app.health()):
        assert payload["status"] == "degraded"
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


def test_invalid_expected_digest_reports_available_unverified_checkpoint_and_fails_closed(tmp_path, monkeypatch):
    path, actual = _configure_checkpoint(tmp_path, monkeypatch, expected="not-a-sha256")

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


def test_checkpoint_digest_cache_reuses_verified_file_and_rejects_replacement(tmp_path, monkeypatch):
    path, actual = _configure_checkpoint(tmp_path, monkeypatch)
    hash_calls = 0
    original_hash = scientific_app._hash_checkpoint

    def counted_hash(stream):
        nonlocal hash_calls
        hash_calls += 1
        return original_hash(stream)

    monkeypatch.setattr(scientific_app, "_hash_checkpoint", counted_hash)

    assert scientific_app.health()["checkpoint_verified"] is True
    for _ in range(3):
        assert community_app.health()["checkpoint_verified"] is True
    assert hash_calls == 1

    replacement = tmp_path / "replacement.pt"
    replacement.write_bytes(b"X" * path.stat().st_size)
    replacement.replace(path)

    payload = community_app.health()
    assert payload["checkpoint_available"] is True
    assert payload["checkpoint_verified"] is False
    assert payload["checkpoint_sha256"] != actual
    assert hash_calls == 2

    with pytest.raises(HTTPException) as exc_info:
        _checkpoint()
    assert exc_info.value.status_code == 503


def test_community_startup_primes_checkpoint_digest_cache_before_health_requests(tmp_path, monkeypatch):
    _path, actual = _configure_checkpoint(tmp_path, monkeypatch)
    hash_calls = 0
    original_hash = scientific_app._hash_checkpoint

    def counted_hash(stream):
        nonlocal hash_calls
        hash_calls += 1
        return original_hash(stream)

    monkeypatch.setattr(scientific_app, "_hash_checkpoint", counted_hash)

    with TestClient(community_app.app) as client:
        first = client.get("/health")
        second = client.get("/health")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["checkpoint_verified"] is True
    assert second.json()["checkpoint_sha256"] == actual
    assert hash_calls == 1


def test_analyze_rejects_upload_before_job_creation_when_checkpoint_is_unverified(tmp_path, monkeypatch):
    path = tmp_path / "untrusted-checkpoint.pt"
    path.write_bytes(b"not the pinned release")
    monkeypatch.setattr(scientific_app, "RELEASE_CHECKPOINT_SHA256", "0" * 64)
    monkeypatch.setenv("BIONUCLEI_CHECKPOINT", str(path))
    monkeypatch.delenv("BIONUCLEI_CHECKPOINT_SHA256", raising=False)

    def unexpected_call(*_args, **_kwargs):
        pytest.fail("unverified checkpoint must reject the upload before auth or job creation")

    monkeypatch.setattr(community_app, "authenticate_optional", unexpected_call)
    monkeypatch.setattr(community_app, "create_job", unexpected_call)

    with TestClient(community_app.app) as client:
        response = client.post(
            "/analyze",
            data={"research_consent": "false"},
            files={"image": ("sample.tif", b"synthetic uint16 image", "image/tiff")},
        )

    assert response.status_code == 503
    assert "does not match the expected release SHA-256" in response.json()["detail"]


def test_root_and_health_report_configured_result_retention(monkeypatch):
    monkeypatch.setattr(community_app.community_service, "DEFAULT_RESULT_RETENTION_HOURS", 24)

    root_payload = community_app.root()
    health_payload = community_app.health()

    assert root_payload["result_retention_hours"] == 24
    assert "expire after 24 hours" in root_payload["retention"]
    assert health_payload["result_retention_hours"] == 24


def test_render_config_does_not_advertise_unimplemented_research_retention():
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / "render.yaml").read_text(encoding="utf-8"))
    community = next(
        service for service in config["services"]
        if service.get("name") == "bionuclei-community"
    )
    env_vars = {
        item["key"]: item.get("value")
        for item in community.get("envVars", [])
    }

    assert "BIONUCLEI_RESEARCH_RETENTION_DAYS" not in env_vars
    assert env_vars["BIONUCLEI_RESULT_RETENTION_HOURS"] == "24"


def test_main_deployment_gate_requires_pinned_checkpoint_and_configured_retention():
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load(
        (root / ".github/workflows/community_analyzer_validation.yml").read_text(encoding="utf-8")
    )
    live_job = workflow["jobs"]["live"]
    assert live_job["timeout-minutes"] >= 25
    live_steps = live_job["steps"]
    root_step = next(step for step in live_steps if step.get("name") == "Check service root")
    root_probe = root_step["run"]
    assert "--connect-timeout 10 --max-time 180" in root_probe
    assert "--retry" not in root_probe

    deploy_step = next(
        step for step in live_steps
        if step.get("name") == "Check deployed source revision on authorized main dispatch"
    )
    script = deploy_step["run"]

    expected_authorization = "${{ github.event_name == 'workflow_dispatch' && inputs.allow_live_render == true && github.ref == 'refs/heads/main' }}"
    assert live_job["if"] == expected_authorization
    assert deploy_step["if"] == expected_authorization
    workflow_text = (root / ".github/workflows/community_analyzer_validation.yml").read_text(encoding="utf-8")
    assert "allow_live_render:" in workflow_text
    assert "default: false" in workflow_text
    assert "checkpoint_available" in script
    assert "checkpoint_verified" in script
    assert "checkpoint_sha256" in script
    assert "7209a6990514380804210292ac208b0f3b0b0a054338a145e1916044762d7c92" in script
    assert "health_retention_hours" in script
    assert "root_retention_hours" in script
    assert 'expected_retention_hours="24"' in script
    assert "deadline=$((SECONDS + 540))" in script
    assert 'while [ "$SECONDS" -lt "$deadline" ]' in script
    assert "--max-time 15" in script
    assert "--retry" not in script


def test_bbbc039_baseline_training_is_main_only():
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load(
        (root / ".github/workflows/bbbc039_baseline.yml").read_text(encoding="utf-8")
    )
    job = workflow["jobs"]["train-evaluate"]
    assert job["if"] == "${{ github.ref == 'refs/heads/main' }}"
    assert job["timeout-minutes"] == 350

