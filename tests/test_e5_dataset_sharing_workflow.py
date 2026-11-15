from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "e5_ablations.yml"


def test_e5_downloads_target_dataset_once_and_reuses_verified_artifact() -> None:
    workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    triggers = workflow["on"]

    push = triggers["push"]
    assert push["branches"] == ["main"]
    assert ".github/workflows/e5_ablations.yml" in push["paths"]
    assert "scripts/extract_s_biad634_archive.py" in push["paths"]
    assert "scripts/download_s_biad634.py" in push["paths"]
    assert "workflow_dispatch" in triggers
    dispatch_inputs = triggers["workflow_dispatch"]["inputs"]
    assert dispatch_inputs["prepare_only"]["type"] == "boolean"
    assert dispatch_inputs["prepare_only"]["default"] == "false"

    jobs = workflow["jobs"]
    prepare = jobs["prepare_target_dataset"]
    assert "if" not in prepare, "dataset preparation must still run in prepare-only mode"
    download_commands = [
        step["run"]
        for step in prepare["steps"]
        if "run" in step and "scripts/download_s_biad634.py" in step["run"]
    ]
    assert download_commands == [
        "python scripts/download_s_biad634.py --data-root data/raw/S-BIAD634 --keep-archive --skip-extract"
    ]

    publish = next(
        step for step in prepare["steps"]
        if step.get("name") == "Publish shared target dataset artifact"
    )
    assert publish["with"]["name"] == "e5-target-dataset-${{ github.run_id }}"
    assert publish["with"]["retention-days"] == "1"
    assert publish["with"]["compression-level"] == "0"
    assert "data/raw/S-BIAD634/archive_inventory.json" in publish["with"]["path"]

    inventory = next(
        step for step in prepare["steps"]
        if step.get("name") == "Record target archive size and digest"
    )
    assert "archive_bytes" in inventory["run"]
    assert "archive_sha256" in inventory["run"]
    assert "manifest_sha256" in inventory["run"]
    assert "zip_entry_count" in inventory["run"]
    assert "zip_file_entry_count" in inventory["run"]
    assert "zip_directory_entry_count" in inventory["run"]
    assert "manifest_file_count" in inventory["run"]
    assert "manifest_files = manifest.get(\"files\")" in inventory["run"]
    assert "manifest_file_count = len(manifest_files)" in inventory["run"]
    assert "zip_file_names != sorted(manifest_files)" in inventory["run"]
    assert "manifest.get(\"raw_image_files\") != raw_image_files" in inventory["run"]
    assert "manifest.get(\"groundtruth_files\") != groundtruth_files" in inventory["run"]
    assert "\"raw_image_count\": len(raw_image_files)" in inventory["run"]
    assert "\"groundtruth_count\": len(groundtruth_files)" in inventory["run"]
    assert "len(manifest_files) != len(set(manifest_files))" in inventory["run"]
    assert "sum(entry.is_dir() for entry in entries)" in inventory["run"]
    assert "zipfile.ZipFile(archive)" in inventory["run"]
    assert "dataset_zip.infolist()" in inventory["run"]
    assert "inventory_path.write_text" in inventory["run"]
    assert "archive_inventory.json" in inventory["run"]
    expected_env = inventory["env"]
    assert expected_env["BIONUCLEI_S_BIAD634_EXPECTED_ARCHIVE_SHA256"] == "8285987ed4d57c46a46a55a33c1c085875ea41f429b59cde31d249741aa07ad1"
    assert expected_env["BIONUCLEI_S_BIAD634_EXPECTED_FILE_COUNT"] == "470"
    assert expected_env["BIONUCLEI_S_BIAD634_EXPECTED_RAW_IMAGE_COUNT"] == "79"
    assert expected_env["BIONUCLEI_S_BIAD634_EXPECTED_GROUNDTRUTH_COUNT"] == "79"
    assert "expected_archive_sha256" in inventory["run"]
    assert "manifest.get(\"expected_public_license\") != expected_license" in inventory["run"]
    assert "len(raw_image_files) != expected_raw_image_count" in inventory["run"]
    assert "len(groundtruth_files) != expected_groundtruth_count" in inventory["run"]

    variant = jobs["e5_variant"]
    assert variant["if"] == "${{ inputs.prepare_only != true }}"
    assert variant["needs"] == "prepare_target_dataset"
    gate = jobs["e5_gate"]
    assert gate["if"] == "${{ inputs.prepare_only != true }}"
    assert set(gate["needs"]) == {"e5_variant", "prepare_target_dataset"}

    for job, expected_path in (
        (variant, "data/raw/S-BIAD634"),
        (gate, "data/shared-target/S-BIAD634"),
    ):
        download = next(
            step for step in job["steps"]
            if step.get("name") == "Download shared target dataset artifact"
        )
        assert download["uses"] == "actions/download-artifact@v4"
        assert download["with"]["name"] == "e5-target-dataset-${{ github.run_id }}"
        assert download["with"]["path"] == expected_path
        extract = next(
            step for step in job["steps"]
            if step.get("name") == "Verify and extract shared target dataset"
        )
        assert "scripts/extract_s_biad634_archive.py" in extract["run"]
    gate_verification = next(
        step for step in gate["steps"]
        if step.get("name") == "Verify all preregistered variants and provenance"
    )
    assert "target_manifest_sha256" in gate_verification["run"]

    all_downloads = [
        step["run"]
        for job in jobs.values()
        for step in job.get("steps", [])
        if "run" in step and "scripts/download_s_biad634.py" in step["run"]
    ]
    assert len(all_downloads) == 1, "only the preparation job may contact BioStudies"



