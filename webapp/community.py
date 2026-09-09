"""Public community-analysis job service for BioNuclei.

This module orchestrates the existing deterministic BioNuclei inference/measurement
code. User-image retention is explicit opt-in and separately namespaced.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import tifffile

from bionuclei.inference import predict
from .app import _checkpoint

JOB_ROOT = Path(os.getenv("BIONUCLEI_JOB_DIR", "/tmp/bionuclei-community-jobs")).expanduser()
DB_PATH = JOB_ROOT / "jobs.sqlite3"
JOB_ROOT.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = int(os.getenv("BIONUCLEI_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
DEFAULT_RESULT_RETENTION_HOURS = int(os.getenv("BIONUCLEI_RESULT_RETENTION_HOURS", "24"))
DEFAULT_RESEARCH_RETENTION_DAYS = int(os.getenv("BIONUCLEI_RESEARCH_RETENTION_DAYS", "90"))
DB_LOCK = threading.Lock()


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            input_sha256 TEXT,
            input_name TEXT,
            retained_copy INTEGER NOT NULL DEFAULT 0,
            research_consent INTEGER NOT NULL DEFAULT 0,
            algorithm_profile TEXT NOT NULL,
            result_json TEXT,
            error TEXT
        )"""
    )
    conn.commit()
    return conn


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _set_job(job_id: str, **fields: object) -> None:
    fields["updated_at"] = _now().isoformat()
    assignments = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [job_id]
    with DB_LOCK, _db() as conn:
        conn.execute(f"UPDATE jobs SET {assignments} WHERE id = ?", values)
        conn.commit()


def _get_job(job_id: str) -> sqlite3.Row | None:
    with DB_LOCK, _db() as conn:
        return conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()


def _job_dir(job_id: str) -> Path:
    return JOB_ROOT / job_id


def _archive(job_id: str) -> Path:
    root = _job_dir(job_id)
    archive = JOB_ROOT / f"{job_id}.zip"
    with ZipFile(archive, "w", ZIP_DEFLATED) as zf:
        for path in root.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(root))
    return archive


def _save_research_copy(job_id: str, input_path: Path, input_sha256: str, metadata: dict) -> None:
    destination = JOB_ROOT / "research_contributions" / job_id
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(input_path, destination / "input" + input_path.suffix if False else destination / f"input{input_path.suffix}")
    (destination / "contribution.json").write_text(json.dumps({
        "job_id": job_id,
        "input_sha256": input_sha256,
        "created_at": _now().isoformat(),
        "retention_days": DEFAULT_RESEARCH_RETENTION_DAYS,
        "research_consent": True,
        "purpose": "Optional research contribution for future BioNuclei development and model-training datasets.",
        "metadata": metadata,
    }, indent=2) + "\n")


def delete_research_copy(job_id: str) -> bool:
    destination = JOB_ROOT / "research_contributions" / job_id
    row = _get_job(job_id)
    if row is None:
        raise FileNotFoundError(job_id)
    if not destination.exists():
        return False
    shutil.rmtree(destination, ignore_errors=True)
    _set_job(job_id, retained_copy=0, research_consent=0)
    return True


def _nd2_to_tiff(source: Path, destination: Path, *, channel: int = 0, time: int = 0, z: int = 0, field: int = 0) -> dict[str, object]:
    """Read a Nikon ND2 and deterministically extract one 2-D YX plane."""
    try:
        import nd2
    except ImportError as exc:  # pragma: no cover - exercised in deployment if dependency missing
        raise RuntimeError("ND2 support requires the optional 'nd2' package") from exc

    with nd2.ND2File(source) as ndfile:
        sizes = dict(ndfile.sizes)
        shape = tuple(ndfile.shape)
        axes = list(sizes.keys())
        if "Y" not in sizes or "X" not in sizes:
            raise ValueError(f"ND2 file has no Y/X image plane: sizes={sizes}")

        requested = {
            "C": channel,
            "T": time,
            "Z": z,
            "P": field,
            "S": 0,
            "V": field,
        }
        indexers: list[int | slice] = []
        selected: dict[str, int] = {}
        for axis in axes:
            if axis in {"Y", "X"}:
                indexers.append(slice(None))
                continue
            size = int(sizes[axis])
            if size < 1:
                raise ValueError(f"ND2 axis {axis} has invalid size {size}")
            value = int(requested.get(axis, 0))
            if value < 0 or value >= size:
                raise ValueError(f"ND2 axis {axis} index {value} outside [0, {size - 1}]")
            indexers.append(value)
            selected[axis] = value

        arr = np.asarray(ndfile.asarray())
        plane = arr[tuple(indexers)]
        plane = np.squeeze(plane)
        if plane.ndim != 2:
            raise ValueError(f"Selected ND2 plane is not 2-D: shape={plane.shape}, axes={axes}, sizes={sizes}")
        tifffile.imwrite(destination, plane)
        return {
            "input_format": "ND2",
            "reader": "nd2",
            "reader_version": getattr(nd2, "__version__", "unknown"),
            "source_shape": list(shape),
            "source_sizes": sizes,
            "source_axes": axes,
            "selected_indices": selected,
            "selected_plane_shape": list(plane.shape),
            "conversion": "ND2 plane extracted to TIFF for the 2-D BioNuclei inference pipeline",
        }


def _prepare_input(image_path: Path, root: Path, *, channel: int, time: int, z: int, field: int) -> tuple[Path, dict[str, object]]:
    suffix = image_path.suffix.lower()
    if suffix != ".nd2":
        return image_path, {"input_format": "TIFF", "conversion": None}
    destination = root / "input_plane.tif"
    metadata = _nd2_to_tiff(image_path, destination, channel=channel, time=time, z=z, field=field)
    return destination, metadata


