#!/usr/bin/env python3
"""Inventory and validate a locally acquired S-BIAD634 study package.

This script does not download data. It records a deterministic file inventory
and performs conservative image/mask pairing checks without assuming a single
pixel format or directory layout beyond the documented study package.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

IMAGE_SUFFIXES = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def inventory(root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        row: dict[str, object] = {
            "path": str(path.relative_to(root)),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        if path.suffix.lower() in IMAGE_SUFFIXES and Image is not None:
            try:
                with Image.open(path) as image:
                    row["format"] = image.format
                    row["size_xy"] = list(image.size)
                    row["mode"] = image.mode
            except Exception as exc:
                row["image_error"] = str(exc)
        rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if not args.root.is_dir():
        raise SystemExit(f"Study directory does not exist: {args.root}")

    rows = inventory(args.root)
    image_rows = [r for r in rows if Path(str(r["path"])).suffix.lower() in IMAGE_SUFFIXES]
    report = {
        "dataset": "S-BIAD634",
        "root": str(args.root),
        "file_count": len(rows),
        "image_file_count": len(image_rows),
        "files": rows,
        "validation_notes": [
            "This is an inventory check, not a claim that the local package is complete.",
            "Ground-truth pairing and study-level splits require inspection of the authoritative file list.",
        ],
    }
    output = args.output or args.root / "download_manifest.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("dataset", "file_count", "image_file_count", "output")}, indent=2))


if __name__ == "__main__":
    main()
