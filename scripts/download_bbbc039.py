#!/usr/bin/env python3
"""Download and extract BBBC039 from an authoritative or explicitly selected mirror.

The script never places raw data under version control. It records the source URL,
archive hash, and extracted file inventory in a local manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

PRIMARY_URL = "https://data.broadinstitute.org/bbbc/BBBC039/BBBC039_v1.zip"
MIRROR_URL = "https://zenodo.org/records/15370205/files/bbbc039.zip"


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)


def inventory(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("data/raw/BBBC039"))
    parser.add_argument("--url", default=PRIMARY_URL)
    parser.add_argument("--allow-mirror", action="store_true")
    parser.add_argument("--keep-archive", action="store_true")
    args = parser.parse_args()

    root = args.data_root
    root.mkdir(parents=True, exist_ok=True)
    archive = root / "BBBC039.zip"

    try:
        print(f"Downloading: {args.url}")
        download(args.url, archive)
        source_url = args.url
    except Exception as primary_error:
        if not args.allow_mirror:
            raise SystemExit(
                "Primary BBBC039 download failed. Re-run with --allow-mirror only "
                "after reviewing the mirror's provenance and license."
            ) from primary_error
        print(f"Primary source failed: {primary_error}")
        print(f"Trying explicitly requested mirror: {MIRROR_URL}")
        download(MIRROR_URL, archive)
        source_url = MIRROR_URL

    archive_hash = sha256(archive)
    with zipfile.ZipFile(archive) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise SystemExit(f"Corrupt ZIP member: {bad}")
        zf.extractall(root / "extracted")

    manifest = {
        "dataset": "BBBC039",
        "source_url": source_url,
        "archive_sha256": archive_hash,
        "files": inventory(root / "extracted"),
    }
    (root / "download_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    if not args.keep_archive:
        archive.unlink()

    print(f"Extracted {len(manifest['files'])} files.")
    print(f"Manifest: {root / 'download_manifest.json'}")


if __name__ == "__main__":
    main()
