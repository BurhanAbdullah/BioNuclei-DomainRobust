"""Boundary-aware semantic-to-instance post-processing."""

from __future__ import annotations

import numpy as np
from scipy import ndimage
from skimage.segmentation import watershed


_CONNECTIVITY_8 = np.ones((3, 3), dtype=np.uint8)


def split_boundary_instances(classes: np.ndarray) -> np.ndarray:
    """Reconstruct instance labels from {0=background, 1=interior, 2=boundary}.

    Interior components are the instance markers. Predicted boundary pixels
    remain inside the foreground mask and are assigned to their nearest marker
    by watershed, so touching nuclei stay separate without discarding their
    boundary pixels. Boundary-only components have no interior evidence and
    therefore remain unlabelled.
    """
    semantic = np.asarray(classes)
    if semantic.ndim != 2:
        raise ValueError(f"Expected a 2-D semantic class map; got shape {semantic.shape}")
    if not np.issubdtype(semantic.dtype, np.integer):
        raise ValueError(f"Expected integer semantic classes; got dtype {semantic.dtype}")
    if np.any((semantic < 0) | (semantic > 2)):
        raise ValueError("Expected semantic class values in {0, 1, 2}")

    foreground = semantic != 0
    interior = semantic == 1
    markers, marker_count = ndimage.label(interior, structure=_CONNECTIVITY_8)
    if marker_count == 0:
        return np.zeros(semantic.shape, dtype=np.int32)

    distance = ndimage.distance_transform_edt(interior).astype(np.float32, copy=False)
    instances = watershed(
        -distance,
        markers,
        mask=foreground,
        connectivity=_CONNECTIVITY_8,
        watershed_line=False,
    )
    return instances.astype(np.int32, copy=False)
