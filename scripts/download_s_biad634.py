#!/usr/bin/env python3
"""Download and inventory S-BIAD634 / S-BSST265 from BioStudies.

The dataset is public CC0. Raw data are never committed; this script records
source provenance and a deterministic inventory for later target-domain
experiments.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

SOURCE_URL = "https://www.ebi.ac.uk/biostudies/files/S-BSST265/dataset.zip"


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("data/raw/S-BIAD634"))
    parser.add_argument("--url", default=SOURCE_URL)
    parser.add_argument("--keep-archive", action="store_true")
    args = parser.parse_args()

    root = args.data_root
    root.mkdir(parents=True, exist_ok=True)
    archive = root / "dataset.zip"
    download(args.url, archive)
    archive_hash = sha256(archive)

    with zipfile.ZipFile(archive) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise SystemExit(f"Corrupt ZIP member: {bad}")
        zf.extractall(root / "extracted")

    files = sorted(str(p.relative_to(root / "extracted")) for p in (root / "extracted").rglob("*") if p.is_file())
    raw = [p for p in files if "/rawimages/" in f"/{p}"]
    groundtruth = [p for p in files if "/groundtruth/" in f"/{p}"]
    metadata = [p for p in files if p.lower().endswith((".txt", ".csv", ".tsv"))]

    manifest = {
        "dataset": "S-BIAD634 / S-BSST265",
        "source_url": args.url,
        "archive_sha256": archive_hash,
        "expected_public_license": "CC0",
        "files": files,
        "raw_image_files": raw,
        "groundtruth_files": groundtruth,
        "metadata_candidates": metadata,
    }
    (root / "download_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    if not args.keep_archive:
        archive.unlink()

    print(json.dumps({
        "raw_image_files": len(raw),
        "groundtruth_files": len(groundtruth),
        "metadata_candidates": metadata,
        "manifest": str(root / "download_manifest.json"),
    }, indent=2))


if __name__ == "__main__":
    main()
