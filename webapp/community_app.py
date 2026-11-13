"""Standalone public BioNuclei Community Analyzer service."""
from __future__ import annotations

import asyncio

import base64
import json
import os
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

from .app import _checkpoint_identity, _checkpoint_lifespan, _png_data_url
from .auth import authenticate_optional, create_guest_token
from . import community as community_service
from .community import MAX_UPLOAD_BYTES, create_job, delete_job, delete_research_copy, get_archive, get_file, get_job, get_jobs_for_user


app = FastAPI(title="BioNuclei Community Analyzer", version="0.3.3", description="Transient public image analysis service with optional account history.", lifespan=_checkpoint_lifespan)
PUBLIC_SITE_ORIGIN = "https://burhanabdullah.github.io"


def _configured_origins(value: str | None) -> list[str]:
    """Keep the published GitHub Pages analyzer able to call the public API.

    Operators may restrict additional origins through BIONUCLEI_ALLOWED_ORIGINS,
    but that setting must not accidentally disable the only supported public UI.
    Wildcard mode remains available because this API intentionally uses no cookies.
    """
    raw = value if value is not None else "*"
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if "*" in origins:
        return ["*"]
    if PUBLIC_SITE_ORIGIN not in origins:
        origins.append(PUBLIC_SITE_ORIGIN)
    return origins or [PUBLIC_SITE_ORIGIN]


allowed_origins = _configured_origins(os.getenv("BIONUCLEI_ALLOWED_ORIGINS"))


# Multipart uploads are parsed and spooled by Starlette before the endpoint
# function runs. Admission must therefore happen at the ASGI boundary, not in
# the route, or concurrent rejected uploads can still exhaust temporary disk.
MAX_MULTIPART_OVERHEAD_BYTES = 1024 * 1024
MAX_UPLOAD_BODY_TIMEOUT_SECONDS = int(
    os.getenv("BIONUCLEI_UPLOAD_BODY_TIMEOUT_SECONDS", "120")
)
if not 1 <= MAX_UPLOAD_BODY_TIMEOUT_SECONDS <= 600:
    raise RuntimeError(
        "BIONUCLEI_UPLOAD_BODY_TIMEOUT_SECONDS must be between 1 and 600"
    )


class _RequestBodyTooLarge(Exception):
    """Abort multipart parsing after the bounded request body is exceeded."""


class _RequestBodyTimedOut(Exception):
    """Abort multipart parsing when the complete upload exceeds its deadline."""


