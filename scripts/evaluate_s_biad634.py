#!/usr/bin/env python3
"""Zero-shot evaluation of a BBBC039-trained model on S-BIAD634."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tifffile
import torch
from scipy import ndimage
from skimage.io import imread

from bionuclei.data import decode_instance_mask
from bionuclei.metrics import boundary_f1, dice_coefficient, iou_score
from bionuclei.models import BoundaryUNet


def aji_score(pred: np.ndarray, target: np.ndarray) -> float:
    pred_ids = [x for x in np.unique(pred) if x > 0]
    true_ids = [x for x in np.unique(target) if x > 0]
    if not true_ids and not pred_ids:
        return 1.0
    if not true_ids or not pred_ids:
        return 0.0
    used: set[int] = set()
    inter_sum = 0.0
    union_sum = 0.0
    for tid in true_ids:
        t = target == tid
        best = (0.0, None)
        for pid in pred_ids:
            if pid in used:
                continue
            p = pred == pid
            inter = np.logical_and(t, p).sum()
            if inter == 0:
                continue
            union = np.logical_or(t, p).sum()
            score = inter / union
            if score > best[0]:
                best = (score, pid)
        if best[1] is None:
            union_sum += t.sum()
        else:
            pid = int(best[1])
            used.add(pid)
            p = pred == pid
            inter_sum += np.logical_and(t, p).sum()
            union_sum += np.logical_or(t, p).sum()
    for pid in pred_ids:
        if pid not in used:
            union_sum += (pred == pid).sum()
    return float(inter_sum / union_sum) if union_sum else 1.0


def boundary_band(mask: np.ndarray) -> np.ndarray:
    fg = mask > 0
    eroded = ndimage.binary_erosion(fg, structure=np.ones((3, 3), dtype=np.uint8))
    return fg & ~eroded


def discover(root: Path, keywords: tuple[str, ...], suffixes: tuple[str, ...]) -> list[Path]:
    return sorted(
        p for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in suffixes and any(k in p.as_posix().lower() for k in keywords)
    )


def pair_files(root: Path) -> list[tuple[Path, Path]]:
    images = discover(root, ("rawimages",), (".tif", ".tiff", ".png"))
    masks = discover(root, ("groundtruth",), (".tif", ".tiff", ".png"))
    by_stem = {p.stem: p for p in masks}
    pairs = []
    for image in images:
        mask = by_stem.get(image.stem)
        if mask is not None:
            pairs.append((image, mask))
    if len(pairs) != len(images) or len(pairs) != len(masks):
        raise RuntimeError(f"Could not pair all target files: images={len(images)}, masks={len(masks)}, pairs={len(pairs)}")
    if not pairs:
        raise RuntimeError(f"No S-BIAD634 image/mask pairs found under {root}")
    return pairs


def load_mask(path: Path) -> np.ndarray:
    return decode_instance_mask(np.asarray(imread(path)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/s_biad634_zero_shot"))
    args = parser.parse_args()

    checkpoint = torch.load(args.checkpoint, map_location="cpu")
    cfg = checkpoint["config"]
    model = BoundaryUNet(
        in_channels=int(cfg["model"]["in_channels"]),
        out_channels=int(cfg["model"]["out_channels"]),
        base_channels=int(cfg["model"]["base_channels"]),
    )
    model.load_state_dict(checkpoint["model"])
    model.eval()

    results = []
    for image_path, mask_path in pair_files(args.data_root):
        image = np.asarray(tifffile.imread(image_path))
        target = load_mask(mask_path)
        if image.shape != target.shape:
            raise ValueError(f"Shape mismatch: {image_path.name}: {image.shape} vs {target.shape}")
        x = image.astype(np.float32)
        scale = np.percentile(x, 99.5)
        x = np.clip(x / max(float(scale), 1.0), 0.0, 1.0)
        with torch.no_grad():
            logits = model(torch.from_numpy(x[None, None]).float())
        classes = logits.argmax(dim=1).cpu().numpy()[0]
        pred, _ = ndimage.label(classes != 0, structure=np.ones((3, 3), dtype=np.uint8))
        pred = pred.astype(np.int32)
        results.append({
            "image": image_path.name,
            "dice": dice_coefficient(pred > 0, target > 0),
            "iou": iou_score(pred > 0, target > 0),
            "aji": aji_score(pred, target),
            "boundary_f1": boundary_f1(boundary_band(pred), boundary_band(target)),
            "height": int(image.shape[0]),
            "width": int(image.shape[1]),
            "n_target_instances": int(np.max(target)),
            "n_pred_instances": int(np.max(pred)),
        })

    metric_names = ("dice", "iou", "aji", "boundary_f1")
    summary = {
        "experiment": "zero_shot_bbbc039_to_s_biad634",
        "n_images": len(results),
        "mean": {m: float(np.mean([r[m] for r in results])) for m in metric_names},
        "median": {m: float(np.median([r[m] for r in results])) for m in metric_names},
        "per_image": results,
        "checkpoint_seed": checkpoint.get("seed"),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "metrics.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["mean"], indent=2))


if __name__ == "__main__":
    main()
