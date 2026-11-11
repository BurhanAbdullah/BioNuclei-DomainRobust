"""Bind the BBBC039 dataset and official split identity into transfer provenance."""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_ARCHIVES = ("images", "masks", "metadata")
_REQUIRED_PARTITIONS = ("train", "validation", "test")


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
    """Validate and fingerprint the dataset, split and config carried by a baseline."""
    download_path = artifact_root / "data/raw/BBBC039/download_manifest.json"
    split_path = artifact_root / "data/manifests/bbbc039_official_split.json"
    download = _read_json_mapping(download_path)
    split = _read_json_mapping(split_path)

    dataset = download.get("dataset")
    release = download.get("release")
    if dataset != "BBBC039v1" or release != "v1":
        raise ValueError(
            f"baseline artifact must identify BBBC039v1 release v1: dataset={dataset!r}, release={release!r}"
        )
    if split.get("dataset") != dataset:
        raise ValueError("BBBC039 split manifest dataset does not match its download manifest")

    reference = download.get("authoritative_reference")
    if not isinstance(reference, str) or not reference.startswith("https://"):
        raise ValueError("BBBC039 download manifest has no authoritative HTTPS reference")

    archives = download.get("archives")
    if not isinstance(archives, Mapping):
        raise ValueError("BBBC039 download manifest has no archive inventory")
    archive_hashes: dict[str, str] = {}
    for name in _REQUIRED_ARCHIVES:
        record = archives.get(name)
        digest = record.get("sha256") if isinstance(record, Mapping) else None
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise ValueError(f"BBBC039 {name} archive SHA-256 is missing or invalid")
        archive_hashes[name] = digest

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

    if not config_path.is_file():
        raise FileNotFoundError(f"committed BBBC039 baseline config is missing: {config_path}")

    return {
        "dataset": dataset,
        "dataset_release": release,
        "authoritative_reference": reference,
        "download_manifest_sha256": _sha256(download_path),
        "split_manifest_sha256": _sha256(split_path),
        "baseline_config_sha256": _sha256(config_path),
        "source_archive_sha256": archive_hashes,
        "split_counts": split_counts,
    }
