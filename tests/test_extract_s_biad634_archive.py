from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from scripts.extract_s_biad634_archive import (
    DATASET,
    SOURCE_URL,
    extract_verified_dataset,
)


def _write_dataset(root: Path, *, members: dict[str, bytes] | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    archive = root / "dataset.zip"
    payload = members or {
        "dataset/rawimages/image_001.tif": b"raw-image",
        "dataset/groundtruth/mask_001.tif": b"ground-truth",
        "dataset/readme.txt": b"CC0 dataset",
    }
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as dataset_zip:
        for name, data in payload.items():
            dataset_zip.writestr(name, data)
    files = sorted(payload)
    raw = [name for name in files if "/rawimages/" in f"/{name}"]
    groundtruth = [name for name in files if "/groundtruth/" in f"/{name}"]
    metadata = [name for name in files if name.lower().endswith((".txt", ".csv", ".tsv"))]
    manifest = {
        "dataset": DATASET,
        "source_url": SOURCE_URL,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "expected_public_license": "CC0",
        "files": files,
        "raw_image_files": raw,
        "groundtruth_files": groundtruth,
        "metadata_candidates": metadata,
    }
    (root / "download_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return archive


def test_extracts_only_the_archive_bound_to_the_manifest(tmp_path: Path) -> None:
    root = tmp_path / "S-BIAD634"
    archive = _write_dataset(root)

    result = extract_verified_dataset(root)

    assert result["archive_sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert result["file_count"] == 3
    assert result["raw_image_files"] == 1
    assert result["groundtruth_files"] == 1
    assert (root / "extracted/dataset/rawimages/image_001.tif").read_bytes() == b"raw-image"
    assert (root / "extracted/dataset/groundtruth/mask_001.tif").read_bytes() == b"ground-truth"


def test_rejects_archive_digest_mismatch_before_extraction(tmp_path: Path) -> None:
    root = tmp_path / "S-BIAD634"
    archive = _write_dataset(root)
    manifest_path = root / "download_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["archive_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="archive SHA-256 mismatch"):
        extract_verified_dataset(root)

    assert archive.is_file()
    assert not (root / "extracted").exists()


def test_rejects_manifest_file_inventory_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "S-BIAD634"
    _write_dataset(root)
    manifest_path = root / "download_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"].remove("dataset/readme.txt")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="metadata inventory"):
        extract_verified_dataset(root)

    assert not (root / "extracted").exists()


@pytest.mark.parametrize("member", ["../escape.txt", "../"])
def test_rejects_zip_path_traversal_without_writing_outside_root(
    tmp_path: Path, member: str
) -> None:
    root = tmp_path / "S-BIAD634"
    _write_dataset(root, members={member: b"outside"})
    outside = tmp_path / "escape.txt"

    with pytest.raises(ValueError, match="Unsafe target-dataset ZIP member"):
        extract_verified_dataset(root)

    assert not outside.exists()
    assert not (root / "extracted").exists()
