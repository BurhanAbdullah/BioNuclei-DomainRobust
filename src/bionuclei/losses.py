"""Losses for the three-class boundary-aware segmentation baseline."""

from __future__ import annotations

import torch
from torch import nn


def soft_dice_loss(logits: torch.Tensor, target: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    """Multiclass soft Dice loss averaged over non-empty classes."""
    if logits.ndim != 4 or target.ndim != 3:
        raise ValueError("Expected logits [N,C,H,W] and target [N,H,W]")
    probs = torch.softmax(logits, dim=1)
    num_classes = probs.shape[1]
    one_hot = torch.nn.functional.one_hot(target.long(), num_classes=num_classes)
    one_hot = one_hot.permute(0, 3, 1, 2).to(probs.dtype)
    dims = (0, 2, 3)
    intersection = (probs * one_hot).sum(dims)
    denom = probs.sum(dims) + one_hot.sum(dims)
    present = one_hot.sum(dims) > 0
    dice = (2.0 * intersection + eps) / (denom + eps)
    if present.any():
        dice = dice[present]
    return 1.0 - dice.mean()


class BoundaryAwareLoss(nn.Module):
    """Cross-entropy with extra boundary emphasis plus soft Dice."""

    def __init__(self, boundary_weight: float = 2.0, dice_weight: float = 1.0) -> None:
        super().__init__()
        if boundary_weight < 0 or dice_weight < 0:
            raise ValueError("loss weights must be non-negative")
        weights = torch.tensor([1.0, 1.0, boundary_weight], dtype=torch.float32)
        self.register_buffer("class_weights", weights)
        self.dice_weight = float(dice_weight)

    def forward(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        ce = torch.nn.functional.cross_entropy(logits, target.long(), weight=self.class_weights)
        return ce + self.dice_weight * soft_dice_loss(logits, target)
