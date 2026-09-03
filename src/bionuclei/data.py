"""Dataset utilities for 2-D fluorescence microscopy images."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np
import tifffile
import torch
from skimage.io import imread
from skimage.morphology import label
from torch.utils.data import Dataset


def decode_instance_mask(mask: np.ndarray) -> np.ndarray:
    """Decode color/grayscale instance masks into integer instance labels.

    RGB/RGBA masks encode instances by color. Each exact RGB color is labeled
    independently by connected component so adjacent nuclei with different
    colors remain separate, while repeated colors in disconnected regions are
    still assigned distinct instance IDs.
    """
    if mask.ndim == 2:
        return mask.astype(np.int64, copy=False)
    if mask.ndim != 3 or mask.shape[-1] not in (3, 4):
        raise ValueError(f"Expected 2-D or RGB/RGBA mask; got shape {mask.shape}")

    rgb = np.asarray(mask[..., :3])
    decoded = np.zeros(rgb.shape[:2], dtype=np.int64)
    next_id = 1
    for color in np.unique(rgb.reshape(-1, 3), axis=0):
        if np.all(color == 0):
            continue
        color_mask = np.all(rgb == color, axis=-1)
        components = label(color_mask, connectivity=2)
        n_components = int(components.max())
        if n_components == 0:
            continue
        decoded[components > 0] = components[components > 0] + next_id - 1
        next_id += n_components
    return decoded


class InstanceMaskDataset(Dataset):
    """Dataset pairing TIFF fluorescence images with PNG/TIFF instance masks."""

    def __init__(self, image_paths: Sequence[str | Path], mask_paths: Sequence[str | Path]) -> None:
        if len(image_paths) != len(mask_paths):
            raise ValueError("image_paths and mask_paths must have the same length")
        self.image_paths = [Path(p) for p in image_paths]
        self.mask_paths = [Path(p) for p in mask_paths]

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        image = np.asarray(tifffile.imread(self.image_paths[index]))
        mask = np.asarray(imread(self.mask_paths[index]))
        mask = decode_instance_mask(mask)

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
