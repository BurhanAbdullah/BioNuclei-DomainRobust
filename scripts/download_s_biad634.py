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
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
import zlib
from pathlib import Path

if __package__:
    from .extract_s_biad634_archive import (
        MAX_ARCHIVE_BYTES,
        extract_verified_dataset,
        validated_member_names,
    )
else:
    from extract_s_biad634_archive import (
        MAX_ARCHIVE_BYTES,
        extract_verified_dataset,
        validated_member_names,
    )

SOURCE_URL = "https://www.ebi.ac.uk/biostudies/files/S-BSST265/dataset.zip"
DOWNLOAD_TIMEOUT_SECONDS = 10
DOWNLOAD_TOTAL_TIMEOUT_SECONDS = 10 * 60
DOWNLOAD_READ_CHUNK_BYTES = 64 * 1024
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


class DownloadDeadlineExceeded(TimeoutError):
    """The total BioStudies download budget was exhausted."""


class DownloadSocketTimeoutControlUnavailable(RuntimeError):
    """The response socket cannot enforce the remaining total download deadline."""


def _set_response_read_timeout(response, timeout: float) -> None:
    """Clamp the underlying urllib socket timeout to the remaining total budget.

    urlopen(timeout=...) configures an inactivity timeout once, at connection
    creation. It does not shrink as the monotonic download deadline approaches.
    """
    raw_socket = getattr(
        getattr(getattr(response, "fp", None), "raw", None),
        "_sock",
        None,
    )
    settimeout = getattr(raw_socket, "settimeout", None)
    if not callable(settimeout):
        raise DownloadSocketTimeoutControlUnavailable(
            "BioStudies response socket timeout control is unavailable; refusing an unbounded read"
        )
    try:
        settimeout(timeout)
    except Exception as exc:
        raise DownloadSocketTimeoutControlUnavailable(
            "BioStudies response socket timeout control could not be applied; refusing an unbounded read"
        ) from exc


class CorruptDatasetArchiveError(RuntimeError):
    """A completed HTTP transfer did not produce a readable, CRC-valid ZIP."""


def _validate_downloaded_archive(path: Path) -> None:
    """Validate every member before the temporary archive can replace the destination."""
    try:
        with zipfile.ZipFile(path) as archive:
            # Apply entry/path/expansion limits before CRC scanning decompresses members.
            validated_member_names(archive.infolist())
            corrupt_member = archive.testzip()
    except (zipfile.BadZipFile, EOFError, zlib.error) as exc:
        raise CorruptDatasetArchiveError(
            "downloaded dataset is not a valid, readable ZIP archive"
        ) from exc
    if corrupt_member is not None:
        raise CorruptDatasetArchiveError(
            f"downloaded dataset ZIP contains a corrupt member: {corrupt_member}"
        )


def download(url: str, destination: Path) -> None:
    """Download atomically within one total monotonic budget.

    Socket inactivity timeouts bound each read, while read1() returns available
    bytes without waiting for a full chunk. Checking the same deadline between
    reads prevents a slow-trickle response from extending the job indefinitely.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + DOWNLOAD_TOTAL_TIMEOUT_SECONDS

    for attempt in range(1, MAX_DOWNLOAD_ATTEMPTS + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise DownloadDeadlineExceeded(
                f"BioStudies download exceeded its {DOWNLOAD_TOTAL_TIMEOUT_SECONDS}s total deadline"
            )

        temporary_path: Path | None = None
        try:
            with urllib.request.urlopen(
                url,
                timeout=min(DOWNLOAD_TIMEOUT_SECONDS, remaining),
            ) as response:
                headers = getattr(response, "headers", None)
                content_length = headers.get("Content-Length") if headers is not None else None
                if content_length:
                    try:
                        declared_size = int(content_length)
                    except (TypeError, ValueError) as exc:
                        raise ValueError("BioStudies returned an invalid Content-Length") from exc
                    if declared_size > MAX_ARCHIVE_BYTES:
                        raise ValueError(
                            f"BioStudies archive exceeds the compressed-size limit "
                            f"({declared_size} > {MAX_ARCHIVE_BYTES} bytes)"
                        )

                read_chunk = getattr(response, "read1", None)
                if not callable(read_chunk):
                    raise RuntimeError(
                        "BioStudies response does not support bounded read1() streaming"
                    )

                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    prefix=f".{destination.name}.",
                    suffix=".part",
                    dir=destination.parent,
                    delete=False,
                ) as out:
                    temporary_path = Path(out.name)
                    total_bytes = 0
                    while True:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise DownloadDeadlineExceeded(
                                f"BioStudies download exceeded its {DOWNLOAD_TOTAL_TIMEOUT_SECONDS}s total deadline"
                            )
                        _set_response_read_timeout(
                            response,
                            min(DOWNLOAD_TIMEOUT_SECONDS, remaining),
                        )
                        chunk = read_chunk(DOWNLOAD_READ_CHUNK_BYTES)
                        if not chunk:
                            break
                        total_bytes += len(chunk)
                        if total_bytes > MAX_ARCHIVE_BYTES:
                            raise ValueError(
                                f"BioStudies archive exceeds the compressed-size limit "
                                f"({total_bytes} > {MAX_ARCHIVE_BYTES} bytes)"
                            )
                        out.write(chunk)
                    out.flush()

            _validate_downloaded_archive(temporary_path)
            temporary_path.replace(destination)
            temporary_path = None
            return
        except DownloadDeadlineExceeded:
            raise
        except CorruptDatasetArchiveError as exc:
            if attempt == MAX_DOWNLOAD_ATTEMPTS:
                raise
            delay = _retry_delay(attempt)
            reason = str(exc)
        except urllib.error.HTTPError as exc:
            retryable = exc.code in RETRYABLE_HTTP_STATUS_CODES
            if not retryable or attempt == MAX_DOWNLOAD_ATTEMPTS:
                exc.close()
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

        remaining = deadline - time.monotonic()
        if remaining <= 0 or delay >= remaining:
            raise DownloadDeadlineExceeded(
                f"BioStudies download exhausted its {DOWNLOAD_TOTAL_TIMEOUT_SECONDS}s total deadline during retry backoff"
            )
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
    parser.add_argument("--skip-extract", action="store_true", help="Inventory the ZIP without extracting it.")
    args = parser.parse_args()

    root = args.data_root
    root.mkdir(parents=True, exist_ok=True)
    archive = root / "dataset.zip"
    download(args.url, archive)
    archive_hash = sha256(archive)

    with zipfile.ZipFile(archive) as zf:
        # Validate paths and declared expansion sizes before CRC verification
        # decompresses any member, including in inventory-only mode.
        files = sorted(validated_member_names(zf.infolist()))
        bad = zf.testzip()
        if bad is not None:
            raise SystemExit(f"Corrupt ZIP member: {bad}")
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

    if not args.skip_extract:
        # This validates the archive digest and every ZIP member before writing.
        extract_verified_dataset(root, expected_source_url=args.url)

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
