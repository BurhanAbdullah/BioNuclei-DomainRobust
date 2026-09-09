"""Standalone public BioNuclei Community Analyzer service."""
from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .community import MAX_UPLOAD_BYTES, create_job, get_archive, get_file, get_job, purge_expired
from .app import _checkpoint

app = FastAPI(
    title="BioNuclei Community Analyzer",
    version="0.1.0",
    description="Asynchronous public analysis service for the validated BioNuclei segmentation pipeline.",
)


@app.get("/health")
def health() -> dict[str, object]:
    try:
        checkpoint = _checkpoint()
        checkpoint_available = checkpoint.is_file()
    except Exception:
        checkpoint_available = False
    return {
        "status": "ok" if checkpoint_available else "degraded",
        "service": "bionuclei-community-analyzer",
        "checkpoint_available": checkpoint_available,
        "max_upload_bytes": MAX_UPLOAD_BYTES,
    }


@app.get("/algorithms")
def algorithms() -> dict[str, object]:
    return {
        "default": "auto",
        "algorithms": [
            {
                "id": "auto",
                "name": "BioNuclei validated pipeline",
                "status": "available",
                "description": "Uses the configured validated Boundary U-Net and deterministic instance post-processing.",
            },
            {
                "id": "nucleus-segmentation",
                "name": "Nuclear instance segmentation",
                "status": "available",
                "description": "Same validated scientific pipeline with the task declared explicitly.",
            },
        ],
        "not_enabled": "Other algorithms are not exposed until they are installed, tested and scientifically validated in this repository.",
    }


@app.post("/analyze")
async def analyze(
    image: Annotated[UploadFile, File(...)],
    research_consent: Annotated[bool, Form()] = False,
    algorithm_profile: Annotated[str, Form()] = "auto",
) -> dict[str, object]:
    data = await image.read(MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")
    try:
        job_id = create_job(
            data,
            image.filename or "uploaded-image.tif",
            research_consent=research_consent,
            algorithm_profile=algorithm_profile,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "job_id": job_id,
        "status": "queued",
        "poll": f"/jobs/{job_id}",
        "research_consent": research_consent,
        "algorithm_profile": algorithm_profile,
        "retention": "research copy retained only when explicit consent is true; result expires according to server retention policy",
    }


@app.get("/jobs/{job_id}")
def job(job_id: str) -> dict[str, object]:
    payload = get_job(job_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    return payload


@app.get("/jobs/{job_id}/download")
def download(job_id: str) -> FileResponse:
    try:
        archive = get_archive(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(archive, media_type="application/zip", filename=f"bionuclei-{job_id}.zip")


@app.get("/jobs/{job_id}/files/{filename}")
def result_file(job_id: str, filename: str) -> FileResponse:
    try:
        path = get_file(job_id, filename)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    media = "application/json" if filename.endswith(".json") else "text/csv" if filename.endswith(".csv") else "image/tiff"
    return FileResponse(path, media_type=media, filename=filename)


@app.delete("/jobs/{job_id}/retained-copy")
def delete_retained_copy(job_id: str) -> dict[str, object]:
    from .community import delete_research_copy

    try:
        deleted = delete_research_copy(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"job_id": job_id, "deleted": deleted}


@app.post("/maintenance/purge")
def purge() -> dict[str, int]:
    return {"removed_jobs": purge_expired()}
