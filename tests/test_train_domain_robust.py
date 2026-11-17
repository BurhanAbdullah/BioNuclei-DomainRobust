import pytest
import torch
from pathlib import Path

from scripts.train_domain_robust import (
    build_training_method_record,
    load_checkpoint,
    resolve_device,
    sha256_file,
)


def test_resolve_device_auto_falls_back_to_cpu(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert resolve_device("auto").type == "cpu"


def test_resolve_device_auto_uses_cuda_when_available(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert resolve_device("auto").type == "cuda"


def test_source_training_record_uses_the_actual_manifest():
    manifest = {
        "dataset": "BBBC039v1",
        "partitions": {"train": ["image-1.tif", "image-2.tif"]},
    }

    record = build_training_method_record(manifest, "a" * 64, 42)

    assert record == {
        "method": "supervised_training",
        "training_dataset": "BBBC039v1",
        "training_manifest_sha256": "a" * 64,
        "training_image_count": 2,
        "seed": 42,
        "init_checkpoint_sha256": None,
    }
    assert "adaptation_dataset" not in record


def test_checkpoint_initialized_training_records_checkpoint_digest():
    manifest = {
        "dataset": "BBBC039v1",
        "partitions": {"train": ["image-1.tif"]},
    }

    record = build_training_method_record(manifest, "a" * 64, 42, "b" * 64)

    assert record["method"] == "checkpoint_initialized_training"
    assert record["training_dataset"] == "BBBC039v1"
    assert record["init_checkpoint_sha256"] == "b" * 64


def test_training_method_record_rejects_missing_training_partition():
    with pytest.raises(ValueError, match="non-empty train partition"):
        build_training_method_record(
            {"dataset": "BBBC039v1", "partitions": {"train": []}},
            "a" * 64,
            42,
        )


def test_sha256_file_hashes_checkpoint_bytes(tmp_path):
    path = tmp_path / "checkpoint.pt"
    path.write_bytes(b"verified checkpoint bytes")

    assert sha256_file(path) == "502fc47eb3b5a9e463ea127f3619c5790ce1c3433ec5bd1a2af8fcb99056378e"


def test_initial_checkpoint_loader_explicitly_uses_weights_only(monkeypatch, tmp_path):
    checkpoint = tmp_path / "initial.pt"
    expected = {"model": {"weight": torch.tensor([1.0, 2.0])}}
    observed = {}

    def safe_load(path, *, map_location, weights_only):
        observed.update(
            path=Path(path),
            map_location=map_location,
            weights_only=weights_only,
        )
        return expected

    monkeypatch.setattr(torch, "load", safe_load)

    assert load_checkpoint(checkpoint) is expected
    assert observed == {
        "path": checkpoint,
        "map_location": "cpu",
        "weights_only": True,
    }
