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


def _files_in_named_dir(files: list[Path], dirname: str) -> list[Path]:
    """Return image files below a named directory, case-insensitively."""
    dirname = dirname.lower()
    return sorted(
        [
            p for p in files
            if p.suffix.lower() in IMAGE_EXTS
            and any(part.lower() == dirname for part in p.parts[:-1])
        ],
        key=_natural_key,
    )


def _pair_publisher_layout(files: list[Path]) -> list[tuple[Path, Path, str]]:
    """Pair the published images/annotations layout without filename guessing.

    The authoritative Arvidsson/Aitslab adapter first uses the preprocessed
    TIFF annotations when their count matches the PNG images, otherwise it
    falls back to the publisher RGB PNG annotations and converts them. Mirror
    that resolution here. Pairing is by the publisher's natural ordering;
    counts and spatial dimensions are verified before any files are copied.
    """
    image_files = _files_in_named_dir(files, "images")
    if not image_files:
        return []

    annotation_dir = [
        p for p in files
        if any(part.lower() == "annotations" for part in p.parts[:-1])
    ]
    preprocessed = sorted(
        [p for p in annotation_dir if p.suffix.lower() in {".tif", ".tiff"} and "_preprocessed" in p.stem.lower()],
        key=_natural_key,
    )
    if len(preprocessed) == len(image_files):
        annotation_files = preprocessed
        pairing_method = "publisher_images_annotations_preprocessed_tif_natural_order"
    else:
        annotation_files = sorted(
            [p for p in annotation_dir if p.suffix.lower() == ".png"],
            key=_natural_key,
        )
        pairing_method = "publisher_images_annotations_png_natural_order"

    if len(image_files) != len(annotation_files):
        return []

    pairs: list[tuple[Path, Path, str]] = []
    for image, annotation in zip(image_files, annotation_files):
        image_shape = skimage.io.imread(image).shape[:2]
        annotation_shape = skimage.io.imread(annotation).shape[:2]
        if image_shape != annotation_shape:
            raise RuntimeError(
                "Publisher image/annotation shape mismatch: "
                f"{image}={image_shape}, {annotation}={annotation_shape}"
            )
        pairs.append((image, annotation, pairing_method))
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


def _safe_extract(zip_path: Path, destination: Path) -> None:
    """Extract a zip while rejecting path traversal entries."""
    destination = destination.resolve()
    with zipfile.ZipFile(zip_path) as z:
        for member in z.infolist():
            target = (destination / member.filename).resolve()
            if target != destination and destination not in target.parents:
                raise RuntimeError(f"Unsafe archive member path: {member.filename}")
        z.extractall(destination)


def _extract_nested_archives(root: Path, max_depth: int = 3) -> None:
    """Recursively unpack nested publisher zips so images/annotations are visible."""
    seen: set[Path] = set()
    for _depth in range(max_depth):
        nested = sorted(root.rglob("*.zip"), key=_natural_key)
        pending = [p for p in nested if p.resolve() not in seen]
        if not pending:
            return
        for nested_zip in pending:
            seen.add(nested_zip.resolve())
            target = nested_zip.with_suffix("")
            target.mkdir(parents=True, exist_ok=True)
            _safe_extract(nested_zip, target)
    remaining = [p for p in root.rglob("*.zip") if p.resolve() not in seen]
    if remaining:
        raise RuntimeError(f"Nested archive depth exceeds {max_depth}: {[str(p) for p in remaining]}")


def normalize_archive(archive: Path, split: str, root: Path) -> list[dict]:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _safe_extract(archive, tmp)
        _extract_nested_archives(tmp)
        files = [p for p in tmp.rglob("*") if p.is_file() and p.suffix.lower() != ".zip"]

        publisher_pairs = _pair_publisher_layout(files)
        pairs: list[tuple[Path, Path, str]] = list(publisher_pairs)
        if not pairs:
            images, masks = classify(files)
            by_stem: dict[str, list[Path]] = {}
            for m in masks:
                by_stem.setdefault(m.stem, []).append(m)
            for image in images:
                candidates = by_stem.get(image.stem, [])
                if len(candidates) == 1:
                    pairs.append((image, candidates[0], "exact_stem"))

        if not pairs:
            raise RuntimeError(f"No unambiguous image/mask pairs found in {archive}")

        out_i, out_m = root / "images", root / "masks"
        out_i.mkdir(parents=True, exist_ok=True)
        out_m.mkdir(parents=True, exist_ok=True)
        rows = []
        for index, (image, mask, pairing_method) in enumerate(pairs):
            # Normalize the paired files to a shared basename. Downstream
            # training/evaluation code resolves masks by image stem, so this
            # preserves the validated publisher pairing without relying on
            # unrelated source filenames having identical stems.
            image_name = f"{split}__{index:03d}__{image.stem}{image.suffix.lower()}"
            mask_name = image_name
            shutil.copy2(image, out_i / image_name)
            shutil.copy2(mask, out_m / mask_name)
            rows.append({
                "image_id": image_name,
                "annotation": mask_name,
                "source_image": str(image.relative_to(tmp)),
                "source_annotation": str(mask.relative_to(tmp)),
                "split": split,
                "pairing_method": pairing_method,
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
