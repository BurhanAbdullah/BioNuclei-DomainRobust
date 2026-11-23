import numpy as np

from bionuclei.decode import connected_instances, decode_instances, seeded_instances


def _disc(shape, center, radius):
    yy, xx = np.ogrid[: shape[0], : shape[1]]
    return (yy - center[0]) ** 2 + (xx - center[1]) ** 2 <= radius ** 2


def _classes_for(masks, shape):
    classes = np.zeros(shape, dtype=np.uint8)
    for m in masks:
        classes[m] = 1
    from scipy import ndimage
    for m in masks:
        edge = m & ~ndimage.binary_erosion(m)
        classes[edge] = 2
    return classes


def test_touching_nuclei_are_split_by_the_boundary_class():
    shape = (80, 120)
    a, b = _disc(shape, (40, 40), 20), _disc(shape, (40, 78), 20)
    classes = _classes_for([a, b], shape)
    assert connected_instances(classes).max() == 1  # published decoder merges them
    assert seeded_instances(classes).max() == 2


def test_holes_are_filled_and_specks_dropped():
    shape = (100, 100)
    a = _disc(shape, (50, 50), 25)
    classes = _classes_for([a], shape)
    classes[48:53, 48:53] = 0          # dark nucleolus hole
    classes[5, 5] = 1                   # one-pixel speck
    classes[90:92, 90:92] = 2           # tiny boundary-only fragment
    out = seeded_instances(classes)
    assert out.max() == 1
    assert out[50, 50] == 1
    assert out[5, 5] == 0 and out[91, 91] == 0


def test_boundary_only_nucleus_is_not_lost():
    shape = (60, 60)
    classes = np.zeros(shape, dtype=np.uint8)
    classes[_disc(shape, (30, 30), 15)] = 2
    assert seeded_instances(classes).max() == 1


def test_empty_and_unknown_decoder():
    assert seeded_instances(np.zeros((10, 10), np.uint8)).max() == 0
    import pytest
    with pytest.raises(ValueError):
        decode_instances(np.zeros((4, 4), np.uint8), "nope")
