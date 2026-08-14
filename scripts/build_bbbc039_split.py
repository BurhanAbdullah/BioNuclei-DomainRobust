#!/usr/bin/env python3
"""Build and validate the official BBBC039 train/validation/test manifest.

The Broad Bioimage Benchmark Collection publishes the recommended partitions in
its metadata archive. This script discovers partition files from the downloaded
metadata package, normalizes image basenames, checks for overlap, and writes a
machine-readable manifest. It deliberately fails rather than inventing a split
when the official partition metadata cannot be found.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

PARTITIONS = ("train", "validation", "test")
IMAGE_EXTENSIONS = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}


def normalize_name(value: str) -> str | None:
    value = value.strip().strip('"').strip("'")
    if not value:
        return None
    p = Path(value)
    if p.suffix.lower() in IMAGE_EXTENSIONS:
        return p.name
    return None


def parse_partition_file(path: Path, partition: str) -> set[str]:
    names: set[str] = set()
    text = path.read_text(errors="replace")
    for line in text.splitlines():
        candidate = normalize_name(line)
        if candidate:
            names.add(candidate)
    if not names:
        raise ValueError(f"No image filenames found in {path} for {partition}")
    return names


def discover_partition_files(metadata_root: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for path in metadata_root.rglob("*"):
        if not path.is_file():
            continue
        stem = re.sub(r"[^a-z0-9]+", "_", path.stem.lower()).strip("_")
        for partition in PARTITIONS:
            if partition in stem and partition not in found:
                found[partition] = path
    missing = [p for p in PARTITIONS if p not in found]
    if missing:
        raise SystemExit(
            "Official BBBC039 partition metadata not found for: "
            + ", ".join(missing)
            + ". Inspect metadata.zip before creating any replacement split."
        )
    return found


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/manifests/bbbc039_official_split.json"))
    args = parser.parse_args()

    files = discover_partition_files(args.metadata_root)
    splits = {name: sorted(parse_partition_file(path, name)) for name, path in files.items()}

    sets = {name: set(values) for name, values in splits.items()}
    for i, left in enumerate(PARTITIONS):
        for right in PARTITIONS[i + 1 :]:
            overlap = sets[left] & sets[right]
            if overlap:
                raise SystemExit(f"Partition leakage detected between {left} and {right}: {sorted(overlap)[:10]}")

    manifest = {
        "dataset": "BBBC039v1",
        "partition_source": {k: str(v) for k, v in files.items()},
        "partitions": splits,
        "counts": {k: len(v) for k, v in splits.items()},
        "validation": {"pairwise_overlap": False},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest["counts"], indent=2))


if __name__ == "__main__":
    main()
