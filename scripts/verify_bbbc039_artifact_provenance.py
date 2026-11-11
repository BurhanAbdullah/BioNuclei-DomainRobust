"""Bind the BBBC039 dataset and official split identity into transfer provenance."""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_ARCHIVES = ("images", "masks", "metadata")
_REQUIRED_PARTITIONS = ("train", "validation", "test")
_EXPECTED_SPLIT_COUNTS = {"train": 100, "validation": 50, "test": 50}
_EXPECTED_IMAGE_SHAPE = [520, 696]
_OFFICIAL_REFERENCE = "https://bbbc.broadinstitute.org/BBBC039"
_OFFICIAL_BASE_URL = "https://data.broadinstitute.org/bbbc/BBBC039"


def _read_json_mapping(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"required baseline provenance file is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"baseline provenance file must contain a JSON object: {path}")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_baseline_artifact_provenance(
    artifact_root: Path,
    config_path: Path,
) -> dict[str, Any]:
    """Validate and fingerprint the dataset, split, acquisition report and config."""
    download_path = artifact_root / "data/raw/BBBC039/download_manifest.json"
    split_path = artifact_root / "data/manifests/bbbc039_official_split.json"
    verification_path = artifact_root / "data/raw/BBBC039/verification_report.json"
    download = _read_json_mapping(download_path)
    split = _read_json_mapping(split_path)
    verification = _read_json_mapping(verification_path)

    dataset = download.get("dataset")
    release = download.get("release")
    if dataset != "BBBC039v1" or release != "v1":
        raise ValueError(
            f"baseline artifact must identify BBBC039v1 release v1: dataset={dataset!r}, release={release!r}"
        )
    if split.get("dataset") != dataset:
        raise ValueError("BBBC039 split manifest dataset does not match its download manifest")

    reference = download.get("authoritative_reference")
    if reference != _OFFICIAL_REFERENCE:
        raise ValueError("BBBC039 download manifest does not identify the official authoritative reference")
    base_url = download.get("base_url")
    if base_url != _OFFICIAL_BASE_URL:
        raise ValueError("BBBC039 download manifest does not identify the official archive base URL")

    archives = download.get("archives")
    if not isinstance(archives, Mapping):
        raise ValueError("BBBC039 download manifest has no archive inventory")
    archive_hashes: dict[str, str] = {}
    archive_urls: dict[str, str] = {}
    for name in _REQUIRED_ARCHIVES:
        record = archives.get(name)
        expected_url = f"{_OFFICIAL_BASE_URL}/{name}.zip"
        url = record.get("url") if isinstance(record, Mapping) else None
        if url != expected_url:
            raise ValueError(f"BBBC039 {name} archive URL is not the official release URL")
        digest = record.get("sha256") if isinstance(record, Mapping) else None
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise ValueError(f"BBBC039 {name} archive SHA-256 is missing or invalid")
        archive_hashes[name] = digest
        archive_urls[name] = url

    partitions = split.get("partitions")
    if not isinstance(partitions, Mapping):
        raise ValueError("BBBC039 official split manifest has no partition mapping")
    split_counts: dict[str, int] = {}
    seen: set[str] = set()
    for name in _REQUIRED_PARTITIONS:
        members = partitions.get(name)
        if not isinstance(members, list) or not members:
            raise ValueError(f"BBBC039 official split manifest has no non-empty {name} partition")
        if any(not isinstance(member, str) or not member.strip() for member in members):
            raise ValueError(f"BBBC039 {name} partition contains an invalid image identifier")
        if len(members) != len(set(members)):
            raise ValueError(f"BBBC039 {name} partition contains duplicate image identifiers")
        overlap = seen.intersection(members)
        if overlap:
            raise ValueError(
                f"BBBC039 official split partitions overlap: {sorted(overlap)[:3]}"
            )
        seen.update(members)
        split_counts[name] = len(members)

    if split_counts != _EXPECTED_SPLIT_COUNTS:
        raise ValueError(
            "BBBC039 official split counts do not match the verified release: "
            f"expected={_EXPECTED_SPLIT_COUNTS}, actual={split_counts}"
        )
    declared_counts = split.get("counts")
    if not isinstance(declared_counts, Mapping) or dict(declared_counts) != split_counts:
        raise ValueError("BBBC039 split manifest declared counts do not match its partitions")
    split_validation = split.get("validation")
    if not isinstance(split_validation, Mapping) or split_validation.get("pairwise_overlap") is not False:
        raise ValueError("BBBC039 split manifest does not certify pairwise-disjoint partitions")

    expected_verification = {
        "dataset": dataset,
        "images": 200,
        "masks": 200,
        "image_shape": _EXPECTED_IMAGE_SHAPE,
        "image_dtype": "uint16",
        "image_channels": 1,
        "image_mask_correspondence_verified": True,
        "target_conversion_verified": True,
        "split_counts_detected": _EXPECTED_SPLIT_COUNTS,
        "expected_split_counts": _EXPECTED_SPLIT_COUNTS,
        "split_counts_verified": True,
    }
    for field, expected in expected_verification.items():
        if verification.get(field) != expected:
            raise ValueError(
                f"BBBC039 verification report {field} does not match the verified release"
            )

    if not config_path.is_file():
        raise FileNotFoundError(f"committed BBBC039 baseline config is missing: {config_path}")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, Mapping):
        raise ValueError("committed BBBC039 baseline config must contain a mapping")
    dataset_config = config.get("dataset")
    if not isinstance(dataset_config, Mapping) or dataset_config.get("name") != dataset:
        raise ValueError("committed BBBC039 config dataset name does not match the baseline artifact")
    if Path(str(dataset_config.get("root", ""))) != Path("data/raw/BBBC039"):
        raise ValueError("committed BBBC039 config dataset root does not match the baseline artifact")
    if Path(str(dataset_config.get("split_manifest", ""))) != Path(
        "data/manifests/bbbc039_official_split.json"
    ):
        raise ValueError("committed BBBC039 config split manifest path does not match the hashed artifact")

    return {
        "dataset": dataset,
        "dataset_release": release,
        "authoritative_reference": reference,
        "download_manifest_sha256": _sha256(download_path),
        "split_manifest_sha256": _sha256(split_path),
        "verification_report_sha256": _sha256(verification_path),
        "baseline_config_sha256": _sha256(config_path),
        "source_archive_urls": archive_urls,
        "source_archive_sha256": archive_hashes,
        "split_counts": split_counts,
    }
