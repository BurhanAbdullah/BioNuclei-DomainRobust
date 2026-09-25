"""BioNuclei production analyzer on Modal.

Architecture:
  GitHub Pages -> this FastAPI control plane -> Modal Function -> GPU inference.

Job metadata is stored in a durable Modal Dict; transient inputs/results live on
an attached Volume and are deleted after the configured retention period. The
browser never receives a service credential. Supabase Auth remains the account
identity provider and guest sessions remain ephemeral bearer tokens.

Deploy:
  modal deploy modal_app.py

Before deployment create a Modal Secret named ``bionuclei-supabase`` containing:
  SUPABASE_URL=...
  SUPABASE_PUBLISHABLE_KEY=...
"""
from __future__ import annotations

import base64
import gc
import hashlib
import json
import os
import shutil
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import modal

# These must be set before importing webapp.community because that module reads
# the job directory and upload limits at import time.
os.environ.setdefault("BIONUCLEI_JOB_DIR", "/data/bionuclei-community-jobs")
os.environ.setdefault("BIONUCLEI_MAX_UPLOAD_BYTES", str(64 * 1024 * 1024))
os.environ.setdefault("BIONUCLEI_RESULT_RETENTION_HOURS", "1")

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from webapp import community as community_service
from webapp.auth import authenticate_optional, create_guest_token
from webapp.app import _checkpoint, _png_data_url

APP_NAME = "bionuclei-production-analyzer"
CHECKPOINT_URL = os.getenv(
    "BIONUCLEI_CHECKPOINT_URL",
    "https://github.com/BurhanAbdullah/BioNuclei-DomainRobust/releases/download/checkpoint-bbbc039-v1/bionuclei_bbbc039.pt",
)
CHECKPOINT_SHA256 = os.getenv(
    "BIONUCLEI_CHECKPOINT_SHA256",
    "7209a6990514380804210292ac208b0f3b0b0a054338a145e1916044762d7c92",
)
DATA_ROOT = Path("/data/bionuclei-community-jobs")
VOLUME = modal.Volume.from_name("bionuclei-analyzer-data", create_if_missing=True)
JOBS = modal.Dict.from_name("bionuclei-analyzer-jobs", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("curl")
    .pip_install(
        "numpy>=1.24",
        "scipy>=1.10",
        "pandas>=2.0",
        "scikit-image>=0.21",
        "scikit-learn>=1.3",
        "tifffile>=2023.7.10",
        "torch>=2.1",
        "torchvision>=0.16",
        "pyyaml>=6.0",
        "tqdm>=4.66",
        "fastapi>=0.115",
        "python-multipart>=0.0.9",
        "pillow>=10.0",
        "nd2>=0.11,<0.12",
        "reportlab>=4.2",
    )
    .add_local_dir("src", "/app/src")
    .add_local_dir("webapp", "/app/webapp")
    .add_local_dir("configs", "/app/configs")
    .add_local_file("README.md", "/app/README.md")
    .run_commands(
        f"mkdir -p /opt/models && curl -fsSL '{CHECKPOINT_URL}' -o /opt/models/bionuclei_bbbc039.pt && echo '{CHECKPOINT_SHA256}  /opt/models/bionuclei_bbbc039.pt' | sha256sum -c -",
    )
    .env(
        {
            "PYTHONPATH": "/app",
            "BIONUCLEI_CHECKPOINT": "/opt/models/bionuclei_bbbc039.pt",
            "BIONUCLEI_CHECKPOINT_SHA256": CHECKPOINT_SHA256,
            "BIONUCLEI_JOB_DIR": str(DATA_ROOT),
            "BIONUCLEI_RESULT_RETENTION_HOURS": "1",
        }
    )
)

app = modal.App(APP_NAME)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _meta(job_id: str) -> dict:
    value = JOBS.get(job_id)
    return dict(value) if value else {}


def _set_meta(job_id: str, **fields: object) -> None:
    current = _meta(job_id)
    current.update(fields)
    current["updated_at"] = _now().isoformat()
    JOBS.put(job_id, current)


def _root(job_id: str) -> Path:
    return DATA_ROOT / job_id


def _safe_filename(filename: str) -> str:
    allowed = {
        "results.json",
        "analysis_report.html",
        "analysis_report.json",
        "analysis_report.pdf",
        "nuclei_analysis.csv",
        "nuclei_report.json",
        "morphology_report.json",
        "intensity_report.json",
        "expert_agents.json",
        "adaptive_plan.json",
        "overlay.tif",
        "segmentation_mask.tif",
    }
    if filename not in allowed:
        raise HTTPException(status_code=404, detail="Unsupported result file")
    return filename


