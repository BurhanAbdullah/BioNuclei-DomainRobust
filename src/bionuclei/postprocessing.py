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
        foreground, structure=_CONNECTIVITY_4
    )
    if foreground_count == 0:
        return np.zeros(semantic.shape, dtype=np.int32)

    interior = semantic == 1
    markers, marker_count = ndimage.label(interior, structure=_CONNECTIVITY_8)
    if marker_count == 0:
        # Tiny nuclei can be entirely boundary class after target erosion.
        return foreground_components.astype(np.int32, copy=False)

    instances = np.zeros(semantic.shape, dtype=np.int32)
    next_fallback_label = marker_count + 1

    # Isolate each connected foreground component. A component with one
    # interior marker needs no distance transform; components with multiple
    # markers get a local nearest-marker partition. Unseeded components remain
    # distinct fallback instances.
    for component_id, component_slice in enumerate(
        ndimage.find_objects(foreground_components), start=1
    ):
        if component_slice is None:
            continue

        component_mask = foreground_components[component_slice] == component_id
        component_markers = markers[component_slice]
        marker_ids = np.unique(
            component_markers[component_mask & (component_markers > 0)]
        )
        instance_view = instances[component_slice]

        if marker_ids.size == 0:
            instance_view[component_mask] = next_fallback_label
            next_fallback_label += 1
        elif marker_ids.size == 1:
            instance_view[component_mask] = marker_ids[0]
        else:
            marker_mask = (component_markers > 0) & component_mask
            nearest_indices = ndimage.distance_transform_edt(
                ~marker_mask,
                return_distances=False,
                return_indices=True,
            )
            nearest_markers = component_markers[tuple(nearest_indices)]
            instance_view[component_mask] = nearest_markers[component_mask]

    return instances
