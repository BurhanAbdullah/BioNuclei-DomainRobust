"""Build the website showcase from a real BBBC039 held-out test image.

The released checkpoint and the Lab's seeded decoder run on every image in the
official test split. The image whose AJI is closest to the split median is used
for the showcase, so the website shows a typical result, not the best one.

Outputs (in --output):
  sample_bbbc039.tif        original 16-bit image (BBBC039 is CC0) for "Try a sample"
  showcase_raw.png          contrast-stretched input
  showcase_prediction.png   BioNuclei outlines on the input
  showcase_truth.png        expert ground-truth outlines on the input
  showcase.json             per-image scores, split means, provenance
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import statistics
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from scipy import ndimage
from skimage.io import imread

from bionuclei.data import decode_instance_mask, read_fluorescence_image
from bionuclei.decode import PRODUCT_DECODER, SEED_H, decode_instances
from bionuclei.metrics import aji_score, dice_coefficient
from bionuclei.models import BoundaryUNet

from evaluate_bbbc039 import mask_path, resolve_image_path

WINE = (196, 32, 92)
TEAL = (46, 196, 182)


def stretch(image: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(image, [1, 99.7])
    return np.clip((image.astype(np.float32) - lo) / max(hi - lo, 1.0), 0, 1)


def outline(labels: np.ndarray) -> np.ndarray:
    grown = ndimage.grey_dilation(labels, size=3)
    shrunk = ndimage.grey_erosion(labels, size=3)
    return (grown != shrunk) & (grown > 0)


def to_png(gray: np.ndarray, edges: np.ndarray | None, color: tuple[int, int, int], path: Path) -> None:
    rgb = np.stack([gray * 0.55, gray * 0.78, gray], axis=-1)
    if edges is not None:
        rgb[edges] = np.array(color) / 255.0
    Image.fromarray((rgb * 255).astype(np.uint8)).save(path, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
    cfg = checkpoint["config"]["model"]
    model = BoundaryUNet(in_channels=int(cfg["in_channels"]), out_channels=int(cfg["out_channels"]),
                         base_channels=int(cfg["base_channels"]))
    model.load_state_dict(checkpoint["model"])
    model.eval()

    names = json.loads(args.manifest.read_text())["partitions"]["test"]
    rows, cache = [], {}
    for name in names:
        image = read_fluorescence_image(resolve_image_path(args.data_root, name))
        truth = decode_instance_mask(np.asarray(imread(mask_path(args.data_root, name))))
        x = image.astype(np.float32)
        x = np.clip(x / max(float(np.percentile(x, 99.5)), 1.0), 0.0, 1.0)
        with torch.no_grad():
            classes = model(torch.from_numpy(x[None, None]).float()).argmax(dim=1).numpy()[0]
        pred = decode_instances(classes, PRODUCT_DECODER)
        row = {"image": name, "dice": float(dice_coefficient(pred > 0, truth > 0)), "aji": float(aji_score(pred, truth)),
               "n_pred": int(pred.max()), "n_true": int(len(np.unique(truth)) - 1)}
        rows.append(row)
        cache[name] = (image, truth, pred)

    median_aji = statistics.median(r["aji"] for r in rows)
    chosen = min(rows, key=lambda r: (abs(r["aji"] - median_aji), r["image"]))
    image, truth, pred = cache[chosen["image"]]

    args.output.mkdir(parents=True, exist_ok=True)
    gray = stretch(image)
    to_png(gray, None, WINE, args.output / "showcase_raw.png")
    to_png(gray, outline(pred), WINE, args.output / "showcase_prediction.png")
    to_png(gray, outline(truth), TEAL, args.output / "showcase_truth.png")
    source = resolve_image_path(args.data_root, chosen["image"])
    sample = args.output / "sample_bbbc039.tif"
    shutil.copyfile(source, sample)

    summary = {
        "dataset": "BBBC039 v1 (Broad Bioimage Benchmark Collection), official held-out test split",
        "dataset_license": "CC0 1.0",
        "dataset_url": "https://bbbc.broadinstitute.org/BBBC039",
        "selection": "test image whose AJI is closest to the split median (typical, not best)",
        "decoder": PRODUCT_DECODER,
        "seed_h": SEED_H,
        "checkpoint_sha256": hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
        "sample_sha256": hashlib.sha256(sample.read_bytes()).hexdigest(),
        "image": chosen,
        "split": {
            "n_images": len(rows),
            "mean_dice": statistics.mean(r["dice"] for r in rows),
            "mean_aji": statistics.mean(r["aji"] for r in rows),
            "median_aji": median_aji,
            "mean_abs_count_error": statistics.mean(abs(r["n_pred"] - r["n_true"]) for r in rows),
        },
    }
    (args.output / "showcase.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
