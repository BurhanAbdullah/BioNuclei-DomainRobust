"""Dataset utilities for 2-D fluorescence microscopy images."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np
import tifffile
import torch
from torch.utils.data import Dataset


class InstanceMaskDataset(Dataset):
    """Dataset pairing TIFF images with integer instance-label TIFFs."""

    def __init__(self, image_paths: Sequence[str | Path], mask_paths: Sequence[str | Path]) -> None:
        if len(image_paths) != len(mask_paths):
            raise ValueError("image_paths and mask_paths must have the same length")
        self.image_paths = [Path(p) for p in image_paths]
        self.mask_paths = [Path(p) for p in mask_paths]

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        image = np.asarray(tifffile.imread(self.image_paths[index]))
        mask = np.asarray(tifffile.imread(self.mask_paths[index]))

        if image.ndim == 2:
            image = image[None, ...]
        elif image.ndim != 3:
            raise ValueError(f"Expected 2-D image or CxHxW image; got shape {image.shape}")

        if mask.ndim != 2:
            raise ValueError(f"Expected 2-D instance mask; got shape {mask.shape}")
        if image.shape[-2:] != mask.shape:
            raise ValueError(
                f"Image/mask spatial mismatch: image={image.shape}, mask={mask.shape}"
            )

        image = image.astype(np.float32, copy=False)
        scale = np.percentile(image, 99.5)
        if not np.isfinite(scale) or scale <= 0:
            scale = 1.0
        image = np.clip(image / scale, 0.0, 1.0)

        return torch.from_numpy(image), torch.from_numpy(mask.astype(np.int64, copy=False))
