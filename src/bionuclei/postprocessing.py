"""Boundary-aware semantic-to-instance post-processing."""

from __future__ import annotations

import numpy as np
from scipy import ndimage
from skimage.segmentation import watershed


_CONNECTIVITY_4 = ndimage.generate_binary_structure(2, 1)
_CONNECTIVITY_8 = np.ones((3, 3), dtype=np.uint8)


def split_boundary_instances(classes: np.ndarray) -> np.ndarray:
    """Reconstruct instance labels from {0=background, 1=interior, 2=boundary}.

    Foreground components use 4-connectivity so two nuclei that touch only
    diagonally remain distinct. Interior markers use 8-connectivity *within
    each foreground component*. Processing components independently prevents
    diagonal adjacency from merging markers belonging to separate components.

    Boundary pixels stay in the foreground mask and are assigned to watershed
    basins. A boundary-only component is retained as one fallback instance,
    since target erosion can leave very small nuclei without interior pixels.
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

    instances = np.zeros(semantic.shape, dtype=np.int32)
    next_instance_label = 1

    # Label and watershed each 4-connected component independently. Global
    # 8-connected marker labeling would merge distinct components that touch
    # only at a diagonal before watershed can preserve their identities.
    for component_id, component_slice in enumerate(
        ndimage.find_objects(foreground_components), start=1
    ):
        if component_slice is None:
            continue

        component_mask = foreground_components[component_slice] == component_id
        component_interior = (
            (semantic[component_slice] == 1) & component_mask
        )
        markers, marker_count = ndimage.label(
            component_interior, structure=_CONNECTIVITY_8
        )
        instance_view = instances[component_slice]

        if marker_count == 0:
            # Tiny nuclei can be entirely boundary class after target erosion.
            instance_view[component_mask] = next_instance_label
            next_instance_label += 1
            continue

        if marker_count == 1:
            # Avoid allocating watershed/distance buffers for the common case.
            instance_view[component_mask] = next_instance_label
            next_instance_label += 1
            continue

        distance = ndimage.distance_transform_edt(
            component_interior
        ).astype(np.float32, copy=False)
        local_instances = watershed(
            -distance,
            markers,
            mask=component_mask,
            connectivity=_CONNECTIVITY_8,
            watershed_line=False,
        )
        instance_view[component_mask] = (
            local_instances[component_mask] + next_instance_label - 1
        )
        next_instance_label += marker_count

    return instances
