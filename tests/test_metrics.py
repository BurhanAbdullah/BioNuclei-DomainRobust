import numpy as np
import pytest

from bionuclei.metrics import aji_score
from scripts.metrics_instance import aji_score as script_aji_score, instance_prf


def test_aji_perfect_instance_masks_is_one():
    target = np.array([[0, 1, 1, 0], [2, 2, 0, 0]], dtype=np.int32)
    pred = target.copy()
    assert aji_score(pred, target) == pytest.approx(1.0)
    assert script_aji_score(pred, target) == pytest.approx(1.0)


def test_aji_is_zero_when_instances_do_not_overlap():
    target = np.array([[1, 1, 0, 0]], dtype=np.int32)
    pred = np.array([[0, 0, 2, 2]], dtype=np.int32)
    assert aji_score(pred, target) == pytest.approx(0.0)
    assert script_aji_score(pred, target) == pytest.approx(0.0)


def test_aji_penalizes_unmatched_extra_prediction():
    target = np.array([[1, 1, 0, 0]], dtype=np.int32)
    pred = np.array([[2, 2, 3, 3]], dtype=np.int32)
    assert aji_score(pred, target) == pytest.approx(0.5)
    assert script_aji_score(pred, target) == pytest.approx(0.5)


def test_aji_handles_noncontiguous_labels_and_empty_masks():
    target = np.array([[0, 10, 10], [0, 30, 0]], dtype=np.int32)
    pred = np.array([[0, 4, 4], [0, 9, 0]], dtype=np.int32)
    assert aji_score(pred, target) == pytest.approx(1.0)
    assert script_aji_score(pred, target) == pytest.approx(1.0)
    assert aji_score(np.zeros_like(target), np.zeros_like(target)) == pytest.approx(1.0)


def test_aji_rejects_shape_mismatch():
    with pytest.raises(ValueError, match="Shape mismatch"):
        aji_score(np.zeros((2, 2), dtype=np.int32), np.zeros((2, 3), dtype=np.int32))
    with pytest.raises(ValueError, match="Shape mismatch"):
        script_aji_score(np.zeros((2, 2), dtype=np.int32), np.zeros((2, 3), dtype=np.int32))


def test_aji_uses_instance_labels_when_touching_instances_share_one_component():
    # Two touching ground-truth instances must remain two instances even though
    # their foreground union is a single 8-connected component. A prediction
    # that merges them into one object is therefore penalized by AJI.
    target = np.array([[1, 1, 2, 2]], dtype=np.int32)
    pred = np.array([[7, 7, 7, 7]], dtype=np.int32)
    assert aji_score(pred, target) == pytest.approx(1.0 / 3.0)
    assert script_aji_score(pred, target) == pytest.approx(1.0 / 3.0)


def test_instance_prf_counts_strictly_subthreshold_split_prediction_as_fp_and_fn():
    # With a 0.51 threshold, each half of a two-instance split prediction has
    # IoU 0.5 against the sole target and therefore neither may be matched.
    target = np.array([[1, 1, 1, 1]], dtype=np.int32)
    pred = np.array([[2, 2, 3, 3]], dtype=np.int32)
    result = instance_prf(pred, target, iou_threshold=0.51)
    assert result["tp"] == 0
    assert result["fp"] == 2
    assert result["fn"] == 1
    assert result["precision"] == pytest.approx(0.0)
    assert result["recall"] == pytest.approx(0.0)
    assert result["f1_score"] == pytest.approx(0.0)


def test_instance_prf_matches_noncontiguous_instance_labels():
    target = np.array([[0, 10, 10, 0], [20, 20, 0, 0]], dtype=np.int32)
    pred = np.array([[0, 3, 3, 0], [7, 7, 0, 0]], dtype=np.int32)
    result = instance_prf(pred, target, iou_threshold=0.5)
    assert result["tp"] == 2
    assert result["fp"] == 0
    assert result["fn"] == 0
    assert result["f1_score"] == pytest.approx(1.0)
