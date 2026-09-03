import numpy as np
import torch
import tifffile

from bionuclei.inference import _measure, _normalise


def test_normalise_is_finite_and_bounded():
    image = np.array([[0, 1], [10, 20]], dtype=np.uint16)
    x = _normalise(image)
    assert x.dtype == np.float32
    assert np.isfinite(x).all()
    assert x.min() >= 0
    assert x.max() <= 1


def test_measure_reports_instances():
    instances = np.array([[0, 1, 1], [0, 0, 2], [2, 2, 0]], dtype=np.int32)
    rows = _measure(instances)
    assert len(rows) == 2
    assert rows[0]["instance_id"] == 1
    assert rows[0]["area_pixels"] == 2
    assert rows[1]["instance_id"] == 2
    assert rows[1]["area_pixels"] == 3
