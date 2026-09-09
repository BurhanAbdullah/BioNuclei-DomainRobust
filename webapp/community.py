"""Public community-analysis job service for BioNuclei.

This module orchestrates the existing deterministic inference/measurement code.
Account ownership is explicit. User-image retention is explicit opt-in.
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
import pandas as pd
import tifffile

from bionuclei.inference import predict
from .app import _checkpoint

JOB_ROOT = Path(os.getenv("BIONUCLEI_JOB_DIR", "/tmp/bionuclei-community-jobs")).expanduser()
DB_PATH = JOB_ROOT / "jobs.sqlite3"
JOB_ROOT.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = int(os.getenv("BIONUCLEI_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
DEFAULT_RESULT_RETENTION_HOURS = int(os.getenv("BIONUCLEI_RESULT_RETENTION_HOURS", "24"))
DEFAULT_RESEARCH_RETENTION_DAYS = int(os.getenv("BIONUCLEI_RESEARCH_RETENTION_DAYS", "90"))
ENABLED_MODULES = {"nuclei", "morphology", "intensity"}
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
            user_id TEXT,
            input_sha256 TEXT,
            input_name TEXT,
            retained_copy INTEGER NOT NULL DEFAULT 0,
            research_consent INTEGER NOT NULL DEFAULT 0,
            algorithm_profile TEXT NOT NULL,
            analysis_modules TEXT NOT NULL DEFAULT 'nuclei,morphology,intensity',
            result_json TEXT,
            error TEXT
        )"""
    )
    columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    if "user_id" not in columns:
        conn.execute("ALTER TABLE jobs ADD COLUMN user_id TEXT")
    if "analysis_modules" not in columns:
        conn.execute("ALTER TABLE jobs ADD COLUMN analysis_modules TEXT NOT NULL DEFAULT 'nuclei,morphology,intensity'")
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


def _get_job(job_id: str, user_id: str | None = None) -> sqlite3.Row | None:
    with DB_LOCK, _db() as conn:
        if user_id is None:
            return conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return conn.execute("SELECT * FROM jobs WHERE id = ? AND user_id = ?", (job_id, user_id)).fetchone()


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
    shutil.copy2(input_path, destination / f"input{input_path.suffix}")
    (destination / "contribution.json").write_text(
        json.dumps(
            {
                "job_id": job_id,
                "input_sha256": input_sha256,
                "created_at": _now().isoformat(),
                "retention_days": DEFAULT_RESEARCH_RETENTION_DAYS,
                "research_consent": True,
                "purpose": "Optional research contribution for future BioNuclei development and model-training datasets.",
                "metadata": metadata,
            },
            indent=2,
        )
        + "\n"
    )


def delete_research_copy(job_id: str, user_id: str) -> bool:
    row = _get_job(job_id, user_id)
    if row is None:
        raise FileNotFoundError(job_id)
    destination = JOB_ROOT / "research_contributions" / job_id
    if not destination.exists():
        return False
    shutil.rmtree(destination, ignore_errors=True)
    _set_job(job_id, retained_copy=0, research_consent=0)
    return True


def _nd2_to_tiff(source: Path, destination: Path, *, channel: int = 0, time: int = 0, z: int = 0, field: int = 0) -> dict[str, object]:
    """Read a Nikon ND2 and deterministically extract one 2-D YX plane."""
    try:
        import nd2
    except ImportError as exc:
        raise RuntimeError("ND2 support requires the optional 'nd2' package") from exc
    with nd2.ND2File(source) as ndfile:
        sizes = dict(ndfile.sizes)
        shape = tuple(ndfile.shape)
        axes = list(sizes.keys())
        if "Y" not in sizes or "X" not in sizes:
            raise ValueError(f"ND2 file has no Y/X image plane: sizes={sizes}")
        requested = {"C": channel, "T": time, "Z": z, "P": field, "S": 0, "V": field}
        indexers: list[int | slice] = []
        selected: dict[str, int] = {}
        for axis in axes:
            if axis in {"Y", "X"}:
                indexers.append(slice(None))
                continue
            size = int(sizes[axis])
            value = int(requested.get(axis, 0))
            if value < 0 or value >= size:
                raise ValueError(f"ND2 axis {axis} index {value} outside [0, {size - 1}]")
            indexers.append(value)
            selected[axis] = value
        arr = np.asarray(ndfile.asarray())
        plane = np.squeeze(arr[tuple(indexers)])
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
    if image_path.suffix.lower() != ".nd2":
        return image_path, {"input_format": "TIFF", "conversion": None}
    destination = root / "input_plane.tif"
    return destination, _nd2_to_tiff(image_path, destination, channel=channel, time=time, z=z, field=field)


