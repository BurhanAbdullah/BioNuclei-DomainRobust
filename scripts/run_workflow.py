#!/usr/bin/env python3
"""Run a declarative BioNuclei workflow over a file or directory."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bionuclei.inference import predict
from bionuclei.workflow import load_workflow


SUPPORTED = {".tif", ".tiff"}


def iter_inputs(path: Path):
    if path.is_file():
        if path.suffix.lower() not in SUPPORTED:
            raise ValueError(f"Unsupported input format: {path.suffix}")
        yield path
        return
    if not path.is_dir():
        raise FileNotFoundError(path)
    for item in sorted(path.rglob("*")):
        if item.is_file() and item.suffix.lower() in SUPPORTED:
            yield item


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a reusable BioNuclei workflow")
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True, help="TIFF file or directory of TIFF files")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    workflow = load_workflow(args.workflow)
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    for image in iter_inputs(args.input):
        out_dir = args.output / image.stem
        result = predict(image, args.checkpoint, out_dir, workflow.device)
        records.append({"input": str(image), "output": str(out_dir), **result})
    (args.output / "workflow_manifest.json").write_text(
        json.dumps({"workflow": workflow.to_dict(), "records": records}, indent=2) + "\n"
    )
    print(f"processed={len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
