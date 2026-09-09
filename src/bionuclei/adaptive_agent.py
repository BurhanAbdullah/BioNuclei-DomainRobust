"""Evidence-first adaptive analysis planner for BioNuclei.

The planner adapts the *analysis plan and warnings* to measurable properties of an
uploaded image. It never changes model weights, invents confidence, or replaces
scientific measurement code.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import tifffile


@dataclass(frozen=True)
class ImageProfile:
    shape: tuple[int, int]
    dtype: str
    min: float
    p01: float
    median: float
    p995: float
    max: float
    mean: float
    std: float
    saturation_fraction: float
    zero_fraction: float
    finite: bool


@dataclass(frozen=True)
class AnalysisPlan:
    status: str
    recommended_modules: tuple[str, ...]
    warnings: tuple[str, ...]
    actions: tuple[str, ...]
    profile: ImageProfile


def inspect_image(path: Path) -> ImageProfile:
    image = np.asarray(tifffile.imread(path))
    if image.ndim != 2:
        raise ValueError(f"Adaptive planner requires a 2-D image; got shape {image.shape}")
    x = image.astype(np.float64, copy=False)
    finite_mask = np.isfinite(x)
    finite = bool(finite_mask.all())
    finite_values = x[finite_mask]
    if finite_values.size == 0:
        finite_values = np.array([0.0])
    dtype_info = np.iinfo(image.dtype) if np.issubdtype(image.dtype, np.integer) else None
    upper = float(dtype_info.max) if dtype_info is not None else float(np.max(finite_values))
    saturation = float(np.mean(finite_values >= upper)) if upper > 0 else 0.0
    return ImageProfile(
        shape=(int(image.shape[0]), int(image.shape[1])),
        dtype=str(image.dtype),
        min=float(np.min(finite_values)),
        p01=float(np.percentile(finite_values, 1)),
        median=float(np.median(finite_values)),
        p995=float(np.percentile(finite_values, 99.5)),
        max=float(np.max(finite_values)),
        mean=float(np.mean(finite_values)),
        std=float(np.std(finite_values)),
        saturation_fraction=saturation,
        zero_fraction=float(np.mean(finite_values == 0)),
        finite=finite,
    )


def build_plan(path: Path, requested_modules: set[str] | None = None) -> AnalysisPlan:
    profile = inspect_image(path)
    requested = set(requested_modules or {"nuclei", "morphology", "intensity"})
    warnings: list[str] = []
    actions = ["Run the released BioNuclei checkpoint in evaluation mode.", "Record input and execution provenance."]
    if not profile.finite:
        warnings.append("Image contains non-finite values; inference is not scientifically safe.")
    if profile.std == 0 or profile.p995 == profile.p01:
        warnings.append("Image has effectively no usable intensity variation.")
    elif profile.std / max(abs(profile.mean), 1e-12) < 0.05:
        warnings.append("Low relative intensity variation; segmentation reliability may be reduced.")
    if profile.saturation_fraction > 0.01:
        warnings.append("More than 1% of pixels are at the detected dtype ceiling; saturation may affect boundaries.")
    if profile.zero_fraction > 0.80:
        warnings.append("More than 80% of pixels are zero; confirm the acquisition/ROI is intentional.")
    actions.append("Label the run with any detected input-quality warnings; do not convert them into model accuracy claims.")
    status = "BLOCKED" if not profile.finite or profile.std == 0 else "CAUTION" if warnings else "READY"
    return AnalysisPlan(
        status=status,
        recommended_modules=tuple(sorted(requested)),
        warnings=tuple(warnings),
        actions=tuple(actions),
        profile=profile,
    )


def to_dict(plan: AnalysisPlan) -> dict[str, Any]:
    payload = asdict(plan)
    payload["recommended_modules"] = list(plan.recommended_modules)
    payload["warnings"] = list(plan.warnings)
    payload["actions"] = list(plan.actions)
    payload["profile"]["shape"] = list(plan.profile.shape)
    return payload