def _extended_reports(inference_input: Path, output: Path, modules: set[str]) -> dict[str, object]:
    mask_path = output / "segmentation_mask.tif"
    if not mask_path.is_file():
        raise FileNotFoundError("segmentation_mask.tif was not produced by the scientific pipeline")
    mask = np.asarray(tifffile.imread(mask_path))
    image = np.asarray(tifffile.imread(inference_input))
    if mask.shape != image.shape:
        raise ValueError(f"Image and predicted mask shapes differ: {image.shape} != {mask.shape}")
    from skimage.measure import regionprops_table

    properties = ["label", "area", "centroid", "bbox"]
    if "morphology" in modules:
        properties += ["perimeter", "eccentricity", "solidity", "major_axis_length", "minor_axis_length"]
    if "intensity" in modules:
        properties += ["mean_intensity", "max_intensity", "min_intensity"]
    table = regionprops_table(mask.astype(np.int32), intensity_image=image, properties=tuple(properties))
    frame = pd.DataFrame(table)
    if "morphology" in modules and not frame.empty:
        frame["circularity"] = np.where(frame["perimeter"] > 0, 4.0 * np.pi * frame["area"] / (frame["perimeter"] ** 2), np.nan)
    frame.to_csv(output / "nuclei_analysis.csv", index=False)

    nuclei_count = int(len(frame))
    summary: dict[str, object] = {"nuclei_count": nuclei_count, "modules": sorted(modules), "measurement_file": "nuclei_analysis.csv"}
    if "morphology" in modules:
        summary["morphology"] = {
            "mean_area": float(frame["area"].mean()) if nuclei_count else None,
            "median_area": float(frame["area"].median()) if nuclei_count else None,
            "mean_perimeter": float(frame["perimeter"].mean()) if nuclei_count else None,
            "mean_eccentricity": float(frame["eccentricity"].mean()) if nuclei_count else None,
            "mean_solidity": float(frame["solidity"].mean()) if nuclei_count else None,
            "mean_circularity": float(frame["circularity"].mean()) if nuclei_count else None,
        }
        (output / "morphology_report.json").write_text(json.dumps(summary["morphology"], indent=2) + "\n")
    if "intensity" in modules:
        summary["intensity"] = {
            "mean_nuclear_intensity": float(frame["mean_intensity"].mean()) if nuclei_count else None,
            "median_nuclear_intensity": float(frame["mean_intensity"].median()) if nuclei_count else None,
            "mean_max_intensity": float(frame["max_intensity"].mean()) if nuclei_count else None,
        }
        (output / "intensity_report.json").write_text(json.dumps(summary["intensity"], indent=2) + "\n")
    (output / "nuclei_report.json").write_text(json.dumps({"nuclei_count": nuclei_count, "modules": sorted(modules)}, indent=2) + "\n")
    return summary


