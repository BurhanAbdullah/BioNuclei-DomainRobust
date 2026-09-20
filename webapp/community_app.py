"""Standalone public BioNuclei Community Analyzer service."""
from __future__ import annotations

import base64
import json
import os
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from .app import _checkpoint, _png_data_url
from .auth import authenticate_optional, create_guest_token
from .community import MAX_UPLOAD_BYTES, create_job, delete_job, get_archive, get_file, get_job, get_jobs_for_user

app = FastAPI(title="BioNuclei Community Analyzer", version="0.3.2", description="Transient public image analysis service with optional account history.")
allowed_origins=[o.strip() for o in os.getenv("BIONUCLEI_ALLOWED_ORIGINS","*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware,allow_origins=allowed_origins or ["*"],allow_credentials=False,allow_methods=["GET","POST","DELETE"],allow_headers=["*"])

@app.get("/")
def root():
    return {"service":"bionuclei-community-analyzer","version":"0.3.2","status":"online","health":"/health","algorithms":"/algorithms","authentication":"account optional; guest sessions use an ephemeral job token","retention":"original uploads are deleted after processing; results are disposable and expire after one hour"}

@app.get("/health")
def health():
    try: available=_checkpoint().is_file()
    except Exception: available=False
    return {"status":"ok" if available else "degraded","service":"bionuclei-community-analyzer","checkpoint_available":available,"max_upload_bytes":MAX_UPLOAD_BYTES,"supported_input_formats":[".tif",".tiff",".nd2"],"account_required":False,"guest_access":True,"input_retention":"transient","result_retention_hours":1}

@app.get("/algorithms")
def algorithms():
    return {"default":"auto","reports_available":[{"id":"nuclei","name":"Nuclei","status":"available"},{"id":"morphology","name":"Morphology","status":"available"},{"id":"intensity","name":"Intensity","status":"available"}]}

@app.post("/guest-session")
def guest_session():
    return {"guest_token":create_guest_token(),"mode":"guest","persisted":False}

@app.post("/analyze")
async def analyze(request:Request,image:Annotated[UploadFile,File(...)],research_consent:Annotated[bool,Form()]=False,algorithm_profile:Annotated[str,Form()]="auto",analysis_modules:Annotated[str,Form()]="nuclei,morphology,intensity",nd2_channel:Annotated[int,Form()]=0,nd2_time:Annotated[int,Form()]=0,nd2_z:Annotated[int,Form()]=0,nd2_field:Annotated[int,Form()]=0):
    user=authenticate_optional(request);data=await image.read(MAX_UPLOAD_BYTES+1)
    if not data: raise HTTPException(status_code=400,detail="Uploaded image is empty")
    modules=[x.strip().lower() for x in analysis_modules.split(",") if x.strip()]
    try: job_id=create_job(data,image.filename or "uploaded-image.tif",user.id,False,algorithm_profile,modules,channel=nd2_channel,time=nd2_time,z=nd2_z,field=nd2_field)
    except ValueError as exc: raise HTTPException(status_code=400,detail=str(exc)) from exc
    return {"job_id":job_id,"status":"queued","poll":f"/jobs/{job_id}","progress":f"/jobs/{job_id}/progress","account":user.email or ("guest" if user.guest else user.id),"guest":user.guest,"research_consent":False,"analysis_modules":modules}

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
    ]
    phase = status if status in {name for name, *_ in stages} else "queued"
    if output.exists():
        if (output / "expert_agents.json").is_file(): phase = "packaging" if status != "completed" else "completed"
        elif (output / "nuclei_analysis.csv").is_file(): phase = "expert_review"
        elif (output / "segmentation_mask.tif").is_file(): phase = "measuring"
        elif (output / "adaptive_plan.json").is_file(): phase = "running" if status == "running" else "planning"
    if status == "completed": phase = "completed"
    if status not in {"completed","planning","running"} and not output.exists(): phase = "queued"
    selected = next(item for item in stages if item[0] == phase)
    return {"job_id":job_id,"status":status,"phase":phase,"label":selected[1],"message":selected[2],"progress":selected[3],"pipeline_truth_source":"filesystem artifacts plus job status","expert_agents_started":(output / "expert_agents.json").is_file() if output.exists() else False,"report_ready":(output / "analysis_report.pdf").is_file() if output.exists() else False}

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

@app.delete("/jobs/{job_id}")
def remove_job(request:Request,job_id:str):
    user=authenticate_optional(request)
    try: deleted=delete_job(job_id,user.id)
    except FileNotFoundError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    return {"job_id":job_id,"deleted":deleted}

def main():
    import uvicorn
    uvicorn.run("webapp.community_app:app",host="0.0.0.0",port=int(os.getenv("PORT","8000")))
