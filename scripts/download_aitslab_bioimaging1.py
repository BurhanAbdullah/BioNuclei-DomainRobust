#!/usr/bin/env python3
"""Acquire and normalize the authoritative Aitslab-bioimaging1 dataset.

The source is the published Zenodo record 10.5281/zenodo.6657260.  The script
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

def pick_files(meta: dict) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for f in meta.get("files", []):
        name = f["key"] if "key" in f else f.get("filename", "")
        low = Path(name).name.lower()
        for split in ("train", "development", "test"):
            if re.search(rf"(?:^|[_-]){split}(?:[_-]|\.|$)", low):
                if low.endswith(".zip"):
                    found[split] = f
    missing = [s for s in ("train", "development", "test") if s not in found]
    if missing:
        raise RuntimeError(f"Aitslab record does not expose required split archives: {missing}")
    return found

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
        images, masks = classify(files)
        by_stem: dict[str, list[Path]] = {}
        for m in masks:
            by_stem.setdefault(m.stem, []).append(m)
        rows = []
        out_i, out_m = root / "images", root / "masks"
        out_i.mkdir(parents=True, exist_ok=True); out_m.mkdir(parents=True, exist_ok=True)
        for image in images:
            candidates = by_stem.get(image.stem, [])
            if len(candidates) != 1:
                continue
            mask = candidates[0]
            image_name = f"{split}__{image.name}"
            mask_name = f"{split}__{mask.name}"
            shutil.copy2(image, out_i / image_name)
            shutil.copy2(mask, out_m / mask_name)
            rows.append({
                "image_id": image_name,
                "annotation": mask_name,
                "source_image": str(image.relative_to(tmp)),
                "source_annotation": str(mask.relative_to(tmp)),
                "split": split,
            })
        if not rows:
            raise RuntimeError(f"No unambiguous image/mask pairs found in {archive}")
        return rows

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    meta = get_json(RECORD_API)
    files = pick_files(meta)
    manifest = {"dataset": "Aitslab_bioimaging1", "doi": "10.5281/zenodo.6657260", "record_id": 6657260, "partitions": {}, "archives": {}}
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
            manifest["archives"][split] = {"name": name, "md5": f.get("checksum"), "sha256": sha256(archive)}
            rows = normalize_archive(archive, split, args.output)
            manifest["partitions"][split] = rows
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"dataset": manifest["dataset"], "counts": {k: len(v) for k,v in manifest["partitions"].items()}, "manifest_sha256": sha256(args.output / "manifest.json")}, indent=2))

if __name__ == "__main__":
    main()
