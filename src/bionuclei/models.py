"""Baseline segmentation models used in the domain-robust study."""

from __future__ import annotations

import os
from contextlib import contextmanager

import torch
from torch import nn
from torch.utils.checkpoint import checkpoint


class DoubleConv(nn.Module):
    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


@contextmanager
def _restore_batchnorm_state(module: nn.Module):
    """Restore BN running buffers after a recomputed checkpointed forward.

    PyTorch checkpoint recomputes the forward pass during backward. BatchNorm
    updates running statistics during each training forward, so a naive
    checkpoint would update those buffers twice. We snapshot and restore all
    BatchNorm buffers around the recomputation; the tensor-valued forward and
    backward computation remains unchanged while the memory-saving path avoids
    retaining intermediate activations.
    """
    snapshots = []
    for submodule in module.modules():
        if isinstance(submodule, nn.modules.batchnorm._BatchNorm):
            snapshots.append(
                (
                    submodule,
                    None if submodule.running_mean is None else submodule.running_mean.detach().clone(),
                    None if submodule.running_var is None else submodule.running_var.detach().clone(),
                    None if submodule.num_batches_tracked is None else submodule.num_batches_tracked.detach().clone(),
                )
            )
    try:
        yield
    finally:
        for submodule, running_mean, running_var, num_batches in snapshots:
            if running_mean is not None:
                submodule.running_mean.copy_(running_mean)
            if running_var is not None:
                submodule.running_var.copy_(running_var)
            if num_batches is not None:
                submodule.num_batches_tracked.copy_(num_batches)


def _checkpointed_block(module: nn.Module, x: torch.Tensor) -> torch.Tensor:
    """Memory-saving block evaluation with BatchNorm-buffer preservation."""
    def run(inp: torch.Tensor) -> torch.Tensor:
        if torch.is_grad_enabled():
            with _restore_batchnorm_state(module):
                return module(inp)
        return module(inp)

    return checkpoint(run, x, use_reentrant=False, preserve_rng_state=True)


class BoundaryUNet(nn.Module):
    """Compact U-Net predicting background/interior/boundary classes.

    This is a baseline, not the proposed novel architecture. Instance separation
    is delegated to post-processing of the boundary-aware semantic prediction.
    """

    def __init__(self, in_channels: int = 1, out_channels: int = 3, base_channels: int = 32) -> None:
        super().__init__()
        b = base_channels
        self.enc1 = DoubleConv(in_channels, b)
        self.enc2 = DoubleConv(b, b * 2)
        self.enc3 = DoubleConv(b * 2, b * 4)
        self.bottleneck = DoubleConv(b * 4, b * 8)
        self.pool = nn.MaxPool2d(2)

        self.up3 = nn.ConvTranspose2d(b * 8, b * 4, 2, stride=2)
        self.dec3 = DoubleConv(b * 8, b * 4)
        self.up2 = nn.ConvTranspose2d(b * 4, b * 2, 2, stride=2)
        self.dec2 = DoubleConv(b * 4, b * 2)
        self.up1 = nn.ConvTranspose2d(b * 2, b, 2, stride=2)
        self.dec1 = DoubleConv(b * 2, b)
        self.head = nn.Conv2d(b, out_channels, 1)

    def _block(self, block: nn.Module, x: torch.Tensor) -> torch.Tensor:
        if self.training and os.environ.get("BIONUCLEI_ACTIVATION_CHECKPOINT") == "1":
            return _checkpointed_block(block, x)
        return block(x)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e1 = self._block(self.enc1, x)
        e2 = self._block(self.enc2, self.pool(e1))
        e3 = self._block(self.enc3, self.pool(e2))
        z = self._block(self.bottleneck, self.pool(e3))

        d3 = self.up3(z)
        d3 = torch.cat((d3, e3), dim=1)
        d3 = self._block(self.dec3, d3)
        d2 = self.up2(d3)
        d2 = torch.cat((d2, e2), dim=1)
        d2 = self._block(self.dec2, d2)
        d1 = self.up1(d2)
        d1 = torch.cat((d1, e1), dim=1)
        d1 = self._block(self.dec1, d1)
        return self.head(d1)
