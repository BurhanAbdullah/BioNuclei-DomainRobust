#!/usr/bin/env python3
"""Instance-level precision/recall/F1 helpers used by experiment reports."""
from __future__ import annotations
import numpy as np

def instance_prf(pred: np.ndarray, target: np.ndarray, iou_threshold: float = 0.5) -> dict[str, float]:
    pred_ids=[int(x) for x in np.unique(pred) if x>0]
    true_ids=[int(x) for x in np.unique(target) if x>0]
    used=set(); tp=0
    for tid in true_ids:
        t=target==tid; best=(0.0,None)
        for pid in pred_ids:
            if pid in used: continue
            p=pred==pid; inter=np.logical_and(t,p).sum()
            if not inter: continue
            score=inter/np.logical_or(t,p).sum()
            if score>best[0]: best=(float(score),pid)
        if best[1] is not None and best[0] >= iou_threshold:
            used.add(int(best[1])); tp += 1
    fp=len(pred_ids)-tp; fn=len(true_ids)-tp
    precision=tp/(tp+fp) if tp+fp else 1.0
    recall=tp/(tp+fn) if tp+fn else 1.0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
    return {'precision':float(precision),'recall':float(recall),'f1_score':float(f1),'tp':tp,'fp':fp,'fn':fn,'iou_threshold':float(iou_threshold)}
