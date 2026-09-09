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
    shutil.copy2(input_path, destination / "input.tif")
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


def _run(job_id: str, image_path: Path, original_name: str, research_consent: bool, algorithm_profile: str) -> None:
    root = _job_dir(job_id)
    output = root / "results"
    try:
        _set_job(job_id, status="running")
        checkpoint = _checkpoint()
        raw = image_path.read_bytes()
        input_sha256 = hashlib.sha256(raw).hexdigest()
        result = predict(image_path, checkpoint, output, device="cpu")
        result.update({
            "analysis_profile": algorithm_profile,
            "scientific_execution": True,
            "input_sha256": input_sha256,
        })
        (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
        metadata = {
            "original_filename": original_name,
            "algorithm_profile": algorithm_profile,
            "checkpoint_configured": True,
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


def create_job(data: bytes, original_name: str, research_consent: bool, algorithm_profile: str) -> str:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Upload exceeds {MAX_UPLOAD_BYTES} bytes")
    if algorithm_profile not in {"auto", "nucleus-segmentation"}:
        raise ValueError("Unsupported analysis profile")
    job_id = uuid.uuid4().hex
    root = _job_dir(job_id)
    root.mkdir(parents=True, exist_ok=True)
    input_path = root / "input.tif"
    input_path.write_bytes(data)
    expires = _now() + timedelta(hours=DEFAULT_RESULT_RETENTION_HOURS)
    with DB_LOCK, _db() as conn:
        conn.execute(
            "INSERT INTO jobs(id,status,created_at,updated_at,expires_at,input_name,retained_copy,research_consent,algorithm_profile) VALUES(?,?,?,?,?,?,?,?,?)",
            (job_id, "queued", _now().isoformat(), _now().isoformat(), expires.isoformat(), original_name, 0, int(research_consent), algorithm_profile),
        )
        conn.commit()
    threading.Thread(target=_run, args=(job_id, input_path, original_name, research_consent, algorithm_profile), daemon=True).start()
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
    allowed = {"segmentation_mask.tif", "overlay.tif", "measurements.csv", "results.json", "provenance.json"}
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
    path = _archive(job_id)
    return path


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
