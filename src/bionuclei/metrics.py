"""Segmentation metrics used by the evaluation protocol."""

from __future__ import annotations

import numpy as np


def dice_coefficient(pred: np.ndarray, target: np.ndarray, eps: float = 1e-8) -> float:
    pred_b = pred.astype(bool)
    target_b = target.astype(bool)
    intersection = np.logical_and(pred_b, target_b).sum(dtype=np.float64)
    return float((2.0 * intersection + eps) / (pred_b.sum(dtype=np.float64) + target_b.sum(dtype=np.float64) + eps))


def iou_score(pred: np.ndarray, target: np.ndarray, eps: float = 1e-8) -> float:
    pred_b = pred.astype(bool)
    target_b = target.astype(bool)
    intersection = np.logical_and(pred_b, target_b).sum(dtype=np.float64)
    union = np.logical_or(pred_b, target_b).sum(dtype=np.float64)
    return float((intersection + eps) / (union + eps))


def boundary_f1(pred_boundary: np.ndarray, target_boundary: np.ndarray, eps: float = 1e-8) -> float:
    pred_b = pred_boundary.astype(bool)
    target_b = target_boundary.astype(bool)
    tp = np.logical_and(pred_b, target_b).sum(dtype=np.float64)
    precision = (tp + eps) / (pred_b.sum(dtype=np.float64) + eps)
    recall = (tp + eps) / (target_b.sum(dtype=np.float64) + eps)
    return float(2.0 * precision * recall / (precision + recall + eps))
