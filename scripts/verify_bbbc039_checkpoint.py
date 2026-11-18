#!/usr/bin/env python3
"""Verify that a BBBC039 checkpoint was trained with the committed release recipe."""
from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import torch
import yaml


def validate_checkpoint_metadata(
    checkpoint: Mapping[str, Any],
    expected_config: Mapping[str, Any],
) -> dict[str, int]:
    """Reject checkpoint metadata that differs from the committed training recipe."""
    actual_config = checkpoint.get("config")
    if not isinstance(actual_config, Mapping) or dict(actual_config) != dict(expected_config):
        raise ValueError("checkpoint config does not match the committed BBBC039 baseline configuration")

    expected_seed = expected_config.get("seed")
    seed = checkpoint.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed != expected_seed:
        raise ValueError(
            f"checkpoint seed does not match committed configuration: expected={expected_seed!r}, actual={seed!r}"
        )

    training = expected_config.get("training")
    expected_epochs = training.get("epochs") if isinstance(training, Mapping) else None
    epochs_run = checkpoint.get("epochs_run")
    if isinstance(epochs_run, bool) or not isinstance(epochs_run, int) or epochs_run != expected_epochs:
        raise ValueError(
            f"checkpoint epochs_run does not match committed configuration: expected={expected_epochs!r}, actual={epochs_run!r}"
        )

    return {"seed": seed, "epochs_run": epochs_run}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()

    if not args.checkpoint.is_file():
        raise FileNotFoundError(f"baseline checkpoint is missing: {args.checkpoint}")

    expected_config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
    verified = validate_checkpoint_metadata(checkpoint, expected_config)
    print(json.dumps({
        "status": "verified",
        "checkpoint": str(args.checkpoint),
        "seed": verified["seed"],
        "epochs_run": verified["epochs_run"],
        "config_matches": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
