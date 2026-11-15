from __future__ import annotations

import numpy as np
import pytest

from bionuclei.targets import instance_to_boundary_target
from scripts.evaluate_s_biad634 import semantic_to_instances
from scripts.metrics_instance import instance_prf


def test_boundary_pixels_are_reassigned_and_small_instances_remain_matchable() -> None:
    instances = np.zeros((7, 9), dtype=np.int32)
    instances[2:5, 1:4] = 10
    instances[2:5, 4:7] = 30

    semantic = instance_to_boundary_target(instances)
    predicted = semantic_to_instances(semantic)
    metrics = instance_prf(predicted, instances, iou_threshold=0.5)

    assert np.array_equal(predicted > 0, instances > 0)
    assert np.unique(predicted[predicted > 0]).size == 2
    assert metrics["tp"] == 2
    assert metrics["fp"] == 0
    assert metrics["fn"] == 0
    assert metrics["f1_score"] == pytest.approx(1.0)


def test_boundary_only_component_is_retained_as_an_instance() -> None:
    semantic = np.full((2, 3), 2, dtype=np.uint8)

    predicted = semantic_to_instances(semantic)

    assert np.all(predicted > 0)
    assert np.unique(predicted).size == 1


def test_diagonally_touching_interiors_use_training_four_connectivity() -> None:
    semantic = np.array([[1, 0], [0, 1]], dtype=np.uint8)

    predicted = semantic_to_instances(semantic)

    assert np.unique(predicted[predicted > 0]).size == 2


def test_diagonally_touching_boundary_only_nuclei_remain_separate() -> None:
    instances = np.zeros((5, 5), dtype=np.int32)
    instances[1:3, 1:3] = 10
    instances[3:5, 3:5] = 30

    semantic = instance_to_boundary_target(instances)
    assert not np.any(semantic == 1)

    predicted = semantic_to_instances(semantic)

    assert np.unique(predicted[predicted > 0]).size == 2
    assert np.all(predicted[semantic > 0] > 0)


def test_empty_semantic_mask_returns_no_instances() -> None:
    predicted = semantic_to_instances(np.zeros((4, 5), dtype=np.uint8))

    assert predicted.dtype == np.int32
    assert np.count_nonzero(predicted) == 0


@pytest.mark.parametrize(
    "semantic",
    [
        np.zeros((1, 2, 3), dtype=np.uint8),
        np.array([[0, 3]], dtype=np.uint8),
        np.array([[0.0, 1.0]], dtype=np.float32),
    ],
)
def test_invalid_semantic_masks_are_rejected(semantic: np.ndarray) -> None:
    with pytest.raises(ValueError):
        semantic_to_instances(semantic)
