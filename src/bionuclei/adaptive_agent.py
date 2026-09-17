"""Evidence first adaptive analysis planner for BioNuclei.

The planner performs deterministic input quality checks and a CNN based
analyseability gate before scientific inference. The released Boundary U Net
checkpoint is used only in evaluation mode. The gate does not invent a
probability of correctness and does not alter model weights.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import os

import numpy as np
import tifffile
import torch
from scipy import ndimage


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
class CNNPatternCheck:
    executed: bool
    architecture: str
    foreground_fraction: float
    mean_class_confidence: float
    mean_entropy: float
    connected_components: int
    status: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisPlan:
    status: str
    recommended_modules: tuple[str, ...]
    warnings: tuple[str, ...]
    actions: tuple[str, ...]
    profile: ImageProfile
    cnn_pattern_check: CNNPatternCheck | None = None
    agent_roles: tuple[str, ...] = (
        "input-qc",
        "cnn-pattern-gate",
        "analysis-planner",
        "scientific-runner",
        "quality-reviewer",
        "report-writer",
    )


def inspect_image(path: Path) -> ImageProfile:
    image = np.asarray(tifffile.imread(path))
    if image.ndim != 2:
        raise ValueError(f"Adaptive planner requires a 2 D image; got shape {image.shape}")
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


def _normalise(image: np.ndarray) -> np.ndarray:
    x = image.astype(np.float32, copy=False)
    scale = float(np.percentile(x, 99.5))
    if not np.isfinite(scale) or scale <= 0:
        scale = 1.0
    return np.clip(x / scale, 0.0, 1.0)


def cnn_pattern_check(path: Path) -> CNNPatternCheck:
    """Run the released CNN as an analyseability gate before full analysis.

    This is an evidence gate, not a calibrated classifier. It checks whether
    the trained segmentation CNN detects coherent nuclear foreground structure
    with sufficient class confidence and nondegenerate spatial support.
    """
    try:
        from bionuclei.models import BoundaryUNet
        checkpoint_path = Path(os.getenv("BIONUCLEI_CHECKPOINT", ""))
        if not checkpoint_path.is_file():
            return CNNPatternCheck(False, "Boundary U Net", 0.0, 0.0, 0.0, 0, "NOT_RUN", ("Released checkpoint is not available for the CNN gate.",))
        state = torch.load(checkpoint_path, map_location="cpu")
        cfg = state.get("config", {}).get("model", {})
        model = BoundaryUNet(
            in_channels=int(cfg.get("in_channels", 1)),
            out_channels=int(cfg.get("out_channels", 3)),
            base_channels=int(cfg.get("base_channels", 32)),
        )
        model.load_state_dict(state["model"])
        model.eval()
        image = np.asarray(tifffile.imread(path))
        x = torch.from_numpy(_normalise(image)[None, None]).float()
        with torch.no_grad():
            probabilities = torch.softmax(model(x), dim=1)[0]
        confidence, classes = probabilities.max(dim=0)
        foreground = classes != 0
        foreground_fraction = float(foreground.float().mean().item())
        entropy = -(probabilities.clamp_min(1e-8) * probabilities.clamp_min(1e-8).log()).sum(dim=0)
        mean_confidence = float(confidence.mean().item())
        mean_entropy = float(entropy.mean().item())
        components = int(ndimage.label(foreground.cpu().numpy(), structure=np.ones((3, 3), dtype=np.uint8))[1])
        reasons: list[str] = []
        if foreground_fraction <= 0.001:
            reasons.append("CNN found negligible nuclear foreground support.")
        if foreground_fraction >= 0.98:
            reasons.append("CNN classified nearly the entire image as foreground.")
        if mean_confidence < 0.55:
            reasons.append("CNN class confidence is low.")
        if components == 0:
            reasons.append("CNN produced no connected foreground component.")
        status = "PASS" if not reasons else "CAUTION"
        return CNNPatternCheck(True, "Boundary U Net", foreground_fraction, mean_confidence, mean_entropy, components, status, tuple(reasons))
    except Exception as exc:
        return CNNPatternCheck(False, "Boundary U Net", 0.0, 0.0, 0.0, 0, "NOT_RUN", (f"CNN gate could not execute: {type(exc).__name__}.",))


def build_plan(path: Path, requested_modules: set[str] | None = None) -> AnalysisPlan:
    profile = inspect_image(path)
    requested = set(requested_modules or {"nuclei", "morphology", "intensity"})
    warnings: list[str] = []
    actions = [
        "Input QC agent validates image structure and intensity properties.",
        "CNN pattern gate evaluates multidimensional spatial nuclear patterns with the released Boundary U Net checkpoint.",
        "Analysis planner selects only enabled validated report modules.",
        "Scientific runner executes the released BioNuclei checkpoint in evaluation mode.",
        "Quality reviewer checks the segmentation result and preserves evidence based warnings.",
        "Report writer assembles concise machine readable and human readable outputs.",
    ]
    if not profile.finite:
        warnings.append("Image contains non finite values; inference is not scientifically safe.")
    if profile.std == 0 or profile.p995 == profile.p01:
        warnings.append("Image has effectively no usable intensity variation.")
    elif profile.std / max(abs(profile.mean), 1e-12) < 0.05:
        warnings.append("Low relative intensity variation; segmentation reliability may be reduced.")
    if profile.saturation_fraction > 0.01:
        warnings.append("More than 1 percent of pixels are at the detected dtype ceiling; saturation may affect boundaries.")
    if profile.zero_fraction > 0.80:
        warnings.append("More than 80 percent of pixels are zero; confirm the acquisition or ROI is intentional.")

    cnn = cnn_pattern_check(path) if profile.finite and profile.std > 0 else None
    if cnn and cnn.status == "CAUTION":
        warnings.extend(cnn.reasons)
    if cnn and cnn.status == "NOT_RUN":
        warnings.extend(cnn.reasons)
    actions.append("Do not report a calibrated probability of correctness unless a separately validated uncertainty model is available.")

    if not profile.finite or profile.std == 0:
        status = "BLOCKED"
    elif cnn is None or cnn.status == "NOT_RUN":
        status = "BLOCKED"
    elif cnn.status == "CAUTION" or warnings:
        status = "CAUTION"
    else:
        status = "READY"
    return AnalysisPlan(
        status=status,
        recommended_modules=tuple(sorted(requested)),
        warnings=tuple(warnings),
        actions=tuple(actions),
        profile=profile,
        cnn_pattern_check=cnn,
    )


def to_dict(plan: AnalysisPlan) -> dict[str, Any]:
    payload = asdict(plan)
    payload["recommended_modules"] = list(plan.recommended_modules)
    payload["warnings"] = list(plan.warnings)
    payload["actions"] = list(plan.actions)
    payload["agent_roles"] = list(plan.agent_roles)
    payload["profile"]["shape"] = list(plan.profile.shape)
    if plan.cnn_pattern_check is not None:
        payload["cnn_pattern_check"]["reasons"] = list(plan.cnn_pattern_check.reasons)
    return payload
