"""Dataset utilities for 2-D fluorescence microscopy images."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np
import tifffile
import torch
from skimage.io import imread
from torch.utils.data import Dataset


def decode_instance_mask(mask: np.ndarray) -> np.ndarray:
    """Decode a BBBC039-style PNG color mask into integer instance labels.

    BBBC039 masks encode touching nuclei using distinct colors. Background is
    treated as zero. Grayscale integer masks are accepted unchanged.
    """
    if mask.ndim == 2:
        return mask.astype(np.int64, copy=False)
    if mask.ndim != 3 or mask.shape[-1] not in (3, 4):
        raise ValueError(f"Expected 2-D or RGB/RGBA mask; got shape {mask.shape}")

    rgb = mask[..., :3]
    colors, inverse = np.unique(rgb.reshape(-1, 3), axis=0, return_inverse=True)
    labels = np.zeros(inverse.shape[0], dtype=np.int64)
    next_label = 1
    for color_index, color in enumerate(colors):
        if np.all(color == 0):
            continue
        labels[inverse == color_index] = next_label
        next_label += 1
    return labels.reshape(mask.shape[:2])


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
