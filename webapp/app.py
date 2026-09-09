"""Deployable HTTP interface for the BioNuclei scientific tool surface.

This is a thin web adapter around the existing deterministic Python package.
It does not implement or infer scientific measurements itself.

Run locally with:
    pip install -e '.[web]'
    BIONUCLEI_CHECKPOINT=/absolute/path/model.pt uvicorn webapp.app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import base64
import io
import json
import os
import tempfile
from pathlib import Path
from typing import Annotated

import numpy as np
import tifffile
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from scipy import ndimage
from PIL import Image

from bionuclei.data import decode_instance_mask
from bionuclei.inference import evaluate, predict
from bionuclei.metrics import aji_score, boundary_f1, dice_coefficient, iou_score

app = FastAPI(
    title="BioNuclei Web API",
    version="0.1.0",
    description="HTTP adapter for deterministic BioNuclei bioimage-analysis operations.",
)

allowed_origins = [origin.strip() for origin in os.getenv("BIONUCLEI_ALLOWED_ORIGINS", "*").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

MAX_UPLOAD_BYTES = int(os.getenv("BIONUCLEI_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))


def _checkpoint() -> Path:
    raw = os.getenv("BIONUCLEI_CHECKPOINT")
    if not raw:
        raise HTTPException(status_code=503, detail="BIONUCLEI_CHECKPOINT is not configured on this server")
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise HTTPException(status_code=503, detail="Configured BioNuclei checkpoint is unavailable")
    return path


async def _save_upload(upload: UploadFile, suffix: str = ".tif") -> Path:
    data = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"Upload exceeds {MAX_UPLOAD_BYTES} bytes")
    fd, name = tempfile.mkstemp(prefix="bionuclei-", suffix=suffix)
    os.close(fd)
    path = Path(name)
    path.write_bytes(data)
    return path


def _png_data_url(path: Path) -> str:
    """Encode an output TIFF as a browser-displayable PNG data URL."""
    image = np.asarray(tifffile.imread(path))
    if image.ndim == 2:
        lo, hi = np.percentile(image, [1, 99])
        if not np.isfinite(lo):
            lo = float(np.min(image))
        if not np.isfinite(hi) or hi <= lo:
            hi = lo + 1.0
        arr = np.clip((image.astype(np.float32) - lo) / (hi - lo), 0, 1)
        image = (arr * 255).astype(np.uint8)
        pil = Image.fromarray(image, mode="L")
    elif image.ndim == 3 and image.shape[-1] in {3, 4}:
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)
        pil = Image.fromarray(image)
    else:
        raise ValueError(f"Unsupported output image shape: {image.shape}")
    buf = io.BytesIO()
    pil.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _artifact_payload(output: Path) -> dict[str, object]:
    payload: dict[str, object] = {}
    for name in ["segmentation_mask.tif", "overlay.tif", "measurements.csv", "results.json", "provenance.json"]:
        path = output / name
        if not path.is_file():
            continue
        if name.endswith(".tif"):
            payload[name] = _png_data_url(path)
        else:
            payload[name] = path.read_text()
    return payload


@app.get("/health")
def health() -> dict[str, object]:
    checkpoint = os.getenv("BIONUCLEI_CHECKPOINT")
    return {
        "status": "ok" if checkpoint and Path(checkpoint).expanduser().is_file() else "degraded",
        "scientific_engine": "bionuclei-domainrobust",
        "checkpoint_configured": bool(checkpoint),
    }


@app.get("/tools")
def tools() -> dict[str, object]:
    return {
        "server": "BioNuclei Web API",
        "measurement_policy": "Scientific Python code is authoritative; the web layer only orchestrates it.",
        "tools": [
            {"name": "inspect_image", "http": "POST /inspect", "status": "implemented"},
            {"name": "predict_image", "http": "POST /predict", "status": "implemented"},
            {"name": "evaluate_image", "http": "POST /evaluate", "status": "implemented"},
            {"name": "compute_instance_metrics", "http": "POST /metrics", "status": "implemented"},
            {"name": "read_provenance", "http": "POST /provenance", "status": "implemented"},
            {"name": "load_result_summary", "http": "POST /result-summary", "status": "implemented"},
        ],
        "research_capabilities": {
            "dataset_verification": "available through repository workflows and manifests; not arbitrary remote dataset execution",
            "domain_shift_diagnostics": "research workflow surface; exposed through validated scripts rather than unsafe arbitrary execution",
            "experiment_validation": "research workflow surface; GitHub Actions remains authoritative for registered release experiments",
        },
    }


@app.post("/inspect")
async def inspect(image: Annotated[UploadFile, File(...)]) -> dict[str, object]:
    path = await _save_upload(image)
    try:
        data = np.asarray(tifffile.imread(path))
        if data.ndim != 2:
            raise HTTPException(status_code=400, detail=f"Expected a 2-D fluorescence image; got shape {data.shape}")
        return {
            "filename": image.filename,
            "shape": list(data.shape),
            "dtype": str(data.dtype),
            "min": float(np.min(data)),
            "max": float(np.max(data)),
            "mean": float(np.mean(data)),
            "p99_5": float(np.percentile(data, 99.5)),
        }
    finally:
        path.unlink(missing_ok=True)


@app.post("/predict")
async def predict_api(image: Annotated[UploadFile, File(...)], device: Annotated[str, Form()] = "cpu") -> dict[str, object]:
    if device not in {"cpu", "cuda"}:
        raise HTTPException(status_code=400, detail="device must be cpu or cuda")
    image_path = await _save_upload(image)
    with tempfile.TemporaryDirectory(prefix="bionuclei-output-") as out:
        try:
            output_dir = Path(out)
            result = predict(image_path, _checkpoint(), output_dir, device)
            result["artifacts"] = _artifact_payload(output_dir)
            return result
        finally:
            image_path.unlink(missing_ok=True)


@app.post("/evaluate")
async def evaluate_api(
    image: Annotated[UploadFile, File(...)],
    ground_truth: Annotated[UploadFile, File(...)],
    device: Annotated[str, Form()] = "cpu",
) -> dict[str, object]:
    if device not in {"cpu", "cuda"}:
        raise HTTPException(status_code=400, detail="device must be cpu or cuda")
    image_path = await _save_upload(image)
    gt_path = await _save_upload(ground_truth, suffix=".png")
    with tempfile.TemporaryDirectory(prefix="bionuclei-output-") as out:
        try:
            output_dir = Path(out)
            result = evaluate(image_path, gt_path, _checkpoint(), output_dir, device)
            result["artifacts"] = _artifact_payload(output_dir)
            return result
        finally:
            image_path.unlink(missing_ok=True)
            gt_path.unlink(missing_ok=True)


@app.post("/metrics")
async def metrics_api(prediction: Annotated[UploadFile, File(...)], ground_truth: Annotated[UploadFile, File(...)]) -> dict[str, float]:
    pred_path = await _save_upload(prediction)
    gt_path = await _save_upload(ground_truth, suffix=".png")
    try:
        pred = np.asarray(tifffile.imread(pred_path))
        target = decode_instance_mask(np.asarray(tifffile.imread(gt_path)))
        if pred.shape != target.shape:
            raise HTTPException(status_code=400, detail="Prediction and ground truth shapes differ")
        pred_boundary = (pred > 0) & ~ndimage.binary_erosion(pred > 0, structure=np.ones((3, 3), dtype=np.uint8))
        target_boundary = (target > 0) & ~ndimage.binary_erosion(target > 0, structure=np.ones((3, 3), dtype=np.uint8))
        return {
            "dice": dice_coefficient(pred > 0, target > 0),
            "iou": iou_score(pred > 0, target > 0),
            "aji": aji_score(pred, target),
            "boundary_f1": boundary_f1(pred_boundary, target_boundary),
        }
    finally:
        pred_path.unlink(missing_ok=True)
        gt_path.unlink(missing_ok=True)


@app.post("/provenance")
async def provenance(provenance: Annotated[UploadFile, File(...)]) -> dict[str, object]:
    path = await _save_upload(provenance, suffix=".json")
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid provenance JSON: {exc}") from exc
    finally:
        path.unlink(missing_ok=True)


@app.post("/result-summary")
async def result_summary(results: Annotated[UploadFile, File(...)]) -> dict[str, object]:
    path = await _save_upload(results, suffix=".json")
    try:
        payload = json.loads(path.read_text())
        if not isinstance(payload, dict):
            raise ValueError("result summary must be a JSON object")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid results JSON: {exc}") from exc
    finally:
        path.unlink(missing_ok=True)
