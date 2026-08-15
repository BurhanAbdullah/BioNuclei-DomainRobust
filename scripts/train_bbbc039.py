#!/usr/bin/env python3
"""Train the boundary-aware U-Net on an already verified BBBC039 split."""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader

from bionuclei.data import InstanceMaskDataset
from bionuclei.losses import BoundaryAwareLoss
from bionuclei.models import BoundaryUNet
from bionuclei.targets import instance_to_boundary_target

IMAGE_EXTENSIONS = (".tif", ".tiff", ".png", ".jpg", ".jpeg")


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def resolve_image_path(root: Path, name: str) -> Path:
    """Resolve a metadata filename against the downloaded image archive."""
    exact = root / "images" / name
    if exact.exists():
        return exact
    stem = Path(name).stem
    candidates = sorted(
        p for p in (root / "images").iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS and p.stem == stem
    )
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise FileNotFoundError(f"No downloaded image matches manifest entry {name}")
    raise RuntimeError(f"Ambiguous downloaded image matches for {name}: {candidates}")


def pair_paths(root: Path, names: list[str]) -> tuple[list[Path], list[Path]]:
    images, masks = [], []
    for name in names:
        image = resolve_image_path(root, name)
        stem = Path(name).stem
        candidates = [root / "masks" / f"{stem}.png", root / "masks" / f"{stem}.tif"]
        mask = next((p for p in candidates if p.exists()), None)
        if mask is None:
            raise FileNotFoundError(f"No mask found for {name}: tried {candidates}")
        images.append(image)
        masks.append(mask)
    return images, masks


def collate(batch):
    images, masks = zip(*batch)
    targets = [torch.from_numpy(instance_to_boundary_target(m.numpy())) for m in masks]
    return torch.stack(images), torch.stack(targets)


def train_epoch(model, loader, loss_fn, optimizer, device):
    model.train()
    total = 0.0
    for images, targets in loader:
        images, targets = images.to(device), targets.to(device)
        optimizer.zero_grad(set_to_none=True)
        logits = model(images)
        loss = loss_fn(logits, targets)
        loss.backward()
        optimizer.step()
        total += loss.item() * images.size(0)
    return total / len(loader.dataset)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/bbbc039_baseline.yaml"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/bbbc039_baseline"))
    parser.add_argument("--epochs", type=int, default=None, help="Optional override for controlled pilot runs")
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    seed = int(cfg["seed"])
    seed_everything(seed)

    manifest = json.loads(args.manifest.read_text())
    train_names = manifest["partitions"]["train"]
    image_paths, mask_paths = pair_paths(args.data_root, train_names)
    dataset = InstanceMaskDataset(image_paths, mask_paths)
    loader = DataLoader(
        dataset,
        batch_size=int(cfg["training"]["batch_size"]),
        shuffle=True,
        num_workers=int(cfg["training"]["num_workers"]),
        collate_fn=collate,
        pin_memory=torch.cuda.is_available(),
    )

    device_cfg = cfg["training"]["device"]
    device = torch.device("cuda" if device_cfg == "auto" and torch.cuda.is_available() else "cpu")
    if device_cfg != "auto":
        device = torch.device(device_cfg)

    model = BoundaryUNet(
        in_channels=int(cfg["model"]["in_channels"]),
        out_channels=int(cfg["model"]["out_channels"]),
        base_channels=int(cfg["model"]["base_channels"]),
    ).to(device)
    loss_fn = BoundaryAwareLoss(
        boundary_weight=float(cfg["loss"]["boundary_weight"]),
        dice_weight=float(cfg["loss"]["dice_weight"]),
    ).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(cfg["training"]["learning_rate"]),
        weight_decay=float(cfg["training"]["weight_decay"]),
    )

    args.output.mkdir(parents=True, exist_ok=True)
    history = []
    epochs = int(args.epochs if args.epochs is not None else cfg["training"]["epochs"])
    for epoch in range(1, epochs + 1):
        loss = train_epoch(model, loader, loss_fn, optimizer, device)
        history.append({"epoch": epoch, "train_loss": loss})
        print(f"epoch={epoch:03d} train_loss={loss:.6f}")
        torch.save({"model": model.state_dict(), "config": cfg, "seed": seed, "epochs_run": epoch}, args.output / "last.pt")

    (args.output / "train_history.json").write_text(json.dumps(history, indent=2) + "\n")


if __name__ == "__main__":
    main()
