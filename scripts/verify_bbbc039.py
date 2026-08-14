#!/usr/bin/env python3
"""Verify a local BBBC039v1 acquisition without changing the data."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import tifffile

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


def normalize_image_name(value: str) -> str | None:
    value = value.strip().strip('"').strip("'")
    if not value:
        return None
    token = Path(value).name
    if token.lower().endswith((".tif", ".tiff")) and not token.startswith("._"):
        return token
    return None


def partition_key(path: Path) -> str | None:
    stem = re.sub(r"[^a-z0-9]+", "_", path.stem.lower()).strip("_")
    if "validation" in stem:
        return "validation"
    if "training" in stem or stem == "train" or "_train_" in f"_{stem}_":
        return "train"
    if "test" in stem:
        return "test"
    return None


def inspect_metadata(root: Path) -> dict[str, int]:
    """Read the official partition files and count unique image names."""
    seen: dict[str, set[str]] = {k: set() for k in EXPECTED_SPLITS}
    partition_files: dict[str, Path] = {}
    for path in files_with_suffix(root, (".txt", ".csv", ".tsv", ".json")):
        key = partition_key(path)
        if key and key not in partition_files:
            partition_files[key] = path

    missing = [k for k in EXPECTED_SPLITS if k not in partition_files]
    if missing:
        raise SystemExit(
            "Official BBBC039 partition metadata not found for: " + ", ".join(missing)
        )

    for split, path in partition_files.items():
        for line in path.read_text(errors="replace").splitlines():
            name = normalize_image_name(line)
            if name:
                seen[split].add(name)

    counts = {split: len(names) for split, names in seen.items()}
    return counts


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
