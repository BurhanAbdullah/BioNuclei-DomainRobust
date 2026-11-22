from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest
import torch
import tifffile
from fastapi import HTTPException
from fastapi.testclient import TestClient


import bionuclei.inference as inference_module
from bionuclei.inference import _load_model, predict
from webapp import app as scientific_app
from webapp import community_app
from webapp.app import RELEASE_CHECKPOINT_SHA256, _checkpoint, _checkpoint_identity


@pytest.fixture(autouse=True)
def _close_checkpoint_fds_after_test():
    yield
    scientific_app._close_checkpoint_load_fds()


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
    fd_path = _checkpoint()
    assert fd_path.parent == Path("/proc/self/fd")
    assert fd_path.read_bytes() == path.read_bytes()

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


def test_verified_checkpoint_fd_load_survives_path_replacement(tmp_path, monkeypatch):
    path = tmp_path / "checkpoint.pt"
    torch.save({"weights": torch.tensor([1, 2, 3])}, path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(scientific_app, "RELEASE_CHECKPOINT_SHA256", digest)
    monkeypatch.setenv("BIONUCLEI_CHECKPOINT", str(path))
    monkeypatch.setenv("BIONUCLEI_CHECKPOINT_SHA256", digest)

    fd_path = _checkpoint()
    replacement = tmp_path / "replacement.pt"
    torch.save({"weights": torch.tensor([9, 9, 9])}, replacement)
    replacement.replace(path)

    # The descriptor still points to the verified original, but its ctime
    # changed when the pathname was replaced; inference must fail closed.
    loaded = torch.load(fd_path, map_location="cpu", mmap=True, weights_only=True)
    assert loaded["weights"].tolist() == [1, 2, 3]
    with pytest.raises(RuntimeError, match="verified checkpoint identity changed"):
        _load_model(fd_path)


def test_verified_checkpoint_fd_rejects_in_place_change_before_load(tmp_path, monkeypatch):
    path = tmp_path / "checkpoint.pt"
    torch.save({"weights": torch.tensor([1, 2, 3])}, path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(scientific_app, "RELEASE_CHECKPOINT_SHA256", digest)
    monkeypatch.setenv("BIONUCLEI_CHECKPOINT", str(path))
    monkeypatch.setenv("BIONUCLEI_CHECKPOINT_SHA256", digest)

    fd_path = _checkpoint()
    with path.open("r+b") as stream:
        stream.seek(0)
        stream.write(b"X")

    with pytest.raises(RuntimeError, match="verified checkpoint identity changed"):
        _load_model(fd_path)

def _save_small_checkpoint(path: Path, fill: float = 0.125) -> BoundaryUNet:
    model = BoundaryUNet(in_channels=1, out_channels=3, base_channels=4)
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.fill_(fill)
    torch.save(
        {
            "config": {"model": {"in_channels": 1, "out_channels": 3, "base_channels": 4}},
            "model": model.state_dict(),
        },
        path,
    )
    return model



def test_loader_rejects_in_place_checkpoint_change_during_torch_load(tmp_path, monkeypatch):
    path = tmp_path / "checkpoint.pt"
    _save_small_checkpoint(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(scientific_app, "RELEASE_CHECKPOINT_SHA256", digest)
    monkeypatch.setenv("BIONUCLEI_CHECKPOINT", str(path))
    monkeypatch.setenv("BIONUCLEI_CHECKPOINT_SHA256", digest)


    fd_path = _checkpoint()
    original_load = torch.load

    def load_then_mutate(*args, **kwargs):
        state = original_load(*args, **kwargs)
        with path.open("r+b") as stream:
            stream.seek(0)
            stream.write(b"X")
        return state



    monkeypatch.setattr(inference_module.torch, "load", load_then_mutate)
    with pytest.raises(RuntimeError, match="verified checkpoint identity changed"):
        _load_model(fd_path)



def test_predict_rejects_checkpoint_change_during_inference(tmp_path, monkeypatch):
    path = tmp_path / "checkpoint.pt"
    _save_small_checkpoint(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(scientific_app, "RELEASE_CHECKPOINT_SHA256", digest)
    monkeypatch.setenv("BIONUCLEI_CHECKPOINT", str(path))
    monkeypatch.setenv("BIONUCLEI_CHECKPOINT_SHA256", digest)


    fd_path = _checkpoint()
    image_path = tmp_path / "image.tif"
    tifffile.imwrite(image_path, np.arange(64, dtype=np.uint16).reshape(8, 8))
    output = tmp_path / "output"



    def mutate_during_prediction(_model, x, *, tile_size=256, overlap=128):
        with path.open("r+b") as stream:
            stream.seek(0)
            stream.write(b"X")
        return torch.zeros((1, 3, *x.shape[-2:]), dtype=torch.float32, device=x.device)



    monkeypatch.setattr(inference_module, "_predict_logits", mutate_during_prediction)
    with pytest.raises(RuntimeError, match="verified checkpoint identity changed"):
        predict(image_path, fd_path, output, device="cpu")
    assert not output.exists()
