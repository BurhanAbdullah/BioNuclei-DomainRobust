import numpy as np

from scripts.profile_s_biad634 import stats


def test_stats_profiles_rgb_image_and_decodes_rgb_mask():
    image = np.zeros((4, 5, 3), dtype=np.uint8)
    image[..., 0] = np.arange(20, dtype=np.uint8).reshape(4, 5)
    image[..., 1] = 10
    image[..., 2] = 20

    mask = np.zeros((4, 5, 3), dtype=np.uint8)
    mask[0:2, 0:2] = (255, 0, 0)
    mask[2:4, 3:5] = (0, 255, 0)

    record = stats(image, mask)

    assert record["shape"] == [4, 5, 3]
    assert record["channel_count"] == 3
    assert record["channel_axis"] == -1
    assert len(record["channel_stats"]) == 3
    assert record["mask_shape"] == [4, 5, 3]
    assert record["annotation_objects"] == 2
    assert record["annotation_foreground_fraction"] == 8 / 20


def test_stats_rejects_spatial_mismatch_after_mask_decoding():
    image = np.zeros((4, 5, 3), dtype=np.uint8)
    mask = np.zeros((3, 5, 3), dtype=np.uint8)

    try:
        stats(image, mask)
    except ValueError as exc:
        assert "shape mismatch" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError for image/mask spatial mismatch")