def _inventory_script() -> str:
    workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    step = next(
        item for item in workflow["jobs"]["prepare_target_dataset"]["steps"]
        if item.get("name") == "Record target archive size and digest"
    )
    command = step["run"]
    lines = command.splitlines()
    assert lines[0] == "python - <<'PY'" and lines[-1] == "PY"
    return "\n".join(lines[1:-1])


def _run_inventory(
    tmp_path: Path,
    manifest_overrides: dict[str, object] | None = None,
    *,
    expected_archive_sha256: str | None = None,
    expected_file_count: int | None = None,
    expected_raw_image_count: int | None = None,
    expected_groundtruth_count: int | None = None,
):
    data_root = tmp_path / "data" / "raw" / "S-BIAD634"
    data_root.mkdir(parents=True)
    archive = data_root / "dataset.zip"
    files = [
        "dataset/rawimages/image_001.tif",
        "dataset/groundtruth/mask_001.tif",
        "dataset/readme.txt",
    ]
    with zipfile.ZipFile(archive, "w") as dataset_zip:
        dataset_zip.writestr(files[0], b"raw-image")
        dataset_zip.writestr(files[1], b"ground-truth")
        dataset_zip.writestr(files[2], b"CC0")
        dataset_zip.writestr("dataset/empty/", b"")

    manifest = {
        "dataset": "S-BIAD634 / S-BSST265",
        "source_url": "https://www.ebi.ac.uk/biostudies/files/S-BSST265/dataset.zip",
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "expected_public_license": "CC0",
        "files": files,
        "raw_image_files": [files[0]],
        "groundtruth_files": [files[1]],
    }
    if manifest_overrides:
        manifest.update(manifest_overrides)
    (data_root / "download_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    env = os.environ.copy()
    env.update({
        "BIONUCLEI_S_BIAD634_EXPECTED_ARCHIVE_SHA256": (
            expected_archive_sha256 or manifest["archive_sha256"]
        ),
        "BIONUCLEI_S_BIAD634_EXPECTED_FILE_COUNT": str(
            expected_file_count if expected_file_count is not None else len(files)
        ),
        "BIONUCLEI_S_BIAD634_EXPECTED_RAW_IMAGE_COUNT": str(
            expected_raw_image_count if expected_raw_image_count is not None else 1
        ),
        "BIONUCLEI_S_BIAD634_EXPECTED_GROUNDTRUTH_COUNT": str(
            expected_groundtruth_count if expected_groundtruth_count is not None else 1
        ),
    })
    completed = subprocess.run(
        [sys.executable, "-c", _inventory_script()],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    return completed, data_root, archive


def test_archive_inventory_counts_real_zip_entries_and_classifies_paths(tmp_path: Path) -> None:
    completed, data_root, archive = _run_inventory(tmp_path)
    assert completed.returncode == 0, completed.stderr

    inventory = json.loads(
        (data_root / "archive_inventory.json").read_text(encoding="utf-8")
    )
    assert inventory["archive_bytes"] == archive.stat().st_size
    assert inventory["zip_entry_count"] == 4
    assert inventory["zip_file_entry_count"] == 3
    assert inventory["zip_directory_entry_count"] == 1
    assert inventory["manifest_file_count"] == 3
    assert inventory["raw_image_count"] == 1
    assert inventory["groundtruth_count"] == 1
    assert inventory["expected_archive_sha256"] == inventory["archive_sha256"]
    assert inventory["expected_file_count"] == 3
    assert inventory["expected_raw_image_count"] == 1
    assert inventory["expected_groundtruth_count"] == 1


def test_archive_inventory_rejects_same_count_but_different_member_paths(tmp_path: Path) -> None:
    completed, _data_root, _archive = _run_inventory(
        tmp_path,
        {"files": [
            "dataset/rawimages/image_001.tif",
            "dataset/groundtruth/mask_001.tif",
            "dataset/metadata.txt",
        ]},
    )
    assert completed.returncode != 0
    assert "Archive file paths do not match the manifest file inventory" in completed.stderr


def test_archive_inventory_rejects_misclassified_manifest_paths(tmp_path: Path) -> None:
    completed, _data_root, _archive = _run_inventory(
        tmp_path,
        {"raw_image_files": []},
    )
    assert completed.returncode != 0
    assert "Archive raw-image paths do not match the manifest inventory" in completed.stderr


def test_archive_inventory_rejects_unpinned_archive_sha256(tmp_path: Path) -> None:
    completed, _data_root, _archive = _run_inventory(
        tmp_path,
        expected_archive_sha256="0" * 64,
    )
    assert completed.returncode != 0
    assert "pinned S-BIAD634 release" in completed.stderr


def test_archive_inventory_rejects_incomplete_target_image_counts(tmp_path: Path) -> None:
    completed, _data_root, _archive = _run_inventory(
        tmp_path,
        expected_raw_image_count=2,
    )
    assert completed.returncode != 0
    assert "raw-image count does not match the pinned S-BIAD634 release" in completed.stderr


def test_archive_inventory_rejects_unexpected_public_license(tmp_path: Path) -> None:
    completed, _data_root, _archive = _run_inventory(
        tmp_path,
        {"expected_public_license": "CC-BY-4.0"},
    )
    assert completed.returncode != 0
    assert "does not confirm the pinned CC0 license" in completed.stderr
