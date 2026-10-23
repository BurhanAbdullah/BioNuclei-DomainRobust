"""User-facing BioNuclei inference and deterministic result bundles."""
from __future__ import annotations

import ctypes
import gc
import json
import platform
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import tifffile
import torch
import torch.nn.functional as F
from scipy import ndimage
from skimage.io import imread
from skimage.measure import regionprops

from .data import decode_instance_mask
from .metrics import boundary_f1, dice_coefficient, iou_score
from .models import BoundaryUNet

# Render's free instance has a tight memory budget.  Keep CPU inference
# single-threaded and serialize model construction/inference so repeated
# browser clicks cannot load multiple Boundary U-Nets concurrently.
_INFERENCE_LOCK = threading.Lock()
try:
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
except RuntimeError:
    # PyTorch may already have initialized its thread pools.
    pass


def _trim_cpu_allocator() -> bool:
    """Return free glibc heap pages to the OS after CPU inference when possible.

    PyTorch CPU tensors are freed below, but glibc can otherwise retain their
    arenas in a long-lived 512 MiB web worker. On non-Linux/non-glibc systems
    this is a safe no-op; inference correctness never depends on trimming.
    """
    if not sys.platform.startswith("linux"):
        return False
    try:
        trim = getattr(ctypes.CDLL(None), "malloc_trim", None)
        if trim is None:
            return False
        trim.argtypes = [ctypes.c_size_t]
        trim.restype = ctypes.c_int
        return bool(trim(0))
    except (AttributeError, OSError, TypeError):
        return False


def _normalise(image: np.ndarray) -> np.ndarray:
    x = image.astype(np.float32, copy=False)
    scale = float(np.percentile(x, 99.5))
    if not np.isfinite(scale) or scale <= 0:
        scale = 1.0
    return np.clip(x / scale, 0.0, 1.0)


def _load_model(checkpoint: Path, device: str = "cpu") -> torch.nn.Module:
    target = torch.device(device)
    # The checkpoint is a trusted, immutable release artifact. Memory-map its
    # CPU storages and assign them directly to the module instead of keeping a
    # deserialized state dict and a second copied parameter set resident at
    # once. This matters on the 512 MiB public worker before tiled activations
    # are even allocated. weights_only rejects arbitrary pickled objects.
    state = torch.load(
        checkpoint,
        map_location="cpu",
        mmap=True,
        weights_only=True,
    )
    cfg = state.get("config", {})
    model_cfg = cfg.get("model", {})
    model = BoundaryUNet(
        in_channels=int(model_cfg.get("in_channels", 1)),
        out_channels=int(model_cfg.get("out_channels", 3)),
        base_channels=int(model_cfg.get("base_channels", 32)),
    )
    model.load_state_dict(state["model"], assign=True)
    del state
    if target.type != "cpu":
        model.to(target)
    return model.eval()


def _split_instances(logits: torch.Tensor) -> np.ndarray:
    classes = logits.argmax(dim=1).detach().cpu().numpy()[0]
    foreground = classes != 0
    instances, _ = ndimage.label(foreground, structure=np.ones((3, 3), dtype=np.uint8))
    return instances.astype(np.int32)


def _measure(instances: np.ndarray) -> list[dict[str, float | int]]:
    measurements: list[dict[str, float | int]] = []
    for prop in regionprops(instances):
        measurements.append({
            "instance_id": int(prop.label),
            "area_pixels": int(prop.area),
            "centroid_row": float(prop.centroid[0]),
            "centroid_col": float(prop.centroid[1]),
            "bbox_min_row": int(prop.bbox[0]),
            "bbox_min_col": int(prop.bbox[1]),
            "bbox_max_row": int(prop.bbox[2]),
            "bbox_max_col": int(prop.bbox[3]),
        })
    return measurements


def _overlay(image: np.ndarray, instances: np.ndarray) -> np.ndarray:
    x = _normalise(image)
    base = np.repeat((x[..., None] * 255).astype(np.uint8), 3, axis=2)
    boundaries = instances > 0
    boundaries &= ~ndimage.binary_erosion(instances > 0, structure=np.ones((3, 3), dtype=np.uint8))
    base[boundaries] = np.array([255, 255, 255], dtype=np.uint8)
    return base


def _axis_tile_starts(length: int, tile_size: int, overlap: int) -> list[int]:
    """Return pooling-grid-aligned tile origins that cover an axis."""
    if length <= tile_size:
        return [0]
    stride = tile_size - overlap
    starts = list(range(0, length - tile_size + 1, stride))
    final_start = length - tile_size
    if starts[-1] != final_start:
        starts.append(final_start)
    return starts