class AnalyzeAdmissionMiddleware:
    """Reserve analyzer capacity and cap request bytes before multipart parsing."""

    def __init__(
        self,
        app,
        max_body_bytes: int | None = None,
        body_timeout_seconds: float | None = None,
    ) -> None:
        self.app = app
        self.max_body_bytes = (
            max_body_bytes
            if max_body_bytes is not None
            else MAX_UPLOAD_BYTES + MAX_MULTIPART_OVERHEAD_BYTES
        )
        self.body_timeout_seconds = (
            body_timeout_seconds
            if body_timeout_seconds is not None
            else MAX_UPLOAD_BODY_TIMEOUT_SECONDS
        )
        if self.body_timeout_seconds <= 0:
            raise ValueError("body_timeout_seconds must be positive")

    async def __call__(self, scope, receive, send) -> None:
        if (
            scope.get("type") != "http"
            or scope.get("method") != "POST"
            or str(scope.get("path", "")).rstrip("/") != "/analyze"
        ):
            await self.app(scope, receive, send)
            return

        content_length = next(
            (
                value
                for key, value in scope.get("headers", [])
                if key.lower() == b"content-length"
            ),
            None,
        )
        if content_length is not None:
            if not content_length.isdigit():
                response = JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid Content-Length header"},
                )
                await response(scope, receive, send)
                return
            try:
                declared_length = int(content_length)
            except ValueError:
                # Python limits decimal-to-int conversion length. Validate this
                # before reserving the only worker slot so a huge numeric header
                # cannot turn a malformed request into a permanent capacity leak.
                response = JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid Content-Length header"},
                )
                await response(scope, receive, send)
                return
            if declared_length > self.max_body_bytes:
                response = JSONResponse(
                    status_code=413,
                    content={
                        "detail": "Analysis request body exceeds the configured upload limit"
                    },
                )
                await response(scope, receive, send)
                return

        try:
            reservation = community_service.reserve_job_slot()
        except community_service.JobCapacityError as exc:
            response = JSONResponse(
                status_code=429,
                content={"detail": str(exc)},
                headers={"Retry-After": "60"},
            )
            await response(scope, receive, send)
            return

        state = scope.setdefault("state", {})
        state["bionuclei_job_slot_reservation"] = reservation
        state["bionuclei_job_slot_transferred"] = False

        received_bytes = 0
        response_sent = False

        async def reject_oversized_body() -> None:
            nonlocal response_sent
            if response_sent:
                return
            response_sent = True
            response = JSONResponse(
                status_code=413,
                content={"detail": "Analysis request body exceeds the configured upload limit"},
            )
            await response(scope, receive, send)

        async def reject_timed_out_body() -> None:
            nonlocal response_sent
            if response_sent:
                return
            response_sent = True
            response = JSONResponse(
                status_code=408,
                content={
                    "detail": (
                        "Analysis upload did not complete within "
                        f"{self.body_timeout_seconds:g} seconds"
                    )
                },
            )
            await response(scope, receive, send)

        loop = asyncio.get_running_loop()
        body_deadline = loop.time() + self.body_timeout_seconds

        async def limited_receive():
            nonlocal received_bytes
            remaining = body_deadline - loop.time()
            if remaining <= 0:
                await reject_timed_out_body()
                raise _RequestBodyTimedOut
            try:
                message = await asyncio.wait_for(receive(), timeout=remaining)
            except asyncio.TimeoutError:
                await reject_timed_out_body()
                raise _RequestBodyTimedOut
            if message.get("type") == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_body_bytes:
                    await reject_oversized_body()
                    raise _RequestBodyTooLarge
            return message

        async def guarded_send(message) -> None:
            if not response_sent:
                await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except _RequestBodyTooLarge:
            # The 413 response was sent before aborting the parser. Suppress any
            # secondary response from the interrupted multipart request.
            return
        except _RequestBodyTimedOut:
            # The 408 response was sent before cancelling the stalled body read.
            return
        finally:
            if not state.get("bionuclei_job_slot_transferred"):
                reservation.release()


