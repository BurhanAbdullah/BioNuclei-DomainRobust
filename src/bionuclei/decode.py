"""Turn the Boundary U-Net class map into labelled nucleus instances.

The network predicts three classes per pixel: 0 background, 1 nucleus
interior and 2 nucleus boundary. Two decoders are kept here.

``connected`` labels every non-background pixel by 8-connectivity. This is the
decoder used for the published BBBC039 / S-BIAD634 evidence, so it stays
available for reproducing those numbers.

``seeded`` is the product decoder. It places one seed per nucleus at the peaks
of the distance map of the interior class, so the boundary class separates
touching nuclei. Each seed is grown back over the full nucleus, holes left by
dark nucleoli are filled, and specks far smaller than the typical nucleus in
the image are dropped. On real 16-bit DAPI images the connected
decoder reports many 1-10 pixel fragments and nuclei with holes; the seeded
decoder does not.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage
from skimage.morphology import h_maxima
from skimage.segmentation import watershed

DECODERS = ("connected", "seeded")
PRODUCT_DECODER = "seeded"

_EIGHT = np.ones((3, 3), dtype=np.uint8)
MIN_OBJECT_PX = 30
RELATIVE_MIN = 0.10
SEED_H = 0.3


def connected_instances(classes: np.ndarray) -> np.ndarray:
    """Label every non-background pixel by 8-connectivity (published decoder)."""
    instances, _ = ndimage.label(classes != 0, structure=_EIGHT)
    return instances.astype(np.int32)


def _size_floor(areas: np.ndarray) -> int:
    """Smallest object kept: 30 px, or 10% of the median of plausible objects."""
    plausible = areas[areas >= MIN_OBJECT_PX]
    if plausible.size == 0:
        return MIN_OBJECT_PX
    return max(MIN_OBJECT_PX, int(RELATIVE_MIN * float(np.median(plausible))))


def seeded_instances(classes: np.ndarray) -> np.ndarray:
    """One seed per nucleus from distance-map peaks, grown over the filled foreground.

    Seeds come from the interior class only, so the predicted boundary band
    separates touching nuclei. Peaks must rise ``SEED_H`` x the typical nucleus
    radius above their surroundings, which stops one textured nucleus (dark
    nucleoli, uneven chromatin) from being cut into several pieces.
    """
    foreground = ndimage.binary_fill_holes(classes != 0)
    if not foreground.any():
        return np.zeros(classes.shape, dtype=np.int32)

    regions, _ = ndimage.label(foreground, structure=_EIGHT)
    region_areas = np.bincount(regions.ravel())[1:]
    plausible = region_areas[region_areas >= MIN_OBJECT_PX]
    radius = float(np.sqrt(np.median(plausible) / np.pi)) if plausible.size else 5.0

    interior = ndimage.binary_fill_holes(classes == 1) & foreground
    distance = ndimage.gaussian_filter(ndimage.distance_transform_edt(interior), 1.0)
    peaks = h_maxima(distance, max(1.0, SEED_H * radius))
    markers, _ = ndimage.label(peaks, structure=_EIGHT)

    # Foreground regions with no seed still become one object each, so a
    # nucleus predicted only as boundary is not silently lost.
    seeded_regions = np.unique(regions[markers > 0])
    orphans = np.isin(regions, seeded_regions, invert=True) & foreground
    if orphans.any():
        extra, _ = ndimage.label(orphans, structure=_EIGHT)
        markers = np.where(extra > 0, extra + int(markers.max()), markers)

    grown = watershed(-ndimage.distance_transform_edt(foreground), markers=markers, mask=foreground)

    areas = np.bincount(grown.ravel())
    floor = _size_floor(areas[1:][areas[1:] > 0])
    out = np.zeros(classes.shape, dtype=np.int32)
    next_label = 0
    for index, region in enumerate(ndimage.find_objects(grown), start=1):
        if region is None or areas[index] < floor:
            continue
        mask = ndimage.binary_fill_holes(grown[region] == index)
        next_label += 1
        out[region][mask & (out[region] == 0)] = next_label
    return out


def decode_instances(classes: np.ndarray, decoder: str = PRODUCT_DECODER) -> np.ndarray:
    if decoder == "connected":
        return connected_instances(classes)
    if decoder == "seeded":
        return seeded_instances(classes)
    raise ValueError(f"Unknown decoder {decoder!r}; choose one of {DECODERS}")
