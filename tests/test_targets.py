import numpy as np

from bionuclei.targets import instance_to_boundary_target


def test_instance_target_shape_and_labels():
    mask = np.zeros((7, 7), dtype=np.int32)
    mask[1:4, 1:4] = 1
    mask[3:6, 3:6] = 2

    target = instance_to_boundary_target(mask, boundary_width=1)

    assert target.shape == mask.shape
    assert set(np.unique(target)).issubset({0, 1, 2})
    assert np.any(target == 2)
    assert np.all(target[mask == 0] == 0)
