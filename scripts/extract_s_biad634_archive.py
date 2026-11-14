#!/usr/bin/env python3
"""Extract a run-scoped S-BIAD634 archive only after verifying its manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath

DATASET = "S-BIAD634 / S-BSST265"
SOURCE_URL = "https://www.ebi.ac.uk/biostudies/files/S-BSST265/dataset.zip"

# The BioImage Archive record documents 468 files and a 472.2 MiB study.
# These limits leave room for metadata/ZIP overhead without permitting an
# unbounded archive expansion or an unexpectedly large individual member.
MAX_ARCHIVE_BYTES = 600 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 512
MAX_MEMBER_UNCOMPRESSED_BYTES = 64 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED_BYTES = 768 * 1024 * 1024


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_member(info: zipfile.ZipInfo) -> str | None:
    name = info.filename
    posix = PurePosixPath(name)
    windows = PureWindowsPath(name)
    if (
        not name
        or "\\" in name
        or "\x00" in name
        or posix.is_absolute()
        or windows.is_absolute()
        or bool(windows.drive)
        or ".." in posix.parts
        or ".." in windows.parts
        or stat.S_ISLNK(info.external_attr >> 16)
    ):
        raise ValueError(f"Unsafe target-dataset ZIP member: {name!r}")
    file_type = stat.S_IFMT(info.external_attr >> 16)
    if file_type not in (0, stat.S_IFREG, stat.S_IFDIR):
        raise ValueError(f"Unsupported target-dataset ZIP member type: {name!r}")
    if info.is_dir():
        return None
    return name


def validated_member_names(infos: list[zipfile.ZipInfo]) -> list[str]:
    """Validate ZIP paths and declared expansion sizes before reading member data."""
    if len(infos) > MAX_ARCHIVE_ENTRIES:
        raise ValueError(
            f"Target-dataset ZIP has {len(infos)} entries; maximum is {MAX_ARCHIVE_ENTRIES}"
        )

    members: list[str] = []
    seen: set[str] = set()
    total_uncompressed_bytes = 0
    for info in infos:
        safe_name = _safe_member(info)
        normalized = str(PurePosixPath(info.filename))
        expected_name = normalized + ("/" if info.is_dir() else "")
        if normalized in {"", "."} or info.filename != expected_name:
            raise ValueError(f"Non-canonical target-dataset ZIP member: {info.filename!r}")
        if normalized in seen:
            raise ValueError(f"Duplicate target-dataset ZIP member: {info.filename!r}")
        seen.add(normalized)

        if info.file_size < 0 or info.compress_size < 0:
            raise ValueError(f"Invalid target-dataset ZIP member size: {info.filename!r}")
        if info.is_dir():
            if info.file_size != 0:
                raise ValueError(f"Directory ZIP member contains data: {info.filename!r}")
            continue
        if info.file_size > MAX_MEMBER_UNCOMPRESSED_BYTES:
            raise ValueError(
                f"Target-dataset ZIP member exceeds the per-file limit: "
                f"{info.filename!r} ({info.file_size} bytes)"
            )

        total_uncompressed_bytes += info.file_size
        if total_uncompressed_bytes > MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise ValueError(
                "Target-dataset ZIP exceeds the total uncompressed-size limit "
                f"({total_uncompressed_bytes} > {MAX_TOTAL_UNCOMPRESSED_BYTES} bytes)"
            )
        if safe_name is None:
            raise ValueError(f"Invalid target-dataset ZIP file member: {info.filename!r}")
        members.append(safe_name)
    return members


def extract_verified_dataset(
    data_root: Path,
    *,
    expected_source_url: str = SOURCE_URL,
) -> dict[str, object]:
    root = Path(data_root)
    archive = root / "dataset.zip"
    manifest_path = root / "download_manifest.json"
    if not archive.is_file():
        raise FileNotFoundError(f"Shared target-dataset archive is missing: {archive}")
    archive_size = archive.stat().st_size
    if archive_size > MAX_ARCHIVE_BYTES:
        raise ValueError(
            f"Target-dataset ZIP exceeds the compressed archive limit "
            f"({archive_size} > {MAX_ARCHIVE_BYTES} bytes)"
        )
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Shared target-dataset manifest is missing: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Target-dataset manifest must be a JSON object")
    if manifest.get("dataset") != DATASET:
        raise ValueError("Target-dataset manifest identifies an unexpected dataset")
    if manifest.get("source_url") != expected_source_url:
        raise ValueError("Target-dataset manifest identifies an unexpected source URL")
    if manifest.get("expected_public_license") != "CC0":
        raise ValueError("Target-dataset manifest does not record the expected CC0 license")

    expected_digest = manifest.get("archive_sha256")
    if (
        not isinstance(expected_digest, str)
        or len(expected_digest) != 64
        or any(char not in "0123456789abcdef" for char in expected_digest)
    ):
        raise ValueError("Target-dataset manifest has no valid archive SHA-256")
    actual_digest = sha256(archive)
    if actual_digest != expected_digest:
        raise ValueError(
            f"Target-dataset archive SHA-256 mismatch: expected {expected_digest}, got {actual_digest}"
        )

    expected_files = manifest.get("files")
    if (
        not isinstance(expected_files, list)
        or not expected_files
        or not all(isinstance(name, str) and name for name in expected_files)
        or len(expected_files) > MAX_ARCHIVE_ENTRIES
        or len(expected_files) != len(set(expected_files))
    ):
        raise ValueError("Target-dataset manifest has an invalid file inventory")

    raw_images = [name for name in expected_files if "/rawimages/" in f"/{name}"]
    groundtruth = [name for name in expected_files if "/groundtruth/" in f"/{name}"]
    metadata = [
        name for name in expected_files
        if name.lower().endswith((".txt", ".csv", ".tsv"))
    ]
    if manifest.get("raw_image_files") != raw_images:
        raise ValueError("Target-dataset raw-image inventory does not match its file list")
    if manifest.get("groundtruth_files") != groundtruth:
        raise ValueError("Target-dataset ground-truth inventory does not match its file list")
    if manifest.get("metadata_candidates") != metadata:
        raise ValueError("Target-dataset metadata inventory does not match its file list")

    root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".s-biad634-extract-", dir=root))
    candidate = staging / "extracted"
    try:
        with zipfile.ZipFile(archive) as dataset_zip:
            # Inspect the central directory and enforce expansion limits before
            # testzip() decompresses any member or extractall() writes any file.
            members = validated_member_names(dataset_zip.infolist())
            if sorted(members) != sorted(expected_files):
                raise ValueError("Target-dataset ZIP members do not match the verified manifest")
            bad_member = dataset_zip.testzip()
            if bad_member is not None:
                raise zipfile.BadZipFile(f"Corrupt target-dataset ZIP member: {bad_member}")
            candidate.mkdir()
            dataset_zip.extractall(candidate)

        actual_files = sorted(
            str(path.relative_to(candidate))
            for path in candidate.rglob("*")
            if path.is_file()
        )
        if actual_files != sorted(expected_files):
            raise ValueError("Extracted target-dataset files do not match the verified manifest")

        extracted = root / "extracted"
        if extracted.exists():
            shutil.rmtree(extracted)
        candidate.replace(extracted)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    return {
        "archive_sha256": actual_digest,
        "file_count": len(actual_files),
        "raw_image_files": len(raw_images),
        "groundtruth_files": len(groundtruth),
        "extracted_dir": str(root / "extracted"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract the E5 target dataset from a manifest-verified run artifact."
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("data/raw/S-BIAD634"),
    )
    args = parser.parse_args()
    try:
        result = extract_verified_dataset(args.data_root)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"target-dataset extraction failed: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