def _run(job_id: str, user_id: str, image_path: Path, original_name: str, research_consent: bool, algorithm_profile: str, analysis_modules: set[str], *, channel: int, time: int, z: int, field: int) -> None:
    root = _job_dir(job_id)
    output = root / "results"
    try:
        _set_job(job_id, status="running")
        checkpoint = _checkpoint()
        raw = image_path.read_bytes()
        input_sha256 = hashlib.sha256(raw).hexdigest()
        inference_input, input_metadata = _prepare_input(image_path, root, channel=channel, time=time, z=z, field=field)
        result = predict(inference_input, checkpoint, output, device="cpu")
        report_summary = _extended_reports(inference_input, output, analysis_modules)
        result.update({
            "analysis_profile": algorithm_profile,
            "analysis_modules": sorted(analysis_modules),
            "scientific_execution": True,
            "input_sha256": input_sha256,
            "source_filename": original_name,
            "input_metadata": input_metadata,
            "reports": report_summary,
        })
        (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
        (output / "community_input.json").write_text(json.dumps({"source_filename": original_name, "source_sha256": input_sha256, **input_metadata}, indent=2) + "\n")
        metadata = {"original_filename": original_name, "algorithm_profile": algorithm_profile, "analysis_modules": sorted(analysis_modules), "checkpoint_configured": True, "input_metadata": input_metadata}
        if research_consent:
            _save_research_copy(job_id, image_path, input_sha256, metadata)
        _archive(job_id)
        expiry = _now() + timedelta(days=DEFAULT_RESEARCH_RETENTION_DAYS if research_consent else 1)
        _set_job(job_id, status="completed", expires_at=expiry.isoformat(), input_sha256=input_sha256, input_name=original_name, result_json=json.dumps(result), retained_copy=int(research_consent))
    except Exception as exc:
        _set_job(job_id, status="failed", error=f"{type(exc).__name__}: {exc}")
    finally:
        image_path.unlink(missing_ok=True)
        (root / "input_plane.tif").unlink(missing_ok=True)


def create_job(data: bytes, original_name: str, user_id: str, research_consent: bool, algorithm_profile: str, analysis_modules: list[str] | None = None, *, channel: int = 0, time: int = 0, z: int = 0, field: int = 0) -> str:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Upload exceeds {MAX_UPLOAD_BYTES} bytes")
    if algorithm_profile not in {"auto", "nucleus-segmentation"}:
        raise ValueError("Unsupported analysis profile")
    modules = set(analysis_modules or ["nuclei", "morphology", "intensity"])
    modules.add("nuclei")
    unknown = modules - ENABLED_MODULES
    if unknown:
        raise ValueError(f"Unsupported analysis modules: {', '.join(sorted(unknown))}")
    if any(value < 0 for value in (channel, time, z, field)):
        raise ValueError("ND2 indices must be non-negative")
    suffix = ".nd2" if original_name.lower().endswith(".nd2") else ".tif"
    job_id = uuid.uuid4().hex
    root = _job_dir(job_id)
    root.mkdir(parents=True, exist_ok=True)
    input_path = root / f"input{suffix}"
    input_path.write_bytes(data)
    expires = _now() + timedelta(hours=DEFAULT_RESULT_RETENTION_HOURS)
    with DB_LOCK, _db() as conn:
        conn.execute("INSERT INTO jobs(id,status,created_at,updated_at,expires_at,user_id,input_name,retained_copy,research_consent,algorithm_profile,analysis_modules) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (job_id, "queued", _now().isoformat(), _now().isoformat(), expires.isoformat(), user_id, original_name, 0, int(research_consent), algorithm_profile, ",".join(sorted(modules))))
        conn.commit()
    threading.Thread(target=_run, args=(job_id, user_id, input_path, original_name, research_consent, algorithm_profile, modules), kwargs={"channel": channel, "time": time, "z": z, "field": field}, daemon=True).start()
    return job_id


def serialize(row: sqlite3.Row) -> dict[str, object]:
    result = json.loads(row["result_json"]) if row["result_json"] else None
    return {"job_id": row["id"], "status": row["status"], "created_at": row["created_at"], "updated_at": row["updated_at"], "expires_at": row["expires_at"], "input_name": row["input_name"], "input_sha256": row["input_sha256"], "research_consent": bool(row["research_consent"]), "retained_copy": bool(row["retained_copy"]), "algorithm_profile": row["algorithm_profile"], "analysis_modules": row["analysis_modules"].split(",") if row["analysis_modules"] else [], "result": result, "error": row["error"], "downloads": {"zip": f"/jobs/{row['id']}/download", "results": f"/jobs/{row['id']}/files/results.json"} if row["status"] == "completed" else {}}


def get_job(job_id: str, user_id: str) -> dict[str, object] | None:
    row = _get_job(job_id, user_id)
    return serialize(row) if row else None


def get_jobs_for_user(user_id: str) -> list[dict[str, object]]:
    with DB_LOCK, _db() as conn:
        rows = conn.execute("SELECT * FROM jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT 50", (user_id,)).fetchall()
    return [serialize(row) for row in rows]


def get_file(job_id: str, user_id: str, filename: str) -> Path:
    allowed = {"segmentation_mask.tif", "overlay.tif", "measurements.csv", "results.json", "provenance.json", "community_input.json", "nuclei_analysis.csv", "nuclei_report.json", "morphology_report.json", "intensity_report.json"}
    if filename not in allowed:
        raise ValueError("File is not a downloadable BioNuclei result")
    row = _get_job(job_id, user_id)
    if not row or row["status"] != "completed":
        raise FileNotFoundError(job_id)
    path = _job_dir(job_id) / "results" / filename
    if not path.is_file():
        raise FileNotFoundError(filename)
    return path


def get_archive(job_id: str, user_id: str) -> Path:
    row = _get_job(job_id, user_id)
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
