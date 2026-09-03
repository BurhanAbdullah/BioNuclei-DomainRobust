#!/usr/bin/env python3
"""Evaluate a trained boundary-aware U-Net on a verified BBBC039 partition."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from scipy import ndimage
import tifffile
from skimage.io import imread

from bionuclei.data import decode_instance_mask
from bionuclei.metrics import aji_score, boundary_f1, dice_coefficient, iou_score
from bionuclei.models import BoundaryUNet

IMAGE_EXTENSIONS = (".tif", ".tiff", ".png", ".jpg", ".jpeg")


def split_instances(logits: torch.Tensor) -> np.ndarray:
    classes = logits.argmax(dim=1).cpu().numpy()[0]
    foreground = classes != 0
    instances, _ = ndimage.label(foreground, structure=np.ones((3, 3), dtype=np.uint8))
    return instances.astype(np.int32)


def boundary_band(mask: np.ndarray) -> np.ndarray:
    foreground = mask > 0
    eroded = ndimage.binary_erosion(foreground, structure=np.ones((3, 3), dtype=np.uint8))
    return foreground & ~eroded


def resolve_image_path(root: Path, image_name: str) -> Path:
    """Resolve a metadata filename anywhere under the downloaded image archive."""
    exact = root / "images" / image_name
    if exact.exists():
        return exact
    stem = Path(image_name).stem
    candidates = sorted(
        p for p in (root / "images").rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS and p.stem == stem
    )
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise FileNotFoundError(f"No downloaded image matches manifest entry {image_name}")
    raise RuntimeError(f"Ambiguous downloaded image matches for {image_name}: {candidates}")


def mask_path(root: Path, image_name: str) -> Path:
    """Resolve a mask anywhere under the downloaded mask archive."""
    stem = Path(image_name).stem
    candidates = sorted(
        p for p in (root / "masks").rglob("*")
        if p.is_file() and p.suffix.lower() in (".png", ".tif", ".tiff") and p.stem == stem
    )
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise FileNotFoundError(f"No mask found for {image_name}")
    raise RuntimeError(f"Ambiguous masks found for {image_name}: {candidates}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--split", choices=("train", "validation", "test"), default="test")
    parser.add_argument("--output", type=Path, default=Path("outputs/bbbc039_eval"))
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

    manifest = json.loads(args.manifest.read_text())
    names = manifest["partitions"][args.split]
    results = []
    for name in names:
        image = np.asarray(tifffile.imread(resolve_image_path(args.data_root, name)))
        target = decode_instance_mask(np.asarray(imread(mask_path(args.data_root, name))))
        if image.shape != target.shape:
            raise ValueError(f"Shape mismatch for {name}: {image.shape} vs {target.shape}")
        x = image.astype(np.float32)
        scale = np.percentile(x, 99.5)
        x = np.clip(x / max(float(scale), 1.0), 0.0, 1.0)
        with torch.no_grad():
            logits = model(torch.from_numpy(x[None, None]).float())
        pred = split_instances(logits)
        results.append({
            "image": name,
            "dice": dice_coefficient(pred > 0, target > 0),
            "iou": iou_score(pred > 0, target > 0),
            "aji": aji_score(pred, target),
            "boundary_f1": boundary_f1(boundary_band(pred), boundary_band(target)),
        })

    summary = {
        "split": args.split,
        "n_images": len(results),
        "mean": {k: float(np.mean([r[k] for r in results])) for k in ("dice", "iou", "aji", "boundary_f1")},
        "per_image": results,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / f"{args.split}_metrics.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["mean"], indent=2))


if __name__ == "__main__":
    main()
