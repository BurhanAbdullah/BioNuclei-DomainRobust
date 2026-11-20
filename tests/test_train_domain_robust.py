import pickle

import pytest
import torch

from scripts.train_domain_robust import load_initial_checkpoint, resolve_device


def test_resolve_device_auto_falls_back_to_cpu(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert resolve_device("auto").type == "cpu"


def test_resolve_device_auto_uses_cuda_when_available(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert resolve_device("auto").type == "cuda"


class _UnsafeCheckpointPayload:
    pass


def test_initial_checkpoint_loads_tensor_state_dict_safely(tmp_path):
    checkpoint_path = tmp_path / "initial.pt"
    state_dict = {"weight": torch.tensor([1.0, 2.0])}
    torch.save({"model": state_dict, "seed": 7}, checkpoint_path)


    loaded = load_initial_checkpoint(checkpoint_path)
    assert loaded["seed"] == 7
    assert torch.equal(loaded["model"]["weight"], state_dict["weight"])


def test_initial_checkpoint_rejects_unsupported_pickle_payload(tmp_path):
    checkpoint_path = tmp_path / "unsafe.pt"
    torch.save({"model": {}, "payload": _UnsafeCheckpointPayload()}, checkpoint_path)


    with pytest.raises(pickle.UnpicklingError):
        load_initial_checkpoint(checkpoint_path)


def test_initial_checkpoint_requires_model_state_dict(tmp_path):
    checkpoint_path = tmp_path / "missing-model.pt"
    torch.save({"metadata": {"seed": 7}}, checkpoint_path)


    with pytest.raises(RuntimeError, match="model state dict"):
        load_initial_checkpoint(checkpoint_path)