# This middleware is deliberately outside the router so it runs before
# FastAPI/Starlette consumes and spools the multipart request body.
app.add_middleware(AnalyzeAdmissionMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    retention_hours = community_service.DEFAULT_RESULT_RETENTION_HOURS
    retention_duration = "1 hour" if retention_hours == 1 else f"{retention_hours} hours"
    return {
        "service": "bionuclei-community-analyzer",
        "version": "0.3.3",
        "status": "online",
        "health": "/health",
        "algorithms": "/algorithms",
        "authentication": "account optional; guest sessions use an ephemeral job token",
        "retention": (
            "original uploads are deleted after processing; results are disposable "
            f"and expire after {retention_duration}"
        ),
        "result_retention_hours": retention_hours,
    }

@app.get("/health")
def health():
    try:
        checkpoint, digest, verified = _checkpoint_identity()
        available = checkpoint.is_file()
    except HTTPException:
        available, digest, verified = False, None, False
    return {
        "status": "ok" if available and verified else "degraded",
        "service": "bionuclei-community-analyzer",
        "checkpoint_available": available,
        "checkpoint_sha256": digest,
        "checkpoint_verified": verified,
        "render_git_commit": os.getenv("RENDER_GIT_COMMIT", "unknown"),
        "render_git_branch": os.getenv("RENDER_GIT_BRANCH", "unknown"),
        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "supported_input_formats": [".tif", ".tiff", ".nd2"],
        "account_required": False,
        "guest_access": True,
        "input_retention": "transient",
        "result_retention_hours": community_service.DEFAULT_RESULT_RETENTION_HOURS,
    }

@app.get("/algorithms")
def algorithms():
    return {"default":"auto","reports_available":[{"id":"nuclei","name":"Nuclei","status":"available"},{"id":"morphology","name":"Morphology","status":"available"},{"id":"intensity","name":"Intensity","status":"available"}]}

@app.post("/guest-session")
def guest_session():
    return {"guest_token":create_guest_token(),"mode":"guest","persisted":False}

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
):
    if research_consent:
        raise HTTPException(
            status_code=400,
            detail="Research retention is not implemented; uploads are processed transiently and are not used for training.",
        )
    community_service._checkpoint()
    user = authenticate_optional(request)
    reservation = getattr(request.state, "bionuclei_job_slot_reservation", None)
    if reservation is None:
        raise HTTPException(
            status_code=503,
            detail="Upload admission could not reserve analyzer capacity.",
        )

    data = await image.read(MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Upload exceeds {MAX_UPLOAD_BYTES} bytes",
        )
    modules = [
        value.strip().lower()
        for value in analysis_modules.split(",")
        if value.strip()
    ]
    try:
        job_id = create_job(
            data,
            image.filename or "uploaded-image.tif",
            user.id,
            False,
            algorithm_profile,
            modules,
            channel=nd2_channel,
            time=nd2_time,
            z=nd2_z,
            field=nd2_field,
            reservation=reservation,
        )
        # The worker now owns the reservation until its cleanup path exits.
        request.state.bionuclei_job_slot_transferred = True
    except community_service.JobCreationError as exc:
        return JSONResponse(
            status_code=500,
            content={
                "detail": (
                    f"{exc} (job {exc.job_id}; stage {exc.stage}; "
                    f"cleanup status {exc.cleanup_status})"
                ),
                "error": "job_creation_failed",
                "job_id": exc.job_id,
                "stage": exc.stage,
                "cleanup_status": exc.cleanup_status,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "job_id": job_id,
        "status": "queued",
        "poll": f"/jobs/{job_id}",
        "progress": f"/jobs/{job_id}/progress",
        "account": user.email or ("guest" if user.guest else user.id),
        "guest": user.guest,
        "research_consent": False,
        "analysis_modules": modules,
    }

@app.get("/jobs")
def jobs(request:Request):
    user=authenticate_optional(request);return {"jobs":get_jobs_for_user(user.id)}

@app.get("/jobs/{job_id}")
def job(request:Request,job_id:str):
    user=authenticate_optional(request);payload=get_job(job_id,user.id)
    if payload is None: raise HTTPException(status_code=404,detail="Analysis job not found")
    if payload.get("status")=="completed" and payload.get("result") is None:
        try:
            result_path=get_file(job_id,user.id,"results.json")
            payload["result"]=json.loads(result_path.read_text(encoding="utf-8"))
        except (FileNotFoundError,ValueError,json.JSONDecodeError,OSError):
            pass
    return payload

@app.get("/jobs/{job_id}/progress")
def progress(request:Request,job_id:str):
    """Return truthful fine-grained progress derived from actual pipeline artifacts."""
    user=authenticate_optional(request)
    payload=get_job(job_id,user.id)
    if payload is None: raise HTTPException(status_code=404,detail="Analysis job not found")
    root = __import__("webapp.community", fromlist=["_job_dir"])._job_dir(job_id)
    output = root / "results"
    status = str(payload.get("status") or "queued").lower()
    stages = [
        ("queued", "1 · Analysis started", "Analysis job accepted and waiting for execution.", 12),
        ("planning", "2 · Quality & planning", "Input-quality gate and adaptive analysis plan are running.", 24),
        ("running", "3 · Boundary U-Net inference", "Boundary U-Net is generating the nuclear prediction.", 52),
        ("measuring", "4 · Instance measurements", "Detected nuclei are being separated and measured.", 68),
        ("expert_review", "5 · Expert evidence review", "Evidence-constrained specialist agents are reviewing the measured result.", 84),
        ("packaging", "6 · Report packaging", "The report and downloadable analysis package are being assembled.", 94),
        ("completed", "7 · Complete", "Analysis complete. The report is ready to download.", 100),
        ("failed", "Analysis failed", "Analysis failed. Cleanup status is reported separately.", 0),
    ]
    phase = status if status in {name for name, *_ in stages} else "queued"
    if output.exists():
        if (output / "expert_agents.json").is_file(): phase = "packaging" if status != "completed" else "completed"
        elif (output / "nuclei_analysis.csv").is_file(): phase = "expert_review"
        elif (output / "segmentation_mask.tif").is_file(): phase = "measuring"
        elif (output / "adaptive_plan.json").is_file(): phase = "running" if status == "running" else "planning"
    if status == "completed": phase = "completed"
    if status == "failed": phase = "failed"
    if status not in {"completed","failed","planning","running"} and not output.exists(): phase = "queued"
    selected = next(item for item in stages if item[0] == phase)
    message = selected[2]
    cleanup_status = "pending"
    if status == "completed":
        # Completion is only persisted after transient input cleanup succeeds.
        cleanup_status = "verified"
    elif status == "failed":
        error = str(payload.get("error") or "")
        if error.endswith(community_service._FAILED_JOB_CLEANUP_SUFFIX):
            cleanup_status = "incomplete"
            message = (
                "Analysis failed. Cleanup is incomplete; transient artifacts may remain. "
                "Automatic cleanup retries will continue. Please retry later."
            )
        elif error in {
            community_service._FAILED_JOB_ERROR,
            community_service._INTERRUPTED_JOB_ERROR,
        }:
            cleanup_status = "verified"
            message = (
                "Analysis failed. Transient input/result artifacts were removed and "
                "cleanup was verified. Please retry the analysis."
            )
        else:
            # Legacy or unrecognized error records do not prove that cleanup succeeded.
            cleanup_status = "unknown"
            message = (
                "Analysis failed. Cleanup status is unknown; do not assume transient "
                "input/result artifacts were removed."
            )
    report_ready = (
        status == "completed"
        and output.exists()
        and (output / "analysis_report.pdf").is_file()
    )
    return {
        "job_id": job_id,
        "status": status,
        "phase": phase,
        "label": selected[1],
        "message": message,
        "progress": selected[3],
        "pipeline_truth_source": "filesystem artifacts plus job status",
        "expert_agents_started": (
            (output / "expert_agents.json").is_file() if output.exists() else False
        ),
        "report_ready": report_ready,
        "cleanup_status": cleanup_status,
    }

@app.get("/jobs/{job_id}/preview/{filename}")
def preview(request:Request,job_id:str,filename:str):
    if filename not in {"overlay.tif","segmentation_mask.tif"}: raise HTTPException(status_code=404,detail="Unsupported preview file")
    user=authenticate_optional(request)
    try:
        data_url=_png_data_url(get_file(job_id,user.id,filename));return Response(content=base64.b64decode(data_url.split(",",1)[1]),media_type="image/png",headers={"Cache-Control":"no-store"})
    except FileNotFoundError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=400,detail=str(exc)) from exc

