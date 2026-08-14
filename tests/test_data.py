import numpy as np

from bionuclei.data import decode_instance_mask


def test_decode_instance_mask_assigns_distinct_labels_to_colors():
    mask = np.zeros((4, 4, 3), dtype=np.uint8)
    mask[0:2, 0:2] = (255, 0, 0)
    mask[2:4, 2:4] = (0, 255, 0)

    decoded = decode_instance_mask(mask)

    assert decoded.shape == (4, 4)
    assert decoded[0, 0] > 0
    assert decoded[2, 2] > 0
    assert decoded[0, 0] != decoded[2, 2]
    assert decoded[3, 0] == 0


def test_decode_instance_mask_preserves_grayscale_instances():
    mask = np.array([[0, 1], [2, 2]], dtype=np.uint16)
    decoded = decode_instance_mask(mask)
    np.testing.assert_array_equal(decoded, mask)
