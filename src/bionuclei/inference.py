"""User-facing BioNuclei inference and deterministic result bundles."""
from __future__ import annotations

import gc
import json
import math
import platform
import threading
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import tifffile
import torch
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


def _normalise(image: np.ndarray) -> np.ndarray:
    x = image.astype(np.float32, copy=False)
    scale = float(np.percentile(x, 99.5))
    if not np.isfinite(scale) or scale <= 0:
        scale = 1.0
    return np.clip(x / scale, 0.0, 1.0)


def _load_model(checkpoint: Path, device: str = "cpu") -> torch.nn.Module:
    target = torch.device(device)
    state = torch.load(checkpoint, map_location=target)
    cfg = state.get("config", {})
    model_cfg = cfg.get("model", {})
    model = BoundaryUNet(
        in_channels=int(model_cfg.get("in_channels", 1)),
        out_channels=int(model_cfg.get("out_channels", 3)),
        base_channels=int(model_cfg.get("base_channels", 32)),
    )
    model.load_state_dict(state["model"])
    # The checkpoint may also contain optimizer/scheduler metadata. Drop the
    # deserialized container before inference so it cannot overlap with tile
    # activations on memory-constrained production instances.
    del state
    gc.collect()
    model.to(target).eval()
    return model


def _split_instances(logits: torch.Tensor) -> np.ndarray:
    classes = logits.argmax(dim=1).detach().cpu().numpy()[0]
    foreground = classes != 0
    instances, _ = ndimage.label(foreground, structure=np.ones((3, 3), dtype=np.uint8))
    return instances.astype(np.int32)



def _tile_starts(length: int, tile_size: int, overlap: int) -> list[int]:
    """Return deterministic, evenly spaced tile origins with complete coverage."""
    if length <= tile_size:
        return [0]
    stride = tile_size - overlap
    count = math.ceil((length - tile_size) / stride) + 1
    # Spread any required remainder across tiles instead of creating a tiny
    # final tile (which can be incompatible with the U-Net's pooling strides).
    return sorted({
        int(round(i * (length - tile_size) / (count - 1)))
        for i in range(count)
    })


def _predict_logits_tiled(
    model: torch.nn.Module,
    x: torch.Tensor,
    *,
    tile_size: int = 288,
    overlap: int = 64,
) -> torch.Tensor:
    """Run inference in overlapping tiles and blend logits on CPU.

    The input tensor is already normalized from the original image. Only model
    activations are tiled; measurements later still use the untouched source
    image, preserving the full uint16 intensity range.
    """
    if tile_size <= 0 or overlap < 0 or overlap >= tile_size:
        raise ValueError("tile_size must be positive and overlap in [0, tile_size)")
    if x.ndim != 4 or x.shape[0] != 1:
        raise ValueError("Tiled inference expects a single NCHW image")

    _, _, height, width = x.shape
    if height <= tile_size and width <= tile_size:
        return model(x)

    y_starts = _tile_starts(height, tile_size, overlap)
    x_starts = _tile_starts(width, tile_size, overlap)
    logits_sum: torch.Tensor | None = None
    weight_sum = torch.zeros((1, 1, height, width), dtype=torch.float32, device="cpu")

    for top in y_starts:
        bottom = min(top + tile_size, height)
        for left in x_starts:
            right = min(left + tile_size, width)
            tile = x[..., top:bottom, left:right]
            tile_logits = model(tile)
            if (
                tile_logits.ndim != 4
                or tile_logits.shape[0] != 1
                or tile_logits.shape[-2:] != (bottom - top, right - left)
            ):
                raise ValueError("Model returned unexpected tile-logit shape")
            if logits_sum is None:
                logits_sum = torch.zeros(
                    (1, tile_logits.shape[1], height, width),
                    dtype=torch.float32,
                    device="cpu",
                )
            logits_sum[..., top:bottom, left:right] += tile_logits.detach().to(
                device="cpu", dtype=torch.float32
            )
            weight_sum[..., top:bottom, left:right] += 1.0
            del tile_logits, tile

    if logits_sum is None or torch.any(weight_sum == 0):
        raise RuntimeError("Tiled inference did not cover every input pixel")
    return logits_sum / weight_sum


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
            with torch.no_grad():
                instances = _split_instances(_predict_logits_tiled(model, x))
        finally:
            del x
            del model
            gc.collect()
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