def _run(job_id: str, image_path: Path, original_name: str, research_consent: bool, algorithm_profile: str, *, channel: int, time: int, z: int, field: int) -> None:
    root = _job_dir(job_id)
    output = root / "results"
    try:
        _set_job(job_id, status="running")
        checkpoint = _checkpoint()
        raw = image_path.read_bytes()
        input_sha256 = hashlib.sha256(raw).hexdigest()
        inference_input, input_metadata = _prepare_input(image_path, root, channel=channel, time=time, z=z, field=field)
        result = predict(inference_input, checkpoint, output, device="cpu")
        result.update({
            "analysis_profile": algorithm_profile,
            "scientific_execution": True,
            "input_sha256": input_sha256,
            "source_filename": original_name,
            "input_metadata": input_metadata,
        })
        (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
        (output / "community_input.json").write_text(json.dumps({
            "source_filename": original_name,
            "source_sha256": input_sha256,
            **input_metadata,
        }, indent=2) + "\n")
        metadata = {
            "original_filename": original_name,
            "algorithm_profile": algorithm_profile,
            "checkpoint_configured": True,
            "input_metadata": input_metadata,
        }
        if research_consent:
            _save_research_copy(job_id, image_path, input_sha256, metadata)
        _archive(job_id)
        expiry = _now() + timedelta(days=DEFAULT_RESEARCH_RETENTION_DAYS if research_consent else 1)
        _set_job(
            job_id,
            status="completed",
            expires_at=expiry.isoformat(),
            input_sha256=input_sha256,
            input_name=original_name,
            result_json=json.dumps(result),
            retained_copy=int(research_consent),
        )
    except Exception as exc:  # noqa: BLE001 - worker must preserve failure state
        _set_job(job_id, status="failed", error=f"{type(exc).__name__}: {exc}")
    finally:
        image_path.unlink(missing_ok=True)
        (root / "input_plane.tif").unlink(missing_ok=True)


def create_job(data: bytes, original_name: str, research_consent: bool, algorithm_profile: str, *, channel: int = 0, time: int = 0, z: int = 0, field: int = 0) -> str:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Upload exceeds {MAX_UPLOAD_BYTES} bytes")
    if algorithm_profile not in {"auto", "nucleus-segmentation"}:
        raise ValueError("Unsupported analysis profile")
    suffix = ".nd2" if original_name.lower().endswith(".nd2") else ".tif"
    if channel < 0 or time < 0 or z < 0 or field < 0:
        raise ValueError("ND2 indices must be non-negative")
    job_id = uuid.uuid4().hex
    root = _job_dir(job_id)
    root.mkdir(parents=True, exist_ok=True)
    input_path = root / f"input{suffix}"
    input_path.write_bytes(data)
    expires = _now() + timedelta(hours=DEFAULT_RESULT_RETENTION_HOURS)
    with DB_LOCK, _db() as conn:
        conn.execute(
            "INSERT INTO jobs(id,status,created_at,updated_at,expires_at,input_name,retained_copy,research_consent,algorithm_profile) VALUES(?,?,?,?,?,?,?,?,?)",
            (job_id, "queued", _now().isoformat(), _now().isoformat(), expires.isoformat(), original_name, 0, int(research_consent), algorithm_profile),
        )
        conn.commit()
    threading.Thread(target=_run, args=(job_id, input_path, original_name, research_consent, algorithm_profile), kwargs={"channel": channel, "time": time, "z": z, "field": field}, daemon=True).start()
    return job_id


def serialize(row: sqlite3.Row) -> dict[str, object]:
    result = json.loads(row["result_json"]) if row["result_json"] else None
    return {
        "job_id": row["id"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "expires_at": row["expires_at"],
        "input_name": row["input_name"],
        "input_sha256": row["input_sha256"],
        "research_consent": bool(row["research_consent"]),
        "retained_copy": bool(row["retained_copy"]),
        "algorithm_profile": row["algorithm_profile"],
        "result": result,
        "error": row["error"],
        "downloads": {
            "zip": f"/jobs/{row['id']}/download",
            "results": f"/jobs/{row['id']}/files/results.json",
        } if row["status"] == "completed" else {},
    }


def get_job(job_id: str) -> dict[str, object] | None:
    row = _get_job(job_id)
    return serialize(row) if row else None


def get_file(job_id: str, filename: str) -> Path:
    allowed = {"segmentation_mask.tif", "overlay.tif", "measurements.csv", "results.json", "provenance.json", "community_input.json"}
    if filename not in allowed:
        raise ValueError("File is not a downloadable BioNuclei result")
    row = _get_job(job_id)
    if not row or row["status"] != "completed":
        raise FileNotFoundError(job_id)
    path = _job_dir(job_id) / "results" / filename
    if not path.is_file():
        raise FileNotFoundError(filename)
    return path


def get_archive(job_id: str) -> Path:
    row = _get_job(job_id)
    if not row or row["status"] != "completed":
        raise FileNotFoundError(job_id)
    return _archive(job_id)


def purge_expired() -> int:
    removed = 0
    now = _now()
    with DB_LOCK, _db() as conn:
        rows = conn.execute("SELECT id FROM jobs WHERE expires_at < ?", (now.isoformat(),)).fetchall()
        for row in rows:
            shutil.rmtree(_job_dir(row["id"]), ignore_errors=True)
            (JOB_ROOT / f"{row['id']}.zip").unlink(missing_ok=True)
            conn.execute("DELETE FROM jobs WHERE id = ?", (row["id"],))
            removed += 1
        conn.commit()
    return removed
