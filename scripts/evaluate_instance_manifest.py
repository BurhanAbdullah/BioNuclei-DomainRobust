#!/usr/bin/env python3
"""Evaluate a Boundary U-Net checkpoint on a manifest-defined image/mask split."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from scipy import ndimage
from skimage.io import imread

from bionuclei.data import decode_instance_mask, read_fluorescence_image
from bionuclei.metrics import aji_score, boundary_f1, dice_coefficient, iou_score
from bionuclei.models import BoundaryUNet

IMAGE_EXTENSIONS = (".tif", ".tiff", ".png", ".jpg", ".jpeg")
MASK_EXTENSIONS = (".png", ".tif", ".tiff")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve(root: Path, image_name: str, kind: str) -> Path:
    base = root / ("images" if kind == "image" else "masks")
    target = Path(image_name).name
    exts = IMAGE_EXTENSIONS if kind == "image" else MASK_EXTENSIONS
    candidates = sorted(
        p for p in base.rglob("*")
        if p.is_file() and p.name == target and p.suffix.lower() in exts
    )
    if len(candidates) != 1:
        raise RuntimeError(f"Expected exactly one {kind} for {image_name}; found {candidates}")
    return candidates[0]


def split_instances(logits: torch.Tensor) -> np.ndarray:
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
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--split", choices=("train", "validation", "test"), default="test")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    checkpoint = torch.load(args.checkpoint, map_location="cpu")
    cfg = checkpoint["config"]
    model = BoundaryUNet(
        in_channels=int(cfg["model"]["in_channels"]),
        out_channels=int(cfg["model"]["out_channels"]),
        base_channels=int(cfg["model"]["base_channels"]),
    )
    model.load_state_dict(checkpoint["model"], strict=True)
    model.eval()

    manifest = json.loads(args.manifest.read_text())
    names = manifest["partitions"][args.split]
    records = []

    for name in names:
        image_path = resolve(args.data_root, name, "image")
        mask_path = resolve(args.data_root, name, "mask")
        image = read_fluorescence_image(image_path)
        target = decode_instance_mask(np.asarray(imread(mask_path)))
        if image.ndim != 2:
            raise ValueError(f"Expected single-channel fluorescence image for {name}; got {image.shape}")
        if image.shape != target.shape:
            raise ValueError(f"Shape mismatch for {name}: {image.shape} vs {target.shape}")
        x = image.astype(np.float32, copy=False)
        scale = np.percentile(x, 99.5)
        if not np.isfinite(scale) or scale <= 0:
            scale = 1.0
        x = np.clip(x / scale, 0.0, 1.0)
        with torch.inference_mode():
            logits = model(torch.from_numpy(x[None, None]).float())
        pred = split_instances(logits)
        records.append({
            "image": name,
            "dice": dice_coefficient(pred > 0, target > 0),
            "iou": iou_score(pred > 0, target > 0),
            "aji": aji_score(pred, target),
            "boundary_f1": boundary_f1(boundary_band(pred), boundary_band(target)),
        })

    metric_names = ("dice", "iou", "aji", "boundary_f1")
    report = {
        "split": args.split,
        "n_images": len(records),
        "checkpoint_sha256": sha256(args.checkpoint),
        "preprocessing": {
            "input": "single-channel fluorescence; fail-closed for RGB/RGBA input",
            "normalization": "99.5th percentile with lower bound 1.0, then clip to [0,1]",
            "instance_postprocessing": "8-connected components of non-background model prediction",
        },
        "tuning": "none; evaluation-only",
        "mean": {name: float(np.mean([r[name] for r in records])) for name in metric_names},
        "per_image": records,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / f"{args.split}_metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["mean"], indent=2))


if __name__ == "__main__":
    main()
