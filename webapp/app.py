"""Deployable HTTP interface for the BioNuclei scientific tool surface.

This is a thin web adapter around the existing deterministic Python package.
It does not implement or infer scientific measurements itself.

Run locally with:
    pip install -e '.[web]'\n    BIONUCLEI_CHECKPOINT=/absolute/path/model.pt uvicorn webapp.app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
import base64
import fcntl
import hashlib
import hmac
import io
import json
import os
import stat
import tempfile
import threading
from pathlib import Path
from typing import Annotated, BinaryIO, Iterator

import numpy as np
import tifffile
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from scipy import ndimage
from PIL import Image

from bionuclei.data import decode_instance_mask
from bionuclei.inference import evaluate, predict
from bionuclei.metrics import aji_score, boundary_f1, dice_coefficient, iou_score

@asynccontextmanager
async def _checkpoint_lifespan(_app: FastAPI):
    # Hash the large release artifact before health probes begin. Missing or
    # mismatched files remain visible as degraded health and fail-closed inference.
    try:
        _checkpoint_identity()
    except HTTPException:
        pass
    yield


app = FastAPI(
    title="BioNuclei Web API",
    version="0.1.0",
    description="HTTP adapter for deterministic BioNuclei bioimage-analysis operations.",
    lifespan=_checkpoint_lifespan,
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


RELEASE_CHECKPOINT_SHA256 = "7209a6990514380804210292ac208b0f3b0b0a054338a145e1916044762d7c92"

# Cache the source digest by exact file identity for health/preflight calls.
# Inference always copies the opened source into a sealed memfd snapshot, so a
# same-inode write after verification cannot change the bytes mmap loads. The
# pinned BBBC039 release asset is 7,743,145 bytes; the snapshot copy is bounded.
_CHECKPOINT_CACHE_LOCK = threading.Lock()
_CHECKPOINT_CACHE: tuple[str, tuple[int, int, int, int, int], str] | None = None


def _checkpoint_stat_key(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _hash_checkpoint(stream) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


@contextmanager
def _checkpoint_handle() -> Iterator[tuple[Path, str, bool, BinaryIO]]:
    """Verify a checkpoint while retaining the exact opened inode for inference."""
    global _CHECKPOINT_CACHE

    raw = os.getenv("BIONUCLEI_CHECKPOINT")
    if not raw:
        raise HTTPException(status_code=503, detail="BIONUCLEI_CHECKPOINT is not configured on this server")
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise HTTPException(status_code=503, detail="Configured BioNuclei checkpoint is unavailable")

    expected = os.getenv("BIONUCLEI_CHECKPOINT_SHA256", RELEASE_CHECKPOINT_SHA256).strip().lower()
    if expected.startswith("sha256:"):
        expected = expected.removeprefix("sha256:")
    expected_is_sha256 = len(expected) == 64 and all(char in "0123456789abcdef" for char in expected)
    configured_release_matches = expected_is_sha256 and hmac.compare_digest(
        expected, RELEASE_CHECKPOINT_SHA256
    )

    stream: BinaryIO | None = None
    try:
        stream = path.open("rb")
        with _CHECKPOINT_CACHE_LOCK:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise HTTPException(status_code=503, detail="Configured BioNuclei checkpoint is unavailable")
            identity = _checkpoint_stat_key(before)
            cached = _CHECKPOINT_CACHE
            cache_hit = cached is not None and cached[0] == str(path) and cached[1] == identity
            actual = cached[2] if cache_hit else _hash_checkpoint(stream)

            # The path and opened descriptor must identify the same unchanged file
            # at verification time. The descriptor remains open after this check,
            # so later path replacement cannot redirect the model loader.
            after = os.fstat(stream.fileno())
            current_path = path.stat()
            if identity != _checkpoint_stat_key(after) or identity != _checkpoint_stat_key(current_path):
                _CHECKPOINT_CACHE = None
                raise HTTPException(
                    status_code=503,
                    detail="Configured BioNuclei checkpoint changed while being verified",
                )
            if not cache_hit:
                _CHECKPOINT_CACHE = (str(path), identity, actual)
    except HTTPException:
        if stream is not None:
            stream.close()
        raise
    except OSError as exc:
        if stream is not None:
            stream.close()
        _CHECKPOINT_CACHE = None
        raise HTTPException(status_code=503, detail="Configured BioNuclei checkpoint could not be read") from exc

    assert stream is not None
    verified = hmac.compare_digest(actual, RELEASE_CHECKPOINT_SHA256) and configured_release_matches
    try:
        yield path, actual, verified, stream
    finally:
        stream.close()


def _checkpoint_identity() -> tuple[Path, str, bool]:
    """Return the actual checkpoint digest and whether it matches the pinned release."""
    with _checkpoint_handle() as (path, actual, verified, _stream):
        return path, actual, verified


@contextmanager
def _sealed_checkpoint_snapshot(stream: BinaryIO, expected_sha256: str) -> Iterator[Path]:
    """Copy verified bytes into a write-sealed memfd for race-free mmap loading."""
    try:
        snapshot_fd = os.memfd_create(
            "bionuclei-verified-checkpoint",
            os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
        )
    except (AttributeError, OSError) as exc:
        raise HTTPException(
            status_code=503,
            detail="This runtime cannot create an immutable checkpoint snapshot",
        ) from exc

    try:
        stream.seek(0)
        digest = hashlib.sha256()
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            view = memoryview(chunk)
            while view:
                written = os.write(snapshot_fd, view)
                if written <= 0:
                    raise OSError("checkpoint snapshot write made no progress")
                view = view[written:]

        if not hmac.compare_digest(digest.hexdigest(), expected_sha256):
            raise HTTPException(
                status_code=503,
                detail="Checkpoint bytes changed while creating the immutable inference snapshot",
            )

        os.lseek(snapshot_fd, 0, os.SEEK_SET)
        required_seals = (
            fcntl.F_SEAL_WRITE
            | fcntl.F_SEAL_GROW
            | fcntl.F_SEAL_SHRINK
            | fcntl.F_SEAL_SEAL
        )
        fcntl.fcntl(snapshot_fd, fcntl.F_ADD_SEALS, required_seals)
        actual_seals = fcntl.fcntl(snapshot_fd, fcntl.F_GET_SEALS)
        if actual_seals & required_seals != required_seals:
            raise HTTPException(
                status_code=503,
                detail="The verified checkpoint snapshot could not be write-sealed",
            )

        descriptor_stat = os.fstat(snapshot_fd)
        descriptor_path = None
        for descriptor_root in (Path("/proc/self/fd"), Path("/dev/fd")):
            candidate = descriptor_root / str(snapshot_fd)
            try:
                candidate_stat = candidate.stat()
            except OSError:
                continue
            if (
                stat.S_ISREG(candidate_stat.st_mode)
                and candidate_stat.st_dev == descriptor_stat.st_dev
                and candidate_stat.st_ino == descriptor_stat.st_ino
            ):
                descriptor_path = candidate
                break

        if descriptor_path is None:
            raise HTTPException(
                status_code=503,
                detail="Immutable checkpoint snapshot has no stable descriptor path",
            )
        yield descriptor_path
    except HTTPException:
        raise
    except (AttributeError, OSError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Verified checkpoint could not be snapshotted and sealed for inference",
        ) from exc
    finally:
        os.close(snapshot_fd)


@contextmanager
def _checkpoint_for_inference() -> Iterator[Path]:
    """Load only a write-sealed snapshot of the verified release checkpoint."""
    with _checkpoint_handle() as (_path, actual, verified, stream):
        if not verified:
            raise HTTPException(
                status_code=503,
                detail="Configured BioNuclei checkpoint does not match the expected release SHA-256",
            )
        with _sealed_checkpoint_snapshot(stream, actual) as snapshot_path:
            yield snapshot_path



def _checkpoint() -> Path:
    """Fail closed when the configured checkpoint is not the pinned release."""
    path, _actual, verified = _checkpoint_identity()
    if not verified:
        raise HTTPException(
            status_code=503,
            detail="Configured BioNuclei checkpoint does not match the expected release SHA-256",
        )
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
    """Encode a 2-D scientific image as a browser-displayable PNG data URL."""
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


def _artifact_payload(output: Path, *, original: Path | None = None) -> dict[str, object]:
    payload: dict[str, object] = {}
    if original is not None and original.is_file():
        payload["input_preview.png"] = _png_data_url(original)
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
    checkpoint_configured = bool(os.getenv("BIONUCLEI_CHECKPOINT"))
    try:
        checkpoint, digest, verified = _checkpoint_identity()
        available = checkpoint.is_file()
    except HTTPException:
        available, digest, verified = False, None, False
    return {
        "status": "ok" if available and verified else "degraded",
        "scientific_engine": "bionuclei-domainrobust",
        "checkpoint_configured": checkpoint_configured,
        "checkpoint_available": available,
        "checkpoint_sha256": digest,
        "checkpoint_verified": verified,
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
            with _checkpoint_for_inference() as checkpoint:
                result = predict(image_path, checkpoint, output_dir, device)
            result["artifacts"] = _artifact_payload(output_dir, original=image_path)
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
            with _checkpoint_for_inference() as checkpoint:
                result = evaluate(image_path, gt_path, checkpoint, output_dir, device)
            result["artifacts"] = _artifact_payload(output_dir, original=image_path)
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
