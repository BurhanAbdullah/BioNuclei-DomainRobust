#!/usr/bin/env python3
"""Verify a local BBBC039v1 acquisition without changing the data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tifffile

from scripts.build_bbbc039_split import discover_partition_files, parse_partition_file

EXPECTED_IMAGES = 200
EXPECTED_SHAPE = (520, 696)
EXPECTED_DTYPE = np.dtype("uint16")
EXPECTED_SPLITS = {"train": 100, "validation": 50, "test": 50}


def is_macos_metadata(path: Path) -> bool:
    return "__MACOSX" in path.parts or path.name.startswith("._")


def files_with_suffix(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    return sorted(
        p
        for p in root.rglob("*")
        if p.is_file()
        and p.suffix.lower() in suffixes
        and not is_macos_metadata(p)
    )


def inspect_metadata(root: Path) -> dict[str, int]:
    """Use the same parser as manifest generation to avoid split drift."""
    files = discover_partition_files(root)
    return {
        partition: len(parse_partition_file(path, partition))
        for partition, path in files.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("data/raw/BBBC039"))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    root = args.data_root
    image_root = root / "images"
    mask_root = root / "masks"
    metadata_root = root / "metadata"
    if not image_root.exists() or not mask_root.exists() or not metadata_root.exists():
        raise SystemExit("Missing extracted images/, masks/, or metadata/ directory.")

    images = files_with_suffix(image_root, (".tif", ".tiff"))
    masks = files_with_suffix(mask_root, (".png", ".tif", ".tiff"))
    if len(images) != EXPECTED_IMAGES:
        raise SystemExit(f"Expected {EXPECTED_IMAGES} images; found {len(images)}")
    if len(masks) != EXPECTED_IMAGES:
        raise SystemExit(f"Expected {EXPECTED_IMAGES} masks; found {len(masks)}")

    image_stems = {p.stem for p in images}
    mask_stems = {p.stem for p in masks}
    if image_stems != mask_stems:
        missing_masks = sorted(image_stems - mask_stems)
        missing_images = sorted(mask_stems - image_stems)
        raise SystemExit(
            "Image/mask integrity failed: "
            f"missing_masks={missing_masks[:10]}, missing_images={missing_images[:10]}"
        )

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

    split_counts = inspect_metadata(metadata_root)
    result = {
        "dataset": "BBBC039v1",
        "images": len(images),
        "masks": len(masks),
        "image_shape": list(EXPECTED_SHAPE),
        "image_dtype": str(EXPECTED_DTYPE),
        "image_mask_correspondence_verified": True,
        "split_counts_detected": split_counts,
        "expected_split_counts": EXPECTED_SPLITS,
        "split_counts_verified": split_counts == EXPECTED_SPLITS,
    }
    if not result["split_counts_verified"]:
        raise SystemExit(
            "Image/mask integrity passed, but official split counts were not "
            f"verified: {split_counts}. Inspect metadata manually before training."
        )

    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
