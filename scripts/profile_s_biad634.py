#!/usr/bin/env python3
"""Profile S-BIAD634 image/annotation properties for domain-shift analysis."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tifffile
from skimage.measure import regionprops

from bionuclei.data import decode_instance_mask


def index_files(root: Path, folder: str) -> dict[str, Path]:
    """Find TIFFs recursively under any directory named ``folder``."""
    files: dict[str, Path] = {}
    for base in root.rglob(folder):
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".tif", ".tiff"}:
                stem = path.stem
                if stem in files and files[stem] != path:
                    raise RuntimeError(f"Duplicate {folder} stem {stem}: {files[stem]} and {path}")
                files[stem] = path
    return files


def stats(image: np.ndarray, mask: np.ndarray) -> dict[str, object]:
    image = np.asarray(image)
    raw_mask = np.asarray(mask)
    if image.ndim > 2:
        image = np.squeeze(image)
    if image.ndim != 2:
        raise ValueError(f"Expected 2D image, got image={image.shape}")

    # Use the same instance-mask decoder as evaluation. Treating an instance
    # mask as a binary foreground mask would merge touching nuclei and corrupt
    # object-count/area statistics used for E3 diagnosis.
    decoded_mask = decode_instance_mask(raw_mask)
    if decoded_mask.ndim != 2 or image.shape != decoded_mask.shape:
        raise ValueError(
            f"Image/mask shape mismatch: image={image.shape}, mask={decoded_mask.shape}"
        )

    labels = decoded_mask.astype(np.int64, copy=False)
    props = regionprops(labels)
    areas = np.asarray([p.area for p in props], dtype=np.float64)
    values = image.astype(np.float64, copy=False)
    return {
        "shape": list(image.shape),
        "dtype": str(image.dtype),
        "mask_dtype": str(raw_mask.dtype),
        "mask_shape": list(raw_mask.shape),
        "mask_encoding": "instance_labels_or_rgb_colors_decoded_by_bionuclei.data.decode_instance_mask",
        "min": float(values.min()),
        "max": float(values.max()),
        "mean": float(values.mean()),
        "std": float(values.std()),
        "p01": float(np.percentile(values, 1)),
        "p50": float(np.percentile(values, 50)),
        "p99": float(np.percentile(values, 99)),
        "nonzero_fraction": float(np.mean(values > 0)),
        "annotation_objects": int(len(props)),
        "annotation_foreground_fraction": float(np.mean(labels > 0)),
        "annotation_area_median": float(np.median(areas)) if areas.size else 0.0,
        "annotation_area_mean": float(areas.mean()) if areas.size else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("data/raw/S-BIAD634"))
    parser.add_argument("--output", type=Path, default=Path("outputs/s_biad634_domain_profile.json"))
    args = parser.parse_args()

    raw = index_files(args.data_root, "rawimages")
    gt = index_files(args.data_root, "groundtruth")
    common = sorted(set(raw) & set(gt))
    if not common:
        raise SystemExit(f"No raw/groundtruth TIFF pairs found under {args.data_root}")

    records = []
    for stem in common:
        records.append({"stem": stem, **stats(tifffile.imread(raw[stem]), tifffile.imread(gt[stem]))})

    def summary(key: str) -> dict[str, float]:
        values = np.asarray([r[key] for r in records], dtype=np.float64)
        return {
            "mean": float(values.mean()),
            "std": float(values.std(ddof=1)) if values.size > 1 else 0.0,
            "min": float(values.min()),
            "max": float(values.max()),
            "p10": float(np.percentile(values, 10)),
            "p50": float(np.percentile(values, 50)),
            "p90": float(np.percentile(values, 90)),
        }

    report = {
        "dataset": "S-BIAD634 / S-BSST265",
        "raw_groundtruth_pairs": len(records),
        "per_image": records,
        "summary": {key: summary(key) for key in [
            "annotation_objects", "annotation_foreground_fraction", "annotation_area_median",
            "mean", "std", "p01", "p99"
        ]},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"pairs": len(records), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
