import torch

from bionuclei.models import BoundaryUNet


def test_boundary_unet_output_shape():
    model = BoundaryUNet(in_channels=1, out_channels=3, base_channels=8)
    x = torch.randn(2, 1, 64, 64)
    y = model(x)
    assert y.shape == (2, 3, 64, 64)


def test_boundary_unet_backward():
    model = BoundaryUNet(in_channels=1, out_channels=3, base_channels=8)
    x = torch.randn(1, 1, 64, 64, requires_grad=True)
    y = model(x)
    loss = y.square().mean()
    loss.backward()
    assert x.grad is not None
    assert torch.isfinite(x.grad).all()
