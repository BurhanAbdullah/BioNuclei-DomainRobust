"""Command-line interface for end-user BioNuclei testing."""
from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .inference import evaluate, predict


def main() -> None:
    parser = argparse.ArgumentParser(prog="bionuclei", description="Run BioNuclei fluorescence nuclear segmentation locally.")
    parser.add_argument("--version", action="version", version=f"BioNuclei {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--input", type=Path, required=True, help="2-D fluorescence TIFF image")
    common.add_argument("--checkpoint", type=Path, required=True, help="BioNuclei model checkpoint (.pt)")
    common.add_argument("--output", type=Path, required=True, help="Directory for result artifacts")
    common.add_argument("--device", default="cpu", choices=("cpu", "cuda"), help="Inference device")

    p_predict = sub.add_parser("predict", parents=[common], help="Segment a fluorescence image")
    p_predict.set_defaults(handler="predict")

    p_eval = sub.add_parser("evaluate", parents=[common], help="Evaluate a prediction against a ground-truth mask")
    p_eval.add_argument("--ground-truth", type=Path, required=True, help="Ground-truth instance mask")
    p_eval.set_defaults(handler="evaluate")

    args = parser.parse_args()
    if args.handler == "predict":
        result = predict(args.input, args.checkpoint, args.output, args.device)
    else:
        result = evaluate(args.input, args.ground_truth, args.checkpoint, args.output, args.device)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