@app.get("/jobs/{job_id}/download")
def download(request:Request,job_id:str):
    user=authenticate_optional(request)
    try: archive=get_archive(job_id,user.id)
    except FileNotFoundError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    return FileResponse(archive,media_type="application/zip",filename=f"bionuclei-{job_id}.zip",headers={"Cache-Control":"no-store"})

@app.get("/jobs/{job_id}/files/{filename}")
def result_file(request:Request,job_id:str,filename:str):
    user=authenticate_optional(request)
    try: path=get_file(job_id,user.id,filename)
    except (FileNotFoundError,ValueError) as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    media="application/json" if filename.endswith(".json") else "text/csv" if filename.endswith(".csv") else "application/pdf" if filename.endswith(".pdf") else "image/tiff"
    return FileResponse(path,media_type=media,filename=filename,headers={"Cache-Control":"no-store"})

@app.delete("/jobs/{job_id}/research-copy")
def remove_research_copy(request: Request, job_id: str):
    user = authenticate_optional(request)
    try:
        deleted = delete_research_copy(job_id, user.id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"job_id": job_id, "research_copy_deleted": deleted}


@app.delete("/jobs/{job_id}")
def remove_job(request:Request,job_id:str):
    user=authenticate_optional(request)
    try: deleted=delete_job(job_id,user.id)
    except FileNotFoundError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    return {"job_id":job_id,"deleted":deleted}

def main():
    import uvicorn
    uvicorn.run("webapp.community_app:app",host="0.0.0.0",port=int(os.getenv("PORT","8000")))
