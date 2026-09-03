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


def aji_score(pred: np.ndarray, target: np.ndarray) -> float:
    """Compute the Aggregated Jaccard Index for integer instance masks.

    Each foreground ground-truth instance is matched to at most one predicted
    instance, using its highest-overlap unmatched prediction. Unmatched
    ground-truth and predicted instances contribute their full area to the
    denominator. Background is label 0 and is ignored.

    The implementation is deliberately independent of label values and works
    with non-contiguous integer instance IDs.
    """
    pred = np.asarray(pred)
    target = np.asarray(target)
    if pred.shape != target.shape:
        raise ValueError(f"Shape mismatch: pred {pred.shape} vs target {target.shape}")

    pred_ids = [int(x) for x in np.unique(pred) if x > 0]
    true_ids = [int(x) for x in np.unique(target) if x > 0]
    if not true_ids and not pred_ids:
        return 1.0
    if not true_ids or not pred_ids:
        return 0.0

    used_pred: set[int] = set()
    intersection_sum = 0.0
    union_sum = 0.0

    # Match each true instance to the highest-IoU unused prediction.
    # Iterating over true IDs is deterministic; ties are resolved by the
    # sorted prediction IDs returned by np.unique.
    for tid in true_ids:
        true_mask = target == tid
        best_iou = 0.0
        best_pid: int | None = None
        for pid in pred_ids:
            if pid in used_pred:
                continue
            pred_mask = pred == pid
            intersection = np.logical_and(true_mask, pred_mask).sum(dtype=np.float64)
            if intersection == 0:
                continue
            union = np.logical_or(true_mask, pred_mask).sum(dtype=np.float64)
            iou = float(intersection / union)
            if iou > best_iou:
                best_iou = iou
                best_pid = pid

        if best_pid is None:
            union_sum += float(true_mask.sum(dtype=np.float64))
            continue

        used_pred.add(best_pid)
        pred_mask = pred == best_pid
        intersection_sum += float(np.logical_and(true_mask, pred_mask).sum(dtype=np.float64))
        union_sum += float(np.logical_or(true_mask, pred_mask).sum(dtype=np.float64))

    for pid in pred_ids:
        if pid not in used_pred:
            union_sum += float((pred == pid).sum(dtype=np.float64))

    return float(intersection_sum / union_sum) if union_sum else 1.0


def boundary_f1(pred_boundary: np.ndarray, target_boundary: np.ndarray, eps: float = 1e-8) -> float:
    pred_b = pred_boundary.astype(bool)
    target_b = target_boundary.astype(bool)
    tp = np.logical_and(pred_b, target_b).sum(dtype=np.float64)
    precision = (tp + eps) / (pred_b.sum(dtype=np.float64) + eps)
    recall = (tp + eps) / (target_b.sum(dtype=np.float64) + eps)
    return float(2.0 * precision * recall / (precision + recall + eps))
