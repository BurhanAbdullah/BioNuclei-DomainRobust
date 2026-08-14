#!/usr/bin/env python3
"""Verify a local BBBC039v1 acquisition without changing the data.

Checks the published dataset-level expectations against the files actually
present on disk. The script deliberately fails closed when an assumption
cannot be verified, so no experimental manifest is silently generated from
partial data.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tifffile
from skimage.io import imread

EXPECTED_IMAGES = 200
EXPECTED_SHAPE = (520, 696)
EXPECTED_DTYPE = np.dtype("uint16")
EXPECTED_SPLITS = {"train": 100, "validation": 50, "test": 50}


def files_with_suffix(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    return sorted(
        p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in suffixes
    )


def inspect_metadata(root: Path) -> dict[str, int]:
    """Count split-labelled metadata files conservatively.

    The Broad package may encode the official partitions in text/CSV files.
    We count unique filenames mentioned next to explicit split tokens rather
    than assuming a particular metadata filename.
    """
    counts = {k: 0 for k in EXPECTED_SPLITS}
    seen: dict[str, set[str]] = {k: set() for k in EXPECTED_SPLITS}
    for p in files_with_suffix(root, (".txt", ".csv", ".tsv", ".json")):
        text = p.read_text(errors="ignore")
        for split in counts:
            for line in text.splitlines():
                low = line.lower()
                if split not in low:
                    continue
                for token in line.replace(",", " ").replace("\t", " ").split():
                    token = token.strip('"\'[]{}()')
                    if token.lower().endswith((".tif", ".tiff")):
                        seen[split].add(token)
    for split in counts:
        counts[split] = len(seen[split])
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("data/raw/BBBC039"))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    root = args.data_root
    image_root = root / "images"
    mask_root = root / "masks"
    if not image_root.exists() or not mask_root.exists():
        raise SystemExit(
            "Missing extracted images/ or masks/ directory. Run download_bbbc039.py first."
        )

    images = files_with_suffix(image_root, (".tif", ".tiff"))
    masks = files_with_suffix(mask_root, (".png", ".tif", ".tiff"))
    if len(images) != EXPECTED_IMAGES:
        raise SystemExit(f"Expected {EXPECTED_IMAGES} images; found {len(images)}")
    if len(masks) != EXPECTED_IMAGES:
        raise SystemExit(f"Expected {EXPECTED_IMAGES} masks; found {len(masks)}")

    shape_counts: dict[str, int] = {}
    dtype_counts: dict[str, int] = {}
    for path in images:
        arr = tifffile.imread(path)
        shape_counts[str(tuple(arr.shape))] = shape_counts.get(str(tuple(arr.shape)), 0) + 1
        dtype_counts[str(arr.dtype)] = dtype_counts.get(str(arr.dtype), 0) + 1

    if shape_counts != {str(EXPECTED_SHAPE): EXPECTED_IMAGES}:
        raise SystemExit(f"Image shape verification failed: {shape_counts}")
    if dtype_counts != {str(EXPECTED_DTYPE): EXPECTED_IMAGES}:
        raise SystemExit(f"Image dtype verification failed: {dtype_counts}")

    split_counts = inspect_metadata(root / "metadata")
    result = {
        "dataset": "BBBC039v1",
        "images": len(images),
        "masks": len(masks),
        "image_shape": list(EXPECTED_SHAPE),
        "image_dtype": str(EXPECTED_DTYPE),
        "split_counts_detected": split_counts,
        "expected_split_counts": EXPECTED_SPLITS,
        "split_counts_verified": split_counts == EXPECTED_SPLITS,
    }
    if not result["split_counts_verified"]:
        raise SystemExit(
            "Image/mask integrity passed, but official split counts could not be "
            f"verified from metadata: {split_counts}. Inspect metadata manually before training."
        )

    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
