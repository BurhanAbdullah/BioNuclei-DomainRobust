#!/usr/bin/env python3
"""Run the frozen E6 cross-dataset few-shot protocol on Aitslab-bioimaging1."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import subprocess
import sys
from pathlib import Path

import yaml

FRACTIONS = (0.01, 0.05, 0.10, 0.25)
SEED = 42
EPOCHS = 20


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def disjoint(parts: dict[str, list[dict]]) -> None:
    ids = {k: {r["image_id"] for r in parts[k]} for k in ("train", "development", "test")}
    for left, right in (("train", "development"), ("train", "test"), ("development", "test")):
        overlap = ids[left] & ids[right]
        if overlap:
            raise RuntimeError(f"E6 BLOCKED: {left}/{right} publisher split overlap: {sorted(overlap)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--dataset-root", type=Path, required=True)
    ap.add_argument("--dataset-manifest", type=Path, required=True)
    ap.add_argument("--init-checkpoint", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--epochs", type=int, default=EPOCHS)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--fraction", type=float, choices=FRACTIONS, default=None)
    a = ap.parse_args()
    if a.seed != SEED:
        raise ValueError(f"E6 requires frozen seed {SEED}")
    if a.epochs != EPOCHS:
        raise ValueError(f"E6 requires frozen {EPOCHS}-epoch budget")

    meta = json.loads(a.dataset_manifest.read_text())
    parts = meta["partitions"]
    train, dev, test = parts["train"], parts["development"], parts["test"]
    if (len(train), len(dev), len(test)) != (30, 10, 10):
        raise RuntimeError(f"E6 BLOCKED: expected publisher split 30/10/10, got {len(train)}/{len(dev)}/{len(test)}")
    disjoint(parts)

    a.output.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    shuffled = list(train)
    rng.shuffle(shuffled)
    fractions = (a.fraction,) if a.fraction is not None else FRACTIONS
    results = []

    for frac in fractions:
        n = max(1, math.ceil(len(train) * frac))
        selected = shuffled[:n]
        split = {
            "partitions": {
                "train": [r["image_id"] for r in selected],
                "validation": [r["image_id"] for r in dev],
                "test": [r["image_id"] for r in test],
            },
            "fraction": frac,
            "n_adaptation_images": n,
            "selection_rule": "uniform image-level sample from publisher train split; deterministic seed 42; ceil(fraction*N); no test access",
        }
        split_path = a.output / f"split_{int(frac * 100):02d}pct.json"
        split_path.write_text(json.dumps(split, indent=2) + "\n")
        run_dir = a.output / f"{int(frac * 100):02d}pct"
        ckpt_dir, eval_dir = run_dir / "checkpoint", run_dir / "evaluation"
        cfg_path = run_dir / "config.yaml"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)

        cfg = yaml.safe_load(a.config.read_text())
        cfg["seed"] = SEED
        cfg["training"]["epochs"] = EPOCHS
        cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))

        train_cmd = [sys.executable, "scripts/train_domain_robust.py", "--config", str(cfg_path), "--manifest", str(split_path), "--data-root", str(a.dataset_root), "--output", str(ckpt_dir), "--epochs", str(EPOCHS), "--init-checkpoint", str(a.init_checkpoint)]
        eval_cmd = [sys.executable, "scripts/evaluate_instance_manifest.py", "--checkpoint", str(ckpt_dir / "last.pt"), "--manifest", str(split_path), "--data-root", str(a.dataset_root), "--split", "test", "--output", str(eval_dir)]
        subprocess.run(train_cmd, check=True)
        subprocess.run(eval_cmd, check=True)

        metrics_path = eval_dir / "test_metrics.json"
        metrics = json.loads(metrics_path.read_text())
        if metrics.get("n_images") != len(test):
            raise RuntimeError(f"E6 {frac}: incomplete test evaluation")

        prov = {
            "experiment": "E6_cross_dataset_few_shot",
            "dataset": "Aitslab_bioimaging1",
            "doi": "10.5281/zenodo.6657260",
            "fraction": frac,
            "n_adaptation_images": n,
            "n_test_images": len(test),
            "seed": SEED,
            "epochs": EPOCHS,
            "dataset_manifest_sha256": sha256(a.dataset_manifest),
            "dataset_archive_sha256": {k: v["sha256"] for k, v in meta["archives"].items()},
            "split_manifest_sha256": sha256(split_path),
            "config_sha256": sha256(cfg_path),
            "init_checkpoint_sha256": sha256(a.init_checkpoint),
            "adapted_checkpoint_sha256": sha256(ckpt_dir / "last.pt"),
            "test_metrics_sha256": sha256(metrics_path),
            "train_command": " ".join(train_cmd),
            "evaluation_command": " ".join(eval_cmd),
            "s_biad634_used_for_adaptation": False,
            "test_images_used_for_adaptation": False,
            "development_images_used_for_training_or_selection": False,
        }
        (run_dir / "provenance.json").write_text(json.dumps(prov, indent=2) + "\n")
        results.append({"fraction": frac, "n_adaptation_images": n, "mean": metrics["mean"], "provenance": str(run_dir / "provenance.json")})

    if a.fraction is None:
        (a.output / "aggregate_results.json").write_text(json.dumps({"protocol": "E6_cross_dataset_few_shot", "fractions": results}, indent=2) + "\n")
    else:
        (a.output / "fraction_result.json").write_text(json.dumps(results[0], indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