def _tile_core_ranges(starts: list[int], tile_length: int, length: int) -> list[tuple[int, int]]:
    """Partition an axis at overlap midpoints so every output pixel is written once."""
    boundaries = [0]
    for previous, current in zip(starts, starts[1:]):
        boundaries.append((previous + tile_length + current) // 2)
    boundaries.append(length)
    return list(zip(boundaries[:-1], boundaries[1:]))


def _predict_logits(
    model: torch.nn.Module,
    x: torch.Tensor,
    tile_size: int = 256,
    overlap: int = 128,
) -> torch.Tensor:
    """Predict logits with bounded spatial activations and overlap-context stitching.

    Origins, tile dimensions, and overlap are multiples of eight to preserve the
    three pooling stages' spatial alignment. A 64-pixel minimum context is kept
    at internal seams; global instance labeling remains a later operation.
    """
    if x.ndim != 4 or x.shape[0] != 1 or x.shape[1] != 1:
        raise ValueError(f"Expected a single-image, single-channel tensor; got {tuple(x.shape)}")
    if tile_size <= overlap or tile_size % 8 or overlap % 8:
        raise ValueError("tile_size and overlap must be multiples of eight with tile_size > overlap")

    original_height, original_width = x.shape[-2:]
    pad_height = (-original_height) % 8
    pad_width = (-original_width) % 8
    if pad_height or pad_width:
        x = F.pad(x, (0, pad_width, 0, pad_height), mode="replicate")

    height, width = x.shape[-2:]
    tile_height = min(tile_size, height)
    tile_width = min(tile_size, width)
    y_starts = _axis_tile_starts(height, tile_size, overlap)
    x_starts = _axis_tile_starts(width, tile_size, overlap)

    with torch.no_grad():
        if len(y_starts) == 1 and len(x_starts) == 1:
            return model(x)[..., :original_height, :original_width]

        y_cores = _tile_core_ranges(y_starts, tile_height, height)
        x_cores = _tile_core_ranges(x_starts, tile_width, width)
        assembled = None
        for y_index, y_start in enumerate(y_starts):
            y0, y1 = y_cores[y_index]
            for x_index, x_start in enumerate(x_starts):
                x0, x1 = x_cores[x_index]
                tile = x[..., y_start:y_start + tile_height, x_start:x_start + tile_width]
                tile_logits = model(tile)
                if assembled is None:
                    assembled = torch.empty(
                        (1, tile_logits.shape[1], height, width),
                        dtype=tile_logits.dtype,
                        device=tile_logits.device,
                    )
                assembled[..., y0:y1, x0:x1] = tile_logits[
                    ...,
                    y0 - y_start:y1 - y_start,
                    x0 - x_start:x1 - x_start,
                ]
                del tile_logits, tile

    return assembled[..., :original_height, :original_width]


def predict(input_path: Path, checkpoint: Path, output: Path, device: str = "cpu") -> dict:
    """Run segmentation and write mask, overlay, measurements and provenance."""
    image = np.asarray(tifffile.imread(input_path))
    if image.ndim != 2:
        raise ValueError(f"Expected a 2-D fluorescence image; got shape {image.shape}")

    # The model is deliberately loaded inside the process-wide lock. This
    # prevents two authenticated /analyze jobs from simultaneously allocating
    # model state and intermediate tensors on a 512 MiB Render instance.
    with _INFERENCE_LOCK:
        model = _load_model(checkpoint, device)
        try:
            x = torch.from_numpy(_normalise(image)[None, None]).float().to(device)
            # The public Render Free instance has a 512 MiB limit. Smaller CPU
            # tiles reduce peak activation memory; retain 64 px context on each
            # side of internal seams. GPU inference keeps the faster default.
            tile_size, overlap = (160, 128) if device == "cpu" else (256, 128)
            with torch.no_grad():
                instances = _split_instances(
                    _predict_logits(model, x, tile_size=tile_size, overlap=overlap)
                )
        finally:
            del x
            del model
            gc.collect()
            if device == "cpu":
                _trim_cpu_allocator()
            if device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()

    output.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(output / "segmentation_mask.tif", instances)
    tifffile.imwrite(output / "overlay.tif", _overlay(image, instances))
    measurements = _measure(instances)
    (output / "measurements.csv").write_text(
        "instance_id,area_pixels,centroid_row,centroid_col,bbox_min_row,bbox_min_col,bbox_max_row,bbox_max_col\n"
        + "\n".join(
            ",".join(str(row[k]) for k in ("instance_id", "area_pixels", "centroid_row", "centroid_col", "bbox_min_row", "bbox_min_col", "bbox_max_row", "bbox_max_col"))
            for row in measurements
        ) + ("\n" if measurements else "")
    )
    results = {"n_instances": len(measurements), "image_shape": list(image.shape)}
    (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    _write_provenance(output, input_path, checkpoint, device, "predict")
    return results


def evaluate(input_path: Path, ground_truth: Path, checkpoint: Path, output: Path, device: str = "cpu") -> dict:
    """Run prediction and report benchmark metrics when ground truth is supplied."""
    result = predict(input_path, checkpoint, output, device)
    target = decode_instance_mask(np.asarray(imread(ground_truth)))
    pred = np.asarray(tifffile.imread(output / "segmentation_mask.tif"))
    if pred.shape != target.shape:
        raise ValueError(f"Prediction/ground-truth shape mismatch: {pred.shape} vs {target.shape}")
    boundary = lambda m: (m > 0) & ~ndimage.binary_erosion(m > 0, structure=np.ones((3, 3), dtype=np.uint8))
    metrics = {
        "dice": float(dice_coefficient(pred > 0, target > 0)),
        "iou": float(iou_score(pred > 0, target > 0)),
        "boundary_f1": float(boundary_f1(boundary(pred), boundary(target))),
    }
    result.update(metrics)
    (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def _write_provenance(output: Path, input_path: Path, checkpoint: Path, device: str, command: str) -> None:
    provenance = {
        "command": command,
        "input": str(input_path.resolve()),
        "checkpoint": str(checkpoint.resolve()),
        "device": device,
        "package": "bionuclei-domainrobust",
        "python": platform.python_version(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