def _archive_without_input(job_id: str) -> Path:
    root = _root(job_id)
    archive = DATA_ROOT / f"{job_id}.zip"
    excluded = {"input.tif", "input.tiff", "input.nd2", "input_plane.tif"}
    with ZipFile(archive, "w", ZIP_DEFLATED) as zf:
        for path in root.rglob("*"):
            if path.is_file() and path.name not in excluded:
                zf.write(path, path.relative_to(root))
    return archive


def _cleanup(job_id: str, *, keep_metadata: bool = True) -> None:
    shutil.rmtree(_root(job_id), ignore_errors=True)
    (DATA_ROOT / f"{job_id}.zip").unlink(missing_ok=True)
    if keep_metadata:
        _set_meta(job_id, input_deleted=True, results_deleted=True)
    else:
        JOBS.pop(job_id, None)
    VOLUME.commit()


@app.function(
    image=image,
    gpu="L4",
    cpu=4,
    memory=16384,
    timeout=1800,
    retries=1,
    max_containers=2,
    volumes={"/data": VOLUME},
)
def analyze_worker(
    job_id: str,
    user_id: str,
    original_name: str,
    algorithm_profile: str,
    analysis_modules: list[str],
    channel: int,
    time_index: int,
    z: int,
    field: int,
) -> None:
    """Run the complete scientific pipeline in an isolated GPU worker."""
    VOLUME.reload()
    root = _root(job_id)
    output = root / "results"
    input_candidates = [root / "input.tif", root / "input.tiff", root / "input.nd2"]
    image_path = next((p for p in input_candidates if p.is_file()), None)
    if image_path is None:
        _set_meta(job_id, status="failed", error="Transient input was not available to the worker.")
        return

    try:
        _set_meta(job_id, status="planning", phase="planning")
        checkpoint = _checkpoint()
        raw = image_path.read_bytes()
        input_sha256 = hashlib.sha256(raw).hexdigest()
        inference_input, input_metadata = community_service._prepare_input(
            image_path,
            root,
            channel=channel,
            time=time_index,
            z=z,
            field=field,
        )
        modules = set(analysis_modules)
        plan = community_service.build_plan(inference_input, modules)
        output.mkdir(parents=True, exist_ok=True)
        (output / "adaptive_plan.json").write_text(
            json.dumps(community_service.to_dict(plan), indent=2) + "\n",
            encoding="utf-8",
        )
        if plan.status == "BLOCKED":
            raise ValueError("Adaptive input-quality gate blocked inference: " + "; ".join(plan.warnings))

        _set_meta(job_id, status="running", phase="running")
        with community_service.INFERENCE_LOCK:
            result = community_service.predict(inference_input, checkpoint, output, device="cuda")
            gc.collect()

        _set_meta(job_id, status="measuring", phase="measuring")
        report_summary = community_service._extended_reports(inference_input, output, modules)
        result.update(
            {
                "analysis_profile": algorithm_profile,
                "analysis_modules": sorted(modules),
                "scientific_execution": True,
                "input_sha256": input_sha256,
                "source_filename": original_name,
                "input_metadata": input_metadata,
                "reports": report_summary,
                "adaptive_plan": community_service.to_dict(plan),
                "model": {
                    "architecture": "Boundary U-Net",
                    "prediction_target": ["background", "nuclear interior", "nuclear boundary"],
                    "training_reference": "BBBC039v1",
                    "weights_updated_during_analysis": False,
                    "checkpoint_sha256": CHECKPOINT_SHA256,
                },
            }
        )

        _set_meta(job_id, status="expert_review", phase="expert_review")
        expert = community_service.run_expert_agents(result)
        result["expert_agents"] = expert
        (output / "expert_agents.json").write_text(json.dumps(expert, indent=2) + "\n", encoding="utf-8")
        (output / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        (output / "community_input.json").write_text(
            json.dumps({"source_filename": original_name, "source_sha256": input_sha256, **input_metadata}, indent=2) + "\n",
            encoding="utf-8",
        )

        _set_meta(job_id, status="packaging", phase="packaging")
        community_service.build_report(result, output)
        archive = _archive_without_input(job_id)
        expiry = _now() + timedelta(hours=1)
        _set_meta(
            job_id,
            status="completed",
            phase="completed",
            expires_at=expiry.isoformat(),
            input_sha256=input_sha256,
            input_name=original_name,
            result=result,
            archive=archive.name,
            report_ready=True,
            input_deleted=True,
        )
        # Delete the source image before committing the result state. The report
        # archive was explicitly built without any input image.
        image_path.unlink(missing_ok=True)
        (root / "input_plane.tif").unlink(missing_ok=True)
        VOLUME.commit()
    except Exception as exc:
        print(f"BioNuclei Modal job {job_id} failed: {type(exc).__name__}: {exc}", flush=True)
        shutil.rmtree(root, ignore_errors=True)
        (DATA_ROOT / f"{job_id}.zip").unlink(missing_ok=True)
        _set_meta(
            job_id,
            status="failed",
            phase="failed",
            error="Analysis worker failed before producing a complete result. Please retry the analysis.",
            input_deleted=True,
            results_deleted=True,
        )
        VOLUME.commit()


@app.function(
    image=image,
    schedule=modal.Period(hours=1),
    volumes={"/data": VOLUME},
)
def cleanup_expired() -> None:
    """Delete expired transient result bundles and their metadata."""
    VOLUME.reload()
    now = _now()
    for job_id, raw in list(JOBS.items()):
        meta = dict(raw or {})
        expires = meta.get("expires_at")
        if not expires:
            continue
        try:
            expired = datetime.fromisoformat(str(expires)) <= now
        except ValueError:
            expired = True
        if expired:
            shutil.rmtree(_root(str(job_id)), ignore_errors=True)
            (DATA_ROOT / f"{job_id}.zip").unlink(missing_ok=True)
            JOBS.pop(job_id, None)
    VOLUME.commit()


api = FastAPI(
    title="BioNuclei Production Analyzer",
    version="1.0.0-modal",
    description="Transient scientific bioimaging analysis with asynchronous GPU execution.",
)
api.add_middleware(
    CORSMiddleware,
    allow_origins=["https://burhanabdullah.github.io"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


def _require_user(request: Request):
    return authenticate_optional(request)


@api.get("/")
def root():
    return {
        "service": "bionuclei-production-analyzer",
        "version": "1.0.0-modal",
        "status": "online",
        "health": "/health",
        "algorithms": "/algorithms",
        "execution": "Modal asynchronous GPU worker",
        "authentication": "Supabase account sessions or ephemeral guest tokens",
        "input_retention": "transient; deleted after ingestion/processing",
        "result_retention_hours": 1,
    }


@api.get("/health")
def health():
    try:
        checkpoint_ok = _checkpoint().is_file()
    except Exception:
        checkpoint_ok = False
    return {
        "status": "ok" if checkpoint_ok else "degraded",
        "service": "bionuclei-production-analyzer",
        "scientific_engine": "bionuclei-domainrobust",
        "checkpoint_configured": checkpoint_ok,
        "checkpoint_sha256": CHECKPOINT_SHA256 if checkpoint_ok else None,
        "gpu_worker": "L4",
        "max_upload_bytes": 64 * 1024 * 1024,
        "supported_input_formats": [".tif", ".tiff", ".nd2"],
        "guest_access": True,
        "input_retention": "transient",
        "result_retention_hours": 1,
    }


@api.get("/algorithms")
def algorithms():
    return {
        "default": "auto",
        "reports_available": [
            {"id": "nuclei", "name": "Nuclei", "status": "available"},
            {"id": "morphology", "name": "Morphology", "status": "available"},
            {"id": "intensity", "name": "Intensity", "status": "available"},
        ],
    }


@api.post("/guest-session")
def guest_session():
    return {"guest_token": create_guest_token(), "mode": "guest", "persisted": False}


@api.post("/analyze")
async def analyze(
    request: Request,
    image: UploadFile = File(...),
    research_consent: bool = Form(False),
    algorithm_profile: str = Form("auto"),
    analysis_modules: str = Form("nuclei,morphology,intensity"),
    nd2_channel: int = Form(0),
    nd2_time: int = Form(0),
    nd2_z: int = Form(0),
    nd2_field: int = Form(0),
):
    user = _require_user(request)
    data = await image.read((64 * 1024 * 1024) + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")
    if len(data) > 64 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Upload exceeds 64 MiB")
    suffix = Path(image.filename or "").suffix.lower()
    if suffix not in {".tif", ".tiff", ".nd2"}:
        raise HTTPException(status_code=400, detail="Unsupported image format")
    modules = {x.strip().lower() for x in analysis_modules.split(",") if x.strip()}
    modules.add("nuclei")
    if modules - {"nuclei", "morphology", "intensity"}:
        raise HTTPException(status_code=400, detail="Unsupported analysis module")
    if algorithm_profile not in {"auto", "nucleus-segmentation"}:
        raise HTTPException(status_code=400, detail="Unsupported analysis profile")
    if min(nd2_channel, nd2_time, nd2_z, nd2_field) < 0:
        raise HTTPException(status_code=400, detail="ND2 indices must be non-negative")

    job_id = uuid.uuid4().hex
    root_path = _root(job_id)
    root_path.mkdir(parents=True, exist_ok=True)
    input_path = root_path / f"input{suffix}"
    input_path.write_bytes(data)
    now = _now()
    _set_meta(
        job_id,
        status="queued",
        phase="queued",
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
        expires_at=(now + timedelta(hours=1)).isoformat(),
        user_id=user.id,
        input_name=image.filename or "uploaded-image.tif",
        input_sha256=hashlib.sha256(data).hexdigest(),
        analysis_profile=algorithm_profile,
        analysis_modules=sorted(modules),
        research_consent=False,
        input_deleted=False,
        results_deleted=False,
    )
    VOLUME.commit()
    analyze_worker.spawn(
        job_id,
        user.id,
        image.filename or "uploaded-image.tif",
        algorithm_profile,
        sorted(modules),
        nd2_channel,
        nd2_time,
        nd2_z,
        nd2_field,
    )
    return {
        "job_id": job_id,
        "status": "queued",
        "poll": f"/jobs/{job_id}",
        "progress": f"/jobs/{job_id}/progress",
        "account": user.email or ("guest" if user.guest else user.id),
        "guest": user.guest,
        "research_consent": False,
        "analysis_modules": sorted(modules),
    }


@api.get("/jobs/{job_id}")
def job(request: Request, job_id: str):
    user = _require_user(request)
    meta = _meta(job_id)
    if not meta or meta.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    payload = dict(meta)
    payload.pop("user_id", None)
    return payload


@api.get("/jobs/{job_id}/progress")
def progress(request: Request, job_id: str):
    user = _require_user(request)
    meta = _meta(job_id)
    if not meta or meta.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    return {
        "job_id": job_id,
        "status": meta.get("status", "queued"),
        "phase": meta.get("phase", "queued"),
        "label": {
            "queued": "1 · Analysis started",
            "planning": "2 · Quality & planning",
            "running": "3 · Boundary U-Net inference",
            "measuring": "4 · Instance measurements",
            "expert_review": "5 · Expert evidence review",
            "packaging": "6 · Report packaging",
            "completed": "7 · Complete",
            "failed": "Analysis failed",
        }.get(meta.get("phase"), "Analysis started"),
        "message": meta.get("error") or "Analysis is progressing in the Modal worker.",
        "progress": {
            "queued": 12,
            "planning": 24,
            "running": 52,
            "measuring": 68,
            "expert_review": 84,
            "packaging": 94,
            "completed": 100,
            "failed": 0,
        }.get(meta.get("phase"), 12),
        "expert_agents_started": meta.get("phase") in {"expert_review", "packaging", "completed"},
        "report_ready": bool(meta.get("report_ready")),
    }


@api.get("/jobs/{job_id}/preview/{filename}")
def preview(request: Request, job_id: str, filename: str):
    if filename not in {"overlay.tif", "segmentation_mask.tif"}:
        raise HTTPException(status_code=404, detail="Unsupported preview file")
    user = _require_user(request)
    meta = _meta(job_id)
    if not meta or meta.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    VOLUME.reload()
    try:
        data_url = _png_data_url(_root(job_id) / "results" / filename)
        return Response(
            content=base64.b64decode(data_url.split(",", 1)[1]),
            media_type="image/png",
            headers={"Cache-Control": "no-store"},
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api.get("/jobs/{job_id}/download")
def download(request: Request, job_id: str):
    user = _require_user(request)
    meta = _meta(job_id)
    if not meta or meta.get("user_id") != user.id or not meta.get("archive"):
        raise HTTPException(status_code=404, detail="Analysis package not found")
    VOLUME.reload()
    archive = DATA_ROOT / str(meta["archive"])
    if not archive.is_file():
        raise HTTPException(status_code=404, detail="Analysis package expired")
    return FileResponse(archive, media_type="application/zip", filename=f"bionuclei-{job_id}.zip", headers={"Cache-Control": "no-store"})


@api.get("/jobs/{job_id}/files/{filename}")
def result_file(request: Request, job_id: str, filename: str):
    filename = _safe_filename(filename)
    user = _require_user(request)
    meta = _meta(job_id)
    if not meta or meta.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    VOLUME.reload()
    path = _root(job_id) / "results" / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Result file not found")
    media = "application/json" if filename.endswith(".json") else "text/csv" if filename.endswith(".csv") else "application/pdf" if filename.endswith(".pdf") else "text/html" if filename.endswith(".html") else "image/tiff"
    return FileResponse(path, media_type=media, filename=filename, headers={"Cache-Control": "no-store"})


@api.delete("/jobs/{job_id}")
def remove_job(request: Request, job_id: str):
    user = _require_user(request)
    meta = _meta(job_id)
    if not meta or meta.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    _cleanup(job_id, keep_metadata=False)
    return {"job_id": job_id, "deleted": True}


@app.function(image=image, secrets=[modal.Secret.from_name("bionuclei-supabase")], volumes={"/data": VOLUME})
@modal.asgi_app()
def web():
    return api
