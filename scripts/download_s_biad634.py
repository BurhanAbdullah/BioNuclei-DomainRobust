#!/usr/bin/env python3
"""Download and inventory S-BIAD634 / S-BSST265 from BioStudies.

The dataset is public CC0. Raw data are never committed; this script records
source provenance and a deterministic inventory for later target-domain
experiments.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

SOURCE_URL = "https://www.ebi.ac.uk/biostudies/files/S-BSST265/dataset.zip"
DOWNLOAD_TIMEOUT_SECONDS = 120
MAX_DOWNLOAD_ATTEMPTS = 4
RETRY_BASE_SECONDS = 2
RETRY_MAX_SECONDS = 30
RETRYABLE_HTTP_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _retry_delay(attempt: int) -> float:
    return min(RETRY_BASE_SECONDS * (2 ** (attempt - 1)), RETRY_MAX_SECONDS)


def download(url: str, destination: Path) -> None:
    """Download atomically, retrying only transient transport/server failures.

    A failed or interrupted transfer must never leave a partial ZIP at the
    destination path: the evaluator opens that path immediately after download.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, MAX_DOWNLOAD_ATTEMPTS + 1):
        temporary_path: Path | None = None
        try:
            with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    prefix=f".{destination.name}.",
                    suffix=".part",
                    dir=destination.parent,
                    delete=False,
                ) as out:
                    temporary_path = Path(out.name)
                    shutil.copyfileobj(response, out, length=1024 * 1024)
                    out.flush()

            temporary_path.replace(destination)
            temporary_path = None
            return
        except urllib.error.HTTPError as exc:
            retryable = exc.code in RETRYABLE_HTTP_STATUS_CODES
            if not retryable or attempt == MAX_DOWNLOAD_ATTEMPTS:
                raise
            exc.close()
            delay = _retry_delay(attempt)
            reason = f"HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException) as exc:
            if attempt == MAX_DOWNLOAD_ATTEMPTS:
                raise
            delay = _retry_delay(attempt)
            reason = type(exc).__name__
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

        print(
            f"Transient BioStudies download failure ({reason}); "
            f"retrying in {delay:g}s (attempt {attempt}/{MAX_DOWNLOAD_ATTEMPTS}).",
            file=sys.stderr,
        )
        time.sleep(delay)


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
