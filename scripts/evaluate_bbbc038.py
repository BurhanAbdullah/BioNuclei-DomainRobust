#!/usr/bin/env python3
"""Evaluate a frozen BioNuclei checkpoint on BBBC038 stage-1 training images.

BBBC038 is used only as an external validation benchmark here. The script
constructs instance labels from the authoritative per-nucleus PNG masks,
fails on overlapping annotations, applies deterministic image preprocessing,
and records image-level metrics plus provenance. It performs no tuning.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import tifffile
import torch
from scipy import ndimage
from skimage.io import imread

from bionuclei.metrics import aji_score, boundary_f1, dice_coefficient, iou_score
from bionuclei.models import BoundaryUNet

IMAGE_EXTENSIONS = {".png", ".tif", ".tiff"}


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def to_grayscale(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image.astype(np.float32, copy=False)
    if image.ndim == 3 and image.shape[-1] >= 3:
        rgb = image[..., :3].astype(np.float32, copy=False)
        return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    raise ValueError(f"Unsupported BBBC038 image shape: {image.shape}")


def decode_bbbc038_instances(sample_dir: Path, shape: tuple[int, int]) -> np.ndarray:
    mask_dir = sample_dir / "masks"
    mask_paths = sorted(p for p in mask_dir.iterdir() if p.is_file() and p.suffix.lower() == ".png")
    if not mask_paths:
        raise ValueError(f"No nucleus masks found in {mask_dir}")
    labels = np.zeros(shape, dtype=np.int32)
    for instance_id, path in enumerate(mask_paths, start=1):
        mask = np.asarray(imread(path))
        if mask.ndim == 3:
            mask = mask[..., 0]
        if mask.shape != shape:
            raise ValueError(f"Mask shape mismatch for {path.name}: {mask.shape} vs {shape}")
        foreground = mask > 0
        if np.any(labels[foreground] != 0):
            raise ValueError(f"Overlapping BBBC038 nucleus masks detected in {sample_dir.name}")
        labels[foreground] = instance_id
    return labels


def predict_instances(model: BoundaryUNet, image: np.ndarray) -> np.ndarray:
    x = to_grayscale(image)
    scale = np.percentile(x, 99.5)
    x = np.clip(x / max(float(scale), 1.0), 0.0, 1.0)
    with torch.inference_mode():
        logits = model(torch.from_numpy(x[None, None]).float())
    classes = logits.argmax(dim=1).cpu().numpy()[0]
    instances, _ = ndimage.label(classes != 0, structure=np.ones((3, 3), dtype=np.uint8))
    return instances.astype(np.int32)


def boundary_band(mask: np.ndarray) -> np.ndarray:
    foreground = mask > 0
    eroded = ndimage.binary_erosion(foreground, structure=np.ones((3, 3), dtype=np.uint8))
    return foreground & ~eroded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/e7_bbbc038"))
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

    root = args.data_root
    sample_dirs = sorted(
        p for p in root.rglob("images") if p.is_dir() and (p.parent / "masks").is_dir()
    )
    if not sample_dirs:
        raise SystemExit(f"No BBBC038 image/mask sample directories found below {root}")

    records = []
    for image_dir in sample_dirs:
        image_candidates = sorted(p for p in image_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)
        if len(image_candidates) != 1:
            raise ValueError(f"Expected exactly one image in {image_dir}; found {len(image_candidates)}")
        image_path = image_candidates[0]
        image = np.asarray(imread(image_path))
        gray = to_grayscale(image)
        target = decode_bbbc038_instances(image_dir.parent, gray.shape)
        pred = predict_instances(model, image)
        records.append({
            "image_id": image_dir.parent.name,
            "image": str(image_path.relative_to(root)),
            "target_instances": int(np.unique(target[target > 0]).size),
            "predicted_instances": int(np.unique(pred[pred > 0]).size),
            "dice": dice_coefficient(pred > 0, target > 0),
            "iou": iou_score(pred > 0, target > 0),
            "aji": aji_score(pred, target),
            "boundary_f1": boundary_f1(boundary_band(pred), boundary_band(target)),
        })

    metric_names = ("dice", "iou", "aji", "boundary_f1")
    report = {
        "dataset": "BBBC038v1",
        "subset": "stage1_train",
        "role": "independent_external_validation",
        "n_images": len(records),
        "checkpoint_sha256": sha256(args.checkpoint),
        "checkpoint_seed": checkpoint.get("seed"),
        "preprocessing": {
            "color_to_grayscale": "ITU-R BT.601 luminance coefficients 0.299/0.587/0.114 for RGB inputs",
            "normalization": "99.5th percentile with lower bound 1.0, then clip to [0,1]",
            "instance_postprocessing": "8-connected components of non-background model prediction",
        },
        "tuning": "none; protocol is evaluation-only",
        "mean": {name: float(np.mean([r[name] for r in records])) for name in metric_names},
        "per_image": records,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["mean"], indent=2))


if __name__ == "__main__":
    main()
