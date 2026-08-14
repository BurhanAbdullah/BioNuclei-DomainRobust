"""Utilities for converting instance masks to boundary-aware targets."""

from __future__ import annotations

import numpy as np
from scipy import ndimage


def instance_to_boundary_target(
    instance_mask: np.ndarray,
    boundary_width: int = 1,
) -> np.ndarray:
    """Convert an integer instance mask to {background, interior, boundary}.

    Label 0 is treated as background. Every positive integer label is treated as
    one nucleus. A boundary band is carved out between touching/adjacent instances
    by testing each nucleus against a binary erosion of itself.

    Returns
    -------
    target : np.ndarray
        Integer array with values 0=background, 1=interior, 2=boundary.
    """
    if instance_mask.ndim != 2:
        raise ValueError("instance_mask must be a 2-D array")
    if boundary_width < 1:
        raise ValueError("boundary_width must be >= 1")

    target = np.zeros(instance_mask.shape, dtype=np.uint8)
    foreground = instance_mask > 0
    target[foreground] = 1

    structure = ndimage.generate_binary_structure(2, 1)
    if boundary_width > 1:
        for _ in range(boundary_width - 1):
            structure = ndimage.iterate_structure(structure, 2)

    labels = np.unique(instance_mask)
    labels = labels[labels != 0]
    for label in labels:
        nucleus = instance_mask == label
        eroded = ndimage.binary_erosion(nucleus, structure=structure, border_value=0)
        boundary = nucleus & ~eroded
        target[boundary] = 2

    return target
