"""Instance-mask decoding utilities with no model-framework dependency."""

from __future__ import annotations

import numpy as np
from skimage.morphology import label


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
