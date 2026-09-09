"""Standalone public BioNuclei Community Analyzer service."""
from __future__ import annotations

import base64
import os
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from .app import _checkpoint, _png_data_url
from .auth import authenticate
from .community import MAX_UPLOAD_BYTES, create_job, get_archive, get_file, get_job, get_jobs_for_user

app = FastAPI(
    title="BioNuclei Community Analyzer",
    version="0.2.0",
    description="Account-based asynchronous public analysis service for BioNuclei.",
)

allowed_origins = [origin.strip() for origin in os.getenv("BIONUCLEI_ALLOWED_ORIGINS", "*").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, object]:
    try:
        checkpoint_available = _checkpoint().is_file()
    except Exception:
        checkpoint_available = False
    return {
        "status": "ok" if checkpoint_available else "degraded",
        "service": "bionuclei-community-analyzer",
        "checkpoint_available": checkpoint_available,
        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "supported_input_formats": [".tif", ".tiff", ".nd2"],
        "account_required": True,
    }


@app.get("/algorithms")
def algorithms() -> dict[str, object]:
    return {
        "default": "auto",
        "reports_available": [
            {"id": "nuclei", "name": "Nuclei", "status": "available", "description": "Instance segmentation and nucleus count."},
            {"id": "morphology", "name": "Morphology", "status": "available", "description": "Area, perimeter, shape and related per-nucleus morphology."},
            {"id": "intensity", "name": "Intensity", "status": "available", "description": "Per-nucleus fluorescence intensity statistics from the selected image plane."},
        ],
        "advanced": {
            "colocalization": "not enabled until a validated multi-channel workflow is implemented",
            "tracking": "not enabled until a validated time-series workflow is implemented",
            "classification": "not enabled until a validated classifier is implemented",
        },
    }


@app.post("/analyze")
async def analyze(
    request: Request,
    image: Annotated[UploadFile, File(...)],
    research_consent: Annotated[bool, Form()] = False,
    algorithm_profile: Annotated[str, Form()] = "auto",
    analysis_modules: Annotated[str, Form()] = "nuclei,morphology,intensity",
    nd2_channel: Annotated[int, Form()] = 0,
    nd2_time: Annotated[int, Form()] = 0,
    nd2_z: Annotated[int, Form()] = 0,
    nd2_field: Annotated[int, Form()] = 0,
) -> dict[str, object]:
    user = authenticate(request)
    data = await image.read(MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")
    modules = [part.strip().lower() for part in analysis_modules.split(",") if part.strip()]
    try:
        job_id = create_job(
            data,
            image.filename or "uploaded-image.tif",
            user.id,
            research_consent,
            algorithm_profile,
            modules,
            channel=nd2_channel,
            time=nd2_time,
            z=nd2_z,
            field=nd2_field,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "job_id": job_id,
        "status": "queued",
        "poll": f"/jobs/{job_id}",
        "account": user.email or user.id,
        "research_consent": research_consent,
        "algorithm_profile": algorithm_profile,
        "analysis_modules": modules,
        "nd2_selection": {"channel": nd2_channel, "time": nd2_time, "z": nd2_z, "field": nd2_field},
        "retention": "results expire according to server policy; research copies are retained only after explicit consent",
    }


@app.get("/jobs")
def jobs(request: Request) -> dict[str, object]:
    user = authenticate(request)
    return {"jobs": get_jobs_for_user(user.id)}


@app.get("/jobs/{job_id}")
def job(request: Request, job_id: str) -> dict[str, object]:
    user = authenticate(request)
    payload = get_job(job_id, user.id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    return payload


@app.get("/jobs/{job_id}/preview/{filename}")
def preview(request: Request, job_id: str, filename: str) -> Response:
    """Return an authenticated browser-displayable PNG preview for a result TIFF."""
    if filename not in {"overlay.tif", "segmentation_mask.tif"}:
        raise HTTPException(status_code=404, detail="Unsupported preview file")
    user = authenticate(request)
    try:
        path = get_file(job_id, user.id, filename)
        data_url = _png_data_url(path)
        encoded = data_url.split(",", 1)[1]
        return Response(content=base64.b64decode(encoded), media_type="image/png", headers={"Cache-Control": "private, max-age=300"})
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/jobs/{job_id}/download")
def download(request: Request, job_id: str) -> FileResponse:
    user = authenticate(request)
    try:
        archive = get_archive(job_id, user.id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(archive, media_type="application/zip", filename=f"bionuclei-{job_id}.zip")


@app.get("/jobs/{job_id}/files/{filename}")
def result_file(request: Request, job_id: str, filename: str) -> FileResponse:
    user = authenticate(request)
    try:
        path = get_file(job_id, user.id, filename)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    media = "application/json" if filename.endswith(".json") else "text/csv" if filename.endswith(".csv") else "image/tiff"
    return FileResponse(path, media_type=media, filename=filename)


@app.delete("/jobs/{job_id}/retained-copy")
def delete_retained_copy(request: Request, job_id: str) -> dict[str, object]:
    user = authenticate(request)
    from .community import delete_research_copy
    try:
        deleted = delete_research_copy(job_id, user.id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"job_id": job_id, "deleted": deleted}


def main() -> None:
    import uvicorn
    uvicorn.run("webapp.community_app:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
