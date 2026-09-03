import torch

from scripts.train_domain_robust import resolve_device


def test_resolve_device_auto_falls_back_to_cpu(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert resolve_device("auto").type == "cpu"


def test_resolve_device_auto_uses_cuda_when_available(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert resolve_device("auto").type == "cuda"
