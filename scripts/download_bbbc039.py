#!/usr/bin/env python3
"""Download and verify the three official BBBC039v1 archives.

The Broad Bioimage Benchmark Collection page is the authoritative dataset
reference. Images, masks, and the official split metadata are distributed as
separate archives. Raw data are never committed to this repository.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

OFFICIAL_PAGE = "https://bbbc.broadinstitute.org/BBBC039"
BASE_URL = "https://data.broadinstitute.org/bbbc/BBBC039"
ARCHIVES = {
    "images": f"{BASE_URL}/images.zip",
    "masks": f"{BASE_URL}/masks.zip",
    "metadata": f"{BASE_URL}/metadata.zip",
}


def digest(path: Path, algorithm: str = "sha256", chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, destination: Path) -> dict[str, str | int | None]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)
        content_length = response.headers.get("Content-Length")
        return {
            "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
            "content_length_bytes": int(content_length) if content_length else None,
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
        }


def inventory(root: Path) -> list[str]:
    return sorted(
        str(p.relative_to(root))
        for p in root.rglob("*")
        if p.is_file() and not is_macos_metadata(p)
    )


def is_macos_metadata(path: Path) -> bool:
    """Return True for AppleDouble/resource-fork files shipped in some ZIPs."""
    return "__MACOSX" in path.parts or path.name.startswith("._")


def extract_archive(zf: zipfile.ZipFile, destination: Path) -> int:
    """Extract only real dataset members, excluding macOS sidecar metadata."""
    extracted = 0
    for member in zf.infolist():
        member_path = Path(member.filename)
        if is_macos_metadata(member_path):
            continue
        zf.extract(member, destination)
        if not member.is_dir():
            extracted += 1
    return extracted


def download_archive(name: str, url: str, root: Path, keep: bool) -> dict:
    archive = root / f"{name}.zip"
    extracted = root / name
    extracted.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {name}: {url}")
    transfer = download(url, archive)
    record = {
        "url": url,
        "sha256": digest(archive, "sha256"),
        "md5": digest(archive, "md5"),
        **transfer,
    }

    with zipfile.ZipFile(archive) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise SystemExit(f"Corrupt ZIP member in {name}: {bad}")
        extracted_count = extract_archive(zf, extracted)

    record["file_count"] = extracted_count
    if not keep:
        archive.unlink()
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("data/raw/BBBC039"))
    parser.add_argument("--keep-archives", action="store_true")
    args = parser.parse_args()

    root = args.data_root
    root.mkdir(parents=True, exist_ok=True)

    manifest = {
        "dataset": "BBBC039v1",
        "release": "v1",
        "authoritative_reference": OFFICIAL_PAGE,
        "base_url": BASE_URL,
        "archives": {},
        "extraction_policy": "exclude __MACOSX and AppleDouble (._*) sidecar files",
    }
    for name, url in ARCHIVES.items():
        manifest["archives"][name] = download_archive(
            name, url, root, args.keep_archives
        )

    (root / "download_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(f"Manifest: {root / 'download_manifest.json'}")


if __name__ == "__main__":
    main()
