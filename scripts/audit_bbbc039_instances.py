#!/usr/bin/env python3
"""Audit BBBC039 instance-mask semantics and prediction instance counts.

This is diagnostic only. It does not alter the trained model or promote any
metric. It records enough information to distinguish an evaluator/mask-encoding
problem from genuine instance-merging or over-segmentation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from scipy import ndimage
from skimage.io import imread
import tifffile

from bionuclei.data import decode_instance_mask
from bionuclei.models import BoundaryUNet


def resolve_image_path(root: Path, image_name: str) -> Path:
    exact = root / "images" / image_name
    if exact.exists():
        return exact
    stem = Path(image_name).stem
    candidates = sorted(p for p in (root / "images").rglob("*") if p.is_file() and p.stem == stem)
    if len(candidates) == 1:
        return candidates[0]
    raise RuntimeError(f"Expected one image for {image_name}; found {len(candidates)}")


def mask_path(root: Path, image_name: str) -> Path:
    stem = Path(image_name).stem
    candidates = sorted(p for p in (root / "masks").rglob("*") if p.is_file() and p.stem == stem)
    if len(candidates) == 1:
        return candidates[0]
    raise RuntimeError(f"Expected one mask for {image_name}; found {len(candidates)}")


def predict_instances(model: BoundaryUNet, image: np.ndarray) -> np.ndarray:
    x = image.astype(np.float32)
    scale = np.percentile(x, 99.5)
    x = np.clip(x / max(float(scale), 1.0), 0.0, 1.0)
    with torch.inference_mode():
        logits = model(torch.from_numpy(x[None, None]).float())
    classes = logits.argmax(dim=1).cpu().numpy()[0]
    instances, _ = ndimage.label(classes != 0, structure=np.ones((3, 3), dtype=np.uint8))
    return instances.astype(np.int32)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--split", choices=("train", "validation", "test"), default="test")
    parser.add_argument("--output", type=Path, default=Path("outputs/bbbc039_eval/instance_audit.json"))
    args = parser.parse_args()

    checkpoint = torch.load(args.checkpoint, map_location="cpu")
    cfg = checkpoint["config"]
    model = BoundaryUNet(
        in_channels=int(cfg["model"]["in_channels"]),
        out_channels=int(cfg["model"]["out_channels"]),
        base_channels=int(cfg["model"]["base_channels"]),
    )
    model.load_state_dict(checkpoint["model"])
    model.eval()

    manifest = json.loads(args.manifest.read_text())
    records = []
    for name in manifest["partitions"][args.split]:
        image_path = resolve_image_path(args.data_root, name)
        mask_path_value = mask_path(args.data_root, name)
        image = np.asarray(tifffile.imread(image_path))
        raw_mask = np.asarray(imread(mask_path_value))
        target = decode_instance_mask(raw_mask)
        pred = predict_instances(model, image)
        target_ids = np.unique(target[target > 0])
        pred_ids = np.unique(pred[pred > 0])
        _, target_component_count = ndimage.label(target > 0, structure=np.ones((3, 3), dtype=np.uint8))
        if raw_mask.ndim == 3 and raw_mask.shape[-1] in (3, 4):
            unique_colors = int(np.unique(raw_mask[..., :3].reshape(-1, 3), axis=0).shape[0])
        else:
            unique_colors = None
        records.append({
            "image": name,
            "mask_shape": list(raw_mask.shape),
            "mask_dtype": str(raw_mask.dtype),
            "raw_mask_unique_values": int(np.unique(raw_mask).size),
            "raw_mask_unique_rgb_colors": unique_colors,
            "decoded_target_instances": int(len(target_ids)),
            "target_connected_components": int(target_component_count),
            "target_instances_per_connected_component": float(len(target_ids) / target_component_count) if target_component_count else None,
            "touching_instance_labels": bool(len(target_ids) > target_component_count),
            "predicted_instances": int(len(pred_ids)),
            "predicted_foreground_fraction": float(np.mean(pred > 0)),
            "target_foreground_fraction": float(np.mean(target > 0)),
            "prediction_to_target_instance_ratio": float(len(pred_ids) / len(target_ids)) if len(target_ids) else None,
        })

    ratios = [r["prediction_to_target_instance_ratio"] for r in records if r["prediction_to_target_instance_ratio"] is not None]
    target_instance_counts = [r["decoded_target_instances"] for r in records]
    target_component_counts = [r["target_connected_components"] for r in records]
    records_with_touching = sum(r["touching_instance_labels"] for r in records)
    report = {
        "dataset": "BBBC039v1",
        "split": args.split,
        "n_images": len(records),
        "checkpoint_seed": checkpoint.get("seed"),
        "diagnostic_only": True,
        "interpretation_guard": {
            "instance_count_is_decoded_label_count": True,
            "connected_component_count_is_not_used_as_instance_count": True,
            "connected_components_may_merge_touching_instances": True,
            "touching_instances_detected_when_decoded_count_exceeds_foreground_components": True,
        },
        "summary": {
            "mean_target_instances": float(np.mean(target_instance_counts)),
            "mean_target_connected_components": float(np.mean(target_component_counts)),
            "mean_target_instances_per_connected_component": float(np.mean([r["target_instances_per_connected_component"] for r in records if r["target_instances_per_connected_component"] is not None])),
            "images_with_touching_instance_labels": int(records_with_touching),
            "mean_predicted_instances": float(np.mean([r["predicted_instances"] for r in records])),
            "median_prediction_to_target_instance_ratio": float(np.median(ratios)) if ratios else None,
        },
        "per_image": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
