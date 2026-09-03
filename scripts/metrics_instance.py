#!/usr/bin/env python3
"""Instance-level metrics used by experiment reports."""
from __future__ import annotations

import numpy as np


def _validate_masks(pred: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    pred = np.asarray(pred)
    target = np.asarray(target)
    if pred.shape != target.shape:
        raise ValueError(f"Shape mismatch: pred {pred.shape} vs target {target.shape}")
    if pred.ndim != 2 or target.ndim != 2:
        raise ValueError(f"Expected 2-D instance masks; got pred {pred.shape}, target {target.shape}")
    return pred, target


def _instance_ids(mask: np.ndarray) -> list[int]:
    return [int(x) for x in np.unique(mask) if x > 0]


def _match_instances(pred: np.ndarray, target: np.ndarray, iou_threshold: float = 0.5) -> tuple[int, int, int]:
    """Greedily match instances at a fixed IoU threshold, deterministically."""
    if not 0.0 <= iou_threshold <= 1.0:
        raise ValueError("iou_threshold must be between 0 and 1")
    pred_ids = _instance_ids(pred)
    true_ids = _instance_ids(target)
    used: set[int] = set()
    tp = 0
    for tid in true_ids:
        true_mask = target == tid
        best_iou = 0.0
        best_pid: int | None = None
        for pid in pred_ids:
            if pid in used:
                continue
            pred_mask = pred == pid
            inter = np.logical_and(true_mask, pred_mask).sum(dtype=np.float64)
            if inter == 0:
                continue
            union = np.logical_or(true_mask, pred_mask).sum(dtype=np.float64)
            iou = float(inter / union)
            if iou > best_iou or (iou == best_iou and best_pid is not None and pid < best_pid):
                best_iou = iou
                best_pid = pid
        if best_pid is not None and best_iou >= iou_threshold:
            used.add(best_pid)
            tp += 1
    fp = len(pred_ids) - tp
    fn = len(true_ids) - tp
    return tp, fp, fn


def instance_prf(pred: np.ndarray, target: np.ndarray, iou_threshold: float = 0.5) -> dict[str, float]:
    pred, target = _validate_masks(pred, target)
    tp, fp, fn = _match_instances(pred, target, iou_threshold)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "iou_threshold": float(iou_threshold),
    }


def aji_score(pred: np.ndarray, target: np.ndarray) -> float:
    """Compute Aggregated Jaccard Index for integer instance masks.

    Each ground-truth instance is matched to the highest-IoU unused prediction.
    Unmatched ground-truth and predicted instances contribute their full area
    to the denominator. Label values are arbitrary positive integers.
    """
    pred, target = _validate_masks(pred, target)
    pred_ids = _instance_ids(pred)
    true_ids = _instance_ids(target)
    if not true_ids and not pred_ids:
        return 1.0
    if not true_ids or not pred_ids:
        return 0.0

    used_pred: set[int] = set()
    intersection_sum = 0.0
    union_sum = 0.0
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
            if iou > best_iou or (iou == best_iou and best_pid is not None and pid < best_pid):
                best_iou = iou
                best_pid = pid
        if best_pid is None:
            union_sum += float(true_mask.sum(dtype=np.float64))
        else:
            used_pred.add(best_pid)
            pred_mask = pred == best_pid
            intersection_sum += float(np.logical_and(true_mask, pred_mask).sum(dtype=np.float64))
            union_sum += float(np.logical_or(true_mask, pred_mask).sum(dtype=np.float64))

    for pid in pred_ids:
        if pid not in used_pred:
            union_sum += float((pred == pid).sum(dtype=np.float64))
    return float(intersection_sum / union_sum) if union_sum else 1.0
