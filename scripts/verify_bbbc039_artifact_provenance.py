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



_S_BIAD634_DATASET = "S-BIAD634 / S-BSST265"
_S_BIAD634_SOURCE_URL = "https://www.ebi.ac.uk/biostudies/files/S-BSST265/dataset.zip"
_S_BIAD634_IMAGE_COUNT = 79


def build_s_biad634_dataset_provenance(manifest_path: Path) -> dict[str, Any]:
    """Validate and fingerprint the exact target-domain dataset used for transfer."""
    manifest = _read_json_mapping(manifest_path)
    if manifest.get("dataset") != _S_BIAD634_DATASET:
        raise ValueError("S-BIAD634 manifest identifies an unexpected dataset")
    if manifest.get("source_url") != _S_BIAD634_SOURCE_URL:
        raise ValueError("S-BIAD634 manifest does not identify the official BioStudies archive")
    if manifest.get("expected_public_license") != "CC0":
        raise ValueError("S-BIAD634 manifest does not record the expected CC0 license")

    archive_sha256 = manifest.get("archive_sha256")
    if not isinstance(archive_sha256, str) or not _SHA256_RE.fullmatch(archive_sha256):
        raise ValueError("S-BIAD634 archive SHA-256 is missing or invalid")

    files = manifest.get("files")
    if not isinstance(files, list) or any(not isinstance(item, str) or not item.strip() for item in files):
        raise ValueError("S-BIAD634 manifest has an invalid extracted-file inventory")
    if len(files) != len(set(files)):
        raise ValueError("S-BIAD634 extracted-file inventory contains duplicates")
    file_set = set(files)

    inventories: dict[str, list[str]] = {}
    for field in ("raw_image_files", "groundtruth_files", "metadata_candidates"):
        members = manifest.get(field)
        if not isinstance(members, list) or any(
            not isinstance(item, str) or not item.strip() for item in members
        ):
            raise ValueError(f"S-BIAD634 manifest has an invalid {field} inventory")
        if len(members) != len(set(members)):
            raise ValueError(f"S-BIAD634 {field} inventory contains duplicates")
        if not set(members).issubset(file_set):
            raise ValueError(f"S-BIAD634 {field} inventory references files outside the archive inventory")
        inventories[field] = members

    raw_count = len(inventories["raw_image_files"])
    groundtruth_count = len(inventories["groundtruth_files"])
    if raw_count != _S_BIAD634_IMAGE_COUNT or groundtruth_count < raw_count:
        raise ValueError(
            "S-BIAD634 manifest must inventory exactly 79 raw images and at least 79 ground-truth masks: "
            f"raw={raw_count}, groundtruth={groundtruth_count}"
        )

    raw_stems = [Path(path).stem for path in inventories["raw_image_files"]]
    if len(set(raw_stems)) != raw_count:
        raise ValueError("S-BIAD634 raw-image inventory contains duplicate image stems")
    raw_by_stem = {
        Path(path).stem: path for path in inventories["raw_image_files"]
    }
    groundtruth_by_stem: dict[str, list[str]] = {}
    for path in inventories["groundtruth_files"]:
        groundtruth_by_stem.setdefault(Path(path).stem, []).append(path)

    missing_masks = sorted(stem for stem in raw_by_stem if stem not in groundtruth_by_stem)
    ambiguous_masks = sorted(
        stem for stem in raw_by_stem if len(groundtruth_by_stem.get(stem, [])) != 1
    )
    if missing_masks or ambiguous_masks:
        raise ValueError(
            "S-BIAD634 raw images must each have exactly one matching ground-truth mask: "
            f"missing_masks={missing_masks[:10]}, ambiguous_masks={ambiguous_masks[:10]}"
        )

    pairing = [
        {
            "stem": stem,
            "raw_image": raw_by_stem[stem],
            "groundtruth": groundtruth_by_stem[stem][0],
        }
        for stem in sorted(raw_by_stem)
    ]
    pairing_sha256 = hashlib.sha256(
        json.dumps(pairing, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return {
        "dataset": _S_BIAD634_DATASET,
        "source_url": _S_BIAD634_SOURCE_URL,
        "expected_public_license": "CC0",
        "archive_sha256": archive_sha256,
        "manifest_sha256": _sha256(manifest_path),
        "file_count": len(files),
        "raw_image_count": raw_count,
        "groundtruth_count": groundtruth_count,
        "paired_image_count": len(pairing),
        "unmatched_groundtruth_count": groundtruth_count - len(pairing),
        "pairing_sha256": pairing_sha256,
        "metadata_candidate_count": len(inventories["metadata_candidates"]),
    }


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
