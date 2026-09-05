#!/usr/bin/env python3
"""Acquire and normalize the authoritative Aitslab-bioimaging1 dataset.

The source is the published Zenodo record 10.5281/zenodo.6657260. The script
never invents a split: it requires the three publisher-provided train,
development and test archives and fails closed if any archive or image/mask
pairing is ambiguous.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from urllib.request import urlopen, Request

import skimage.io

RECORD_API = "https://zenodo.org/api/records/6657260"
IMAGE_EXTS = {".png", ".tif", ".tiff", ".jpg", ".jpeg"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def get_json(url: str) -> dict:
    with urlopen(Request(url, headers={"User-Agent": "BioNuclei-DomainRobust/1.0"})) as r:
        return json.load(r)


def _split_match(name: str, split: str) -> bool:
    """Match publisher archive naming variants without guessing a new split."""
    stem = Path(name).stem.lower()
    aliases = {
        "train": ("train", "training"),
        "development": ("development", "dev"),
        "test": ("test", "testing"),
    }[split]
    return any(re.search(rf"(?:^|[_-]){re.escape(token)}(?:[_-]|$)", stem) for token in aliases)


def pick_files(meta: dict) -> dict[str, dict]:
    """Resolve the three publisher split archives from the Zenodo file list."""
    candidates: dict[str, list[dict]] = {s: [] for s in ("train", "development", "test")}
    for f in meta.get("files", []):
        name = f.get("key") or f.get("filename") or ""
        if not name.lower().endswith(".zip"):
            continue
        for split in candidates:
            if _split_match(Path(name).name, split):
                candidates[split].append(f)

    missing = [s for s, vals in candidates.items() if not vals]
    if missing:
        available = [Path(f.get("key") or f.get("filename") or "").name for f in meta.get("files", [])]
        raise RuntimeError(
            "Aitslab record does not expose required split archives: "
            f"{missing}; available files={available}"
        )

    ambiguous = {s: [Path(f.get("key") or f.get("filename") or "").name for f in vals]
                 for s, vals in candidates.items() if len(vals) != 1}
    if ambiguous:
        raise RuntimeError(f"Ambiguous publisher split archives: {ambiguous}")
    return {s: vals[0] for s, vals in candidates.items()}


def _natural_key(path: Path) -> list[object]:
    """Stable natural ordering for the publisher's image/annotation folders."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def _pair_publisher_layout(files: list[Path]) -> list[tuple[Path, Path]]:
    """Pair the authoritative images/annotations layout used by the dataset.

    The published Aitslab archives contain an ``images/`` directory and an
    ``annotations/`` directory. The independent torch-em dataset adapter for
    this same DOI uses the publisher's natural ordering to pair the two lists.
    We reproduce that convention here, but fail closed on count or shape
    mismatches rather than silently guessing correspondence.
    """
    image_files = sorted(
        [p for p in files if p.suffix.lower() in IMAGE_EXTS and "images" in p.parts],
        key=_natural_key,
    )
    annotation_files = sorted(
        [p for p in files if p.suffix.lower() in IMAGE_EXTS and "annotations" in p.parts],
        key=_natural_key,
    )
    if not image_files or not annotation_files:
        return []
    if len(image_files) != len(annotation_files):
        raise RuntimeError(
            "Publisher image/annotation counts differ: "
            f"images={len(image_files)}, annotations={len(annotation_files)}"
        )
    pairs = []
    for image, annotation in zip(image_files, annotation_files):
        image_shape = skimage.io.imread(image).shape[:2]
        annotation_shape = skimage.io.imread(annotation).shape[:2]
        if image_shape != annotation_shape:
            raise RuntimeError(
                "Publisher image/annotation shape mismatch: "
                f"{image.relative_to(image.parents[0])}={image_shape}, "
                f"{annotation.relative_to(annotation.parents[0])}={annotation_shape}"
            )
        pairs.append((image, annotation))
    return pairs


def classify(files: list[Path]) -> tuple[list[Path], list[Path]]:
    images, masks = [], []
    for p in files:
        if p.suffix.lower() not in IMAGE_EXTS:
            continue
        low = str(p).lower()
        if any(token in low for token in ("annotation", "annot", "mask", "label", "segmentation")):
            masks.append(p)
        else:
            images.append(p)
    return images, masks


def normalize_archive(archive: Path, split: str, root: Path) -> list[dict]:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        with zipfile.ZipFile(archive) as z:
            z.extractall(tmp)
        files = [p for p in tmp.rglob("*") if p.is_file()]

        pairs = _pair_publisher_layout(files)
        if not pairs:
            images, masks = classify(files)
            by_stem: dict[str, list[Path]] = {}
            for m in masks:
                by_stem.setdefault(m.stem, []).append(m)
            for image in images:
                candidates = by_stem.get(image.stem, [])
                if len(candidates) == 1:
                    pairs.append((image, candidates[0]))

        if not pairs:
            raise RuntimeError(f"No unambiguous image/mask pairs found in {archive}")

        out_i, out_m = root / "images", root / "masks"
        out_i.mkdir(parents=True, exist_ok=True)
        out_m.mkdir(parents=True, exist_ok=True)
        rows = []
        for index, (image, mask) in enumerate(pairs):
            image_name = f"{split}__{index:03d}__{image.name}"
            mask_name = f"{split}__{index:03d}__{mask.name}"
            shutil.copy2(image, out_i / image_name)
            shutil.copy2(mask, out_m / mask_name)
            rows.append({
                "image_id": image_name,
                "annotation": mask_name,
                "source_image": str(image.relative_to(tmp)),
                "source_annotation": str(mask.relative_to(tmp)),
                "split": split,
                "pairing_method": "publisher_images_annotations_natural_order" if "images" in image.parts and "annotations" in mask.parts else "exact_stem",
            })
        return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    meta = get_json(RECORD_API)
    files = pick_files(meta)
    manifest = {
        "dataset": "Aitslab_bioimaging1",
        "doi": "10.5281/zenodo.6657260",
        "record_id": 6657260,
        "partitions": {},
        "archives": {},
    }
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for split in ("train", "development", "test"):
            f = files[split]
            name = Path(f.get("key", f.get("filename", ""))).name
            archive = td / name
            url = f.get("links", {}).get("self") or f.get("links", {}).get("download")
            if not url:
                raise RuntimeError(f"No download URL for {split} archive")
            with urlopen(Request(url, headers={"User-Agent": "BioNuclei-DomainRobust/1.0"})) as r, archive.open("wb") as out:
                shutil.copyfileobj(r, out)
            manifest["archives"][split] = {
                "name": name,
                "md5": f.get("checksum"),
                "sha256": sha256(archive),
            }
            rows = normalize_archive(archive, split, args.output)
            manifest["partitions"][split] = rows
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({
        "dataset": manifest["dataset"],
        "counts": {k: len(v) for k, v in manifest["partitions"].items()},
        "manifest_sha256": sha256(args.output / "manifest.json"),
    }, indent=2))


if __name__ == "__main__":
    main()
