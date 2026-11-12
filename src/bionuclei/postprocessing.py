"""Boundary-aware semantic-to-instance post-processing."""

from __future__ import annotations

import numpy as np
from scipy import ndimage


_CONNECTIVITY_4 = ndimage.generate_binary_structure(2, 1)
_CONNECTIVITY_8 = np.ones((3, 3), dtype=np.uint8)


def split_boundary_instances(classes: np.ndarray) -> np.ndarray:
    """Reconstruct instance labels from {0=background, 1=interior, 2=boundary}.

    Interior components are the instance markers. Boundary pixels in each
    4-connected foreground component are assigned to their nearest interior
    marker using SciPy's compiled Euclidean distance transform. Processing
    one component at a time avoids the Python priority queue used by
    scikit-image watershed and bounds temporary index arrays to that
    component's bounding box, which matters under the public worker's 480 MiB
    memory ceiling.

    Boundary-only components use 4-connectivity: two tiny nuclei that touch
    only diagonally must not be merged merely because target erosion left
    both without interior markers. This fallback is necessarily conservative
    because a diagonal-only single object is ambiguous without an interior
    marker.
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
    foreground_components, foreground_count = ndimage.label(
        foreground,
        structure=_CONNECTIVITY_4,
    )
    if foreground_count == 0:
        return np.zeros(semantic.shape, dtype=np.int32)

    instances = np.zeros(semantic.shape, dtype=np.int32)
    next_instance_label = 1
    for component_id, component_slice in enumerate(
        ndimage.find_objects(foreground_components),
        start=1,
    ):
        if component_slice is None:
            continue
        component_mask = foreground_components[component_slice] == component_id
        instance_view = instances[component_slice]

        # Label interior markers within this foreground component, not globally.
        # Global 8-connectivity can join markers from two distinct 4-connected
        # foreground components that touch only at a diagonal, assigning both
        # nuclei the same instance ID.
        component_interior = (semantic[component_slice] == 1) & component_mask
        component_markers, marker_count = ndimage.label(
            component_interior,
            structure=_CONNECTIVITY_8,
        )
        if marker_count == 0:
            instance_view[component_mask] = next_instance_label
            next_instance_label += 1
            continue
        if marker_count == 1:
            instance_view[component_mask] = next_instance_label
            next_instance_label += 1
            continue

        marker_mask = component_markers > 0
        nearest_indices = ndimage.distance_transform_edt(
            ~marker_mask,
            return_distances=False,
            return_indices=True,
        )
        nearest_markers = component_markers[tuple(nearest_indices)]
        instance_view[component_mask] = (
            nearest_markers[component_mask] + next_instance_label - 1
        )
        next_instance_label += marker_count

    return instances
