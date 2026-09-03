import numpy as np
import pytest

from bionuclei.metrics import aji_score


def test_aji_perfect_instance_masks_is_one():
    target = np.array([[0, 1, 1, 0], [2, 2, 0, 0]], dtype=np.int32)
    pred = target.copy()
    assert aji_score(pred, target) == pytest.approx(1.0)


def test_aji_is_zero_when_instances_do_not_overlap():
    target = np.array([[1, 1, 0, 0]], dtype=np.int32)
    pred = np.array([[0, 0, 2, 2]], dtype=np.int32)
    assert aji_score(pred, target) == pytest.approx(0.0)


def test_aji_penalizes_unmatched_extra_prediction():
    target = np.array([[1, 1, 0, 0]], dtype=np.int32)
    pred = np.array([[2, 2, 3, 3]], dtype=np.int32)
    # Matched pair contributes intersection 2 / union 2; extra prediction
    # contributes 2 to the denominator, giving 2 / 4.
    assert aji_score(pred, target) == pytest.approx(0.5)


def test_aji_handles_noncontiguous_labels_and_empty_masks():
    target = np.array([[0, 10, 10], [0, 30, 0]], dtype=np.int32)
    pred = np.array([[0, 4, 4], [0, 9, 0]], dtype=np.int32)
    assert aji_score(pred, target) == pytest.approx(1.0)
    assert aji_score(np.zeros_like(target), np.zeros_like(target)) == pytest.approx(1.0)


def test_aji_rejects_shape_mismatch():
    with pytest.raises(ValueError, match="Shape mismatch"):
        aji_score(np.zeros((2, 2), dtype=np.int32), np.zeros((2, 3), dtype=np.int32))
