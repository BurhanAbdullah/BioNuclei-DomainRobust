#!/usr/bin/env python3
"""Validate a leakage-safe E6 adaptation/evaluation split.

The locked S-BIAD634 zero-shot test set must never be reused for adaptation.
This checker validates manifests before any E6 training is allowed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

IMAGE_KEYS = ("image_id", "id", "image", "filename", "file")
ANNOTATION_KEYS = (
    "annotation_id",
    "annotation",
    "annotation_file",
    "ground_truth",
    "ground_truth_file",
    "mask",
    "mask_file",
    "mask_path",
)


def load_rows(path: Path) -> list[object]:
    obj = json.loads(path.read_text())
    if isinstance(obj, dict):
        rows = obj.get("images") or obj.get("items") or obj.get("records")
    else:
        rows = obj
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a JSON list or a dict containing images/items/records")
    return rows


def load_ids_and_validate_annotations(path: Path) -> set[str]:
    rows = load_rows(path)
    ids: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{path}: every manifest row must be an object containing image and annotation correspondence")
        image_key = next((k for k in IMAGE_KEYS if row.get(k)), None)
        annotation_key = next((k for k in ANNOTATION_KEYS if row.get(k)), None)
        if image_key is None:
            raise ValueError(f"{path}: manifest row has no image identifier: {row}")
        if annotation_key is None:
            raise ValueError(
                f"{path}: manifest row has no annotation/mask reference; "
                f"expected one of {ANNOTATION_KEYS}"
            )
        ids.append(str(row[image_key]))
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate image identifiers detected")
    return set(ids)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adaptation-manifest", type=Path, required=True)
    ap.add_argument("--test-manifest", type=Path, required=True)
    ap.add_argument("--min-adaptation-images", type=int, default=1)
    args = ap.parse_args()

    for p in (args.adaptation_manifest, args.test_manifest):
        if not p.is_file():
            raise SystemExit(f"E6 BLOCKED: missing required manifest: {p}")

    adaptation = load_ids_and_validate_annotations(args.adaptation_manifest)
    test = load_ids_and_validate_annotations(args.test_manifest)
    overlap = adaptation & test
    if len(adaptation) < args.min_adaptation_images:
        raise SystemExit(
            f"E6 BLOCKED: adaptation manifest contains {len(adaptation)} images; "
            f"minimum is {args.min_adaptation_images}"
        )
    if overlap:
        sample = sorted(overlap)[:10]
        raise SystemExit(f"E6 BLOCKED: adaptation/test leakage detected ({len(overlap)} images): {sample}")

    report = {
        "gate": "E6_leakage_split",
        "status": "PASS",
        "adaptation_images": len(adaptation),
        "test_images": len(test),
        "overlap_images": 0,
        "annotation_correspondence_checked": True,
        "adaptation_manifest_sha256": sha256(args.adaptation_manifest),
        "test_manifest_sha256": sha256(args.test_manifest),
        "target_test_reuse_allowed": False,
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
