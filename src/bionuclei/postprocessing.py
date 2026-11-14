"""Boundary-aware semantic-to-instance post-processing."""

from __future__ import annotations

import numpy as np
from scipy import ndimage
from skimage.segmentation import watershed


_CONNECTIVITY_4 = ndimage.generate_binary_structure(2, 1)
_CONNECTIVITY_8 = np.ones((3, 3), dtype=np.uint8)


def split_boundary_instances(classes: np.ndarray) -> np.ndarray:
    """Reconstruct instance labels from {0=background, 1=interior, 2=boundary}.

    Interior components are the instance markers. Predicted boundary pixels
    remain inside the foreground mask and are partitioned into marker basins
    by watershed, so touching nuclei stay separate without discarding their
    boundary pixels. Boundary-only fallback components use 4-connectivity:
    two tiny nuclei that touch only diagonally must not be merged merely
    because target erosion left both without interior markers. This fallback
    is necessarily conservative because a diagonal-only single object is
    ambiguous without an interior marker.
    """
    semantic = np.asarray(classes)
    if semantic.ndim != 2:
        raise ValueError(
            f"Expected a 2-D semantic class map; got shape {semantic.shape}"
        )
    if not np.issubdtype(semantic.dtype, np.integer):
        raise ValueError(
            f"Expected integer semantic classes; got dtype {semantic.dtype}"
        )
    if np.any((semantic < 0) | (semantic > 2)):
        raise ValueError("Expected semantic class values in {0, 1, 2}")

    foreground = semantic != 0
    # Use 4-connectivity for fallback component identity. Interior markers and
    # watershed retain 8-connectivity so seeded, diagonally connected regions
    # are not fragmented by the fallback policy.
    foreground_components, foreground_count = ndimage.label(
        foreground, structure=_CONNECTIVITY_4
    )
    if foreground_count == 0:
        return np.zeros(semantic.shape, dtype=np.int32)

    interior = semantic == 1
    markers, marker_count = ndimage.label(interior, structure=_CONNECTIVITY_8)
    if marker_count == 0:
        # Tiny nuclei can be entirely boundary class after target erosion.
        return foreground_components.astype(np.int32, copy=False)

    distance = ndimage.distance_transform_edt(interior).astype(np.float32, copy=False)
    instances = watershed(
        -distance,
        markers,
        mask=foreground,
        connectivity=_CONNECTIVITY_8,
        watershed_line=False,
    )

    # Keep unseeded boundary-only components as single objects. Components
    # that touch seeded regions only diagonally remain independent.
    seeded_components = np.zeros(foreground_count + 1, dtype=bool)
    seeded_components[np.unique(foreground_components[markers > 0])] = True
    unseeded_components = np.flatnonzero(~seeded_components[1:]) + 1
    if unseeded_components.size:
        fallback_labels = np.zeros(foreground_count + 1, dtype=np.int32)
        fallback_labels[unseeded_components] = np.arange(
            marker_count + 1,
            marker_count + unseeded_components.size + 1,
            dtype=np.int32,
        )
        fallback_mask = (foreground_components > 0) & ~seeded_components[foreground_components]
        instances[fallback_mask] = fallback_labels[foreground_components[fallback_mask]]

    return instances.astype(np.int32, copy=False)
