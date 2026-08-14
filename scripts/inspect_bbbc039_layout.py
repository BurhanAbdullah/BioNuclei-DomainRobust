#!/usr/bin/env python3
"""Produce a non-destructive inventory of the downloaded BBBC039 archives.

This is intentionally diagnostic: it reports paths, suffix counts, duplicate
basenames, and image dimensions without deciding that an unexpected layout is
valid. It excludes ZIP-generated macOS resource-fork metadata so the inventory
reflects the scientific dataset rather than archive noise.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import tifffile


def is_macos_metadata(path: Path) -> bool:
    return "__MACOSX" in path.parts or path.name.startswith("._")


def inventory(root: Path) -> dict:
    result: dict = {"root": str(root), "directories": {}, "tiff": {}}
    for name in ("images", "masks", "metadata"):
        directory = root / name
        if not directory.exists():
            result["directories"][name] = {"exists": False}
            continue
        all_files = [p for p in directory.rglob("*") if p.is_file()]
        files = [p for p in all_files if not is_macos_metadata(p)]
        suffixes = Counter(p.suffix.lower() for p in files)
        result["directories"][name] = {
            "exists": True,
            "file_count": len(files),
            "excluded_macos_metadata_files": len(all_files) - len(files),
            "suffix_counts": dict(sorted(suffixes.items())),
            "sample_paths": [str(p.relative_to(directory)) for p in files[:20]],
        }
        if name == "images":
            tiffs = sorted(p for p in files if p.suffix.lower() in {".tif", ".tiff"})
            by_name: dict[str, list[str]] = defaultdict(list)
            shapes = Counter()
            dtypes = Counter()
            for p in tiffs:
                by_name[p.name.lower()].append(str(p.relative_to(directory)))
                try:
                    arr = tifffile.imread(p)
                    shapes[str(tuple(arr.shape))] += 1
                    dtypes[str(arr.dtype)] += 1
                except Exception as exc:
                    shapes[f"READ_ERROR:{type(exc).__name__}"] += 1
            result["tiff"] = {
                "file_count": len(tiffs),
                "unique_basenames": len(by_name),
                "duplicate_basenames": {
                    k: v for k, v in by_name.items() if len(v) > 1
                },
                "shape_counts": dict(shapes),
                "dtype_counts": dict(dtypes),
            }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("data/raw/BBBC039"))
    parser.add_argument("--output", type=Path, default=Path("data/raw/BBBC039/layout_report.json"))
    args = parser.parse_args()
    report = inventory(args.data_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
