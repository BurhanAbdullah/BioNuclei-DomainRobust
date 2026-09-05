#!/usr/bin/env python3
"""Acquire and inventory the authoritative BBBC038 stage-1 benchmark.

Raw data are never committed. The manifest records the Broad download URL,
archive SHA-256, extracted file inventory, and deterministic image IDs for
later independent external validation. It does not infer biological strata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

SOURCE_URL = "https://data.broadinstitute.org/bbbc/BBBC038/stage1_train.zip"


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=300) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)


def image_id_from_path(path: str, directory: str) -> str:
    parts = Path(path).parts
    try:
        index = parts.index(directory)
    except ValueError as exc:
        raise ValueError(f"Path does not contain /{directory}/: {path}") from exc
    if index == 0:
        raise ValueError(f"Cannot infer image ID from path: {path}")
    return parts[index - 1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("data/raw/BBBC038"))
    parser.add_argument("--url", default=SOURCE_URL)
    parser.add_argument("--keep-archive", action="store_true")
    args = parser.parse_args()

    root = args.data_root
    root.mkdir(parents=True, exist_ok=True)
    archive = root / "stage1_train.zip"
    download(args.url, archive)
    archive_hash = sha256(archive)

    with zipfile.ZipFile(archive) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise SystemExit(f"Corrupt ZIP member: {bad}")
        zf.extractall(root / "extracted")

    files = sorted(
        str(p.relative_to(root / "extracted"))
        for p in (root / "extracted").rglob("*")
        if p.is_file()
    )
    image_files = [
        p for p in files
        if "/images/" in f"/{p}" and p.lower().endswith((".png", ".tif", ".tiff"))
    ]
    mask_files = [
        p for p in files
        if "/masks/" in f"/{p}" and p.lower().endswith(".png")
    ]

    image_ids = sorted({image_id_from_path(p, "images") for p in image_files})
    mask_image_ids = sorted({image_id_from_path(p, "masks") for p in mask_files})
    if not image_ids:
        raise SystemExit("No stage1 image files found in the extracted archive")
    missing_mask_dirs = sorted(set(image_ids) - set(mask_image_ids))

    manifest = {
        "dataset": "BBBC038v1",
        "subset": "stage1_train",
        "role": "independent_external_validation",
        "source_url": args.url,
        "archive_sha256": archive_hash,
        "expected_public_license": "CC0",
        "image_count": len(image_ids),
        "mask_count": len(mask_files),
        "image_ids": image_ids,
        "mask_image_ids": mask_image_ids,
        "image_ids_without_masks": missing_mask_dirs,
        "files": files,
    }
    (root / "download_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    if not args.keep_archive:
        archive.unlink()

    print(json.dumps({
        "dataset": manifest["dataset"],
        "subset": manifest["subset"],
        "image_count": manifest["image_count"],
        "mask_count": manifest["mask_count"],
        "image_ids_without_masks": len(missing_mask_dirs),
        "archive_sha256": archive_hash,
        "manifest": str(root / "download_manifest.json"),
    }, indent=2))


if __name__ == "__main__":
    main()
