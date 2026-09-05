"""Dataset utilities for 2-D fluorescence microscopy images."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np
import tifffile
import torch
from skimage.io import imread
from torch.utils.data import Dataset

from bionuclei.masks import decode_instance_mask


def read_fluorescence_image(path: str | Path) -> np.ndarray:
    """Read a supported microscopy image without changing TIFF behavior.

    BBBC039 uses TIFF input; Aitslab-bioimaging1 publishes normalized 8-bit
    grayscale PNG input.  TIFFs remain on tifffile for reproducibility, while
    non-TIFF image formats are read through skimage.  E6 is deliberately
    fail-closed for multi-channel external images because the frozen E4 model
    is a single-channel fluorescence model and silently collapsing channels
    would change the preregistered scientific protocol.
    """
    path = Path(path)
    if path.suffix.lower() in (".tif", ".tiff"):
        image = np.asarray(tifffile.imread(path))
    else:
        image = np.asarray(imread(path))

    if image.ndim == 3 and image.shape[-1] in (3, 4):
        raise ValueError(
            f"Expected single-channel fluorescence input; got channel-last image "
            f"shape {image.shape} for {path}"
        )
    return image


class InstanceMaskDataset(Dataset):
    """Dataset pairing fluorescence images with PNG/TIFF instance masks."""

    def __init__(self, image_paths: Sequence[str | Path], mask_paths: Sequence[str | Path]) -> None:
        if len(image_paths) != len(mask_paths):
            raise ValueError("image_paths and mask_paths must have the same length")
        self.image_paths = [Path(p) for p in image_paths]
        self.mask_paths = [Path(p) for p in mask_paths]

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        image = read_fluorescence_image(self.image_paths[index])
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
