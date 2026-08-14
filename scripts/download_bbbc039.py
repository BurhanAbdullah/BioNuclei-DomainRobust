#!/usr/bin/env python3
"""Download and extract BBBC039 from a user-selected source.

The Broad Bioimage Benchmark Collection page is the authoritative dataset
reference. A Zenodo copy is supported explicitly as a provenance-preserving
mirror. Raw data are never committed to this repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

OFFICIAL_PAGE = "https://bbbc.broadinstitute.org/BBBC039"
ZENODO_URL = "https://zenodo.org/records/15370205/files/bbbc039.zip"
ZENODO_MD5 = "5af00c79c54b7ece852f030e26bed536"


def digest(path: Path, algorithm: str = "sha256", chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.new(algorithm)
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
    parser.add_argument("--url", required=True, help="Exact archive URL to download")
    parser.add_argument("--expected-md5", default=None)
    parser.add_argument("--keep-archive", action="store_true")
    args = parser.parse_args()

    root = args.data_root
    root.mkdir(parents=True, exist_ok=True)
    archive = root / "BBBC039.zip"

    print(f"Authoritative dataset reference: {OFFICIAL_PAGE}")
    print(f"Downloading: {args.url}")
    download(args.url, archive)

    sha256 = digest(archive, "sha256")
    md5 = digest(archive, "md5")
    if args.expected_md5 and md5.lower() != args.expected_md5.lower():
        archive.unlink(missing_ok=True)
        raise SystemExit(f"MD5 mismatch: expected {args.expected_md5}, got {md5}")

    extracted = root / "extracted"
    extracted.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise SystemExit(f"Corrupt ZIP member: {bad}")
        zf.extractall(extracted)

    files = inventory(extracted)
    manifest = {
        "dataset": "BBBC039",
        "authoritative_reference": OFFICIAL_PAGE,
        "source_url": args.url,
        "archive_sha256": sha256,
        "archive_md5": md5,
        "expected_md5": args.expected_md5,
        "file_count": len(files),
        "files": files,
    }
    (root / "download_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    if not args.keep_archive:
        archive.unlink()

    print(f"Extracted {len(files)} files.")
    print(f"Manifest: {root / 'download_manifest.json'}")


if __name__ == "__main__":
    main()
