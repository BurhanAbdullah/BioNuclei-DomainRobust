from __future__ import annotations

import numpy as np
import pytest
import torch
from scipy import ndimage

from bionuclei.inference import _split_instances
from bionuclei.postprocessing import split_boundary_instances
from bionuclei.targets import instance_to_boundary_target
from scripts.audit_bbbc039_instances import predict_instances
from scripts.evaluate_bbbc038 import model_predict_with_padding
from scripts.evaluate_bbbc039 import split_instances as split_bbbc039
from scripts.evaluate_instance_manifest import split_instances as split_manifest
from scripts.evaluate_s_biad634 import split_instances as split_s_biad634


def _touching_boundary_map() -> np.ndarray:
    """Two adjacent nuclei with interior and boundary classes kept distinct."""
    instances = np.zeros((8, 16), dtype=np.int32)
    instances[1:7, 1:8] = 1
    instances[1:7, 8:15] = 2

    return instance_to_boundary_target(instances)


def _logits_for(classes: np.ndarray) -> torch.Tensor:
    tensor = torch.as_tensor(classes, dtype=torch.long)
    logits = torch.full((1, 3, *classes.shape), -10.0)
    logits.scatter_(1, tensor[None, None, ...], 10.0)
    return logits


def _instance_count(instances: np.ndarray) -> int:
    return int(np.unique(instances[instances > 0]).size)


def test_boundary_pixels_separate_touching_instances_and_are_reassigned() -> None:
    classes = _touching_boundary_map()

    # The old foreground-union rule collapses both nuclei into one component.
    old_component_count = ndimage.label(
        classes != 0, structure=np.ones((3, 3), dtype=np.uint8)
    )[1]
    assert old_component_count == 1

    instances = split_boundary_instances(classes)

    assert _instance_count(instances) == 2
    assert np.all(instances[classes == 0] == 0)
    assert np.all(instances[classes > 0] > 0)
    assert set(np.unique(instances[classes == 2])) == {1, 2}


def test_boundary_only_component_is_retained_as_one_instance() -> None:
    classes = np.zeros((8, 8), dtype=np.uint8)
    classes[2:6, 2:6] = 2

    instances = split_boundary_instances(classes)

    assert instances.dtype == np.int32
    assert _instance_count(instances) == 1
    assert np.all(instances[classes > 0] > 0)
    assert np.all(instances[classes == 0] == 0)


def test_disconnected_boundary_only_components_remain_separate() -> None:
    classes = np.zeros((10, 10), dtype=np.uint8)
    classes[1:3, 1:3] = 2
    classes[6:8, 6:8] = 2

    instances = split_boundary_instances(classes)

    assert _instance_count(instances) == 2


def test_unseeded_boundary_component_is_retained_alongside_seeded_nuclei() -> None:
    instances = np.zeros((12, 20), dtype=np.int32)
    instances[3:9, 3:10] = 1
    instances[3:9, 10:17] = 2
    classes = instance_to_boundary_target(instances)
    classes[0:2, 0:2] = 2

    predicted = split_boundary_instances(classes)

    assert _instance_count(predicted) == 3
    assert np.all(predicted[classes > 0] > 0)


def test_empty_map_returns_an_empty_instance_mask() -> None:
    instances = split_boundary_instances(np.zeros((4, 7), dtype=np.uint8))

    assert instances.shape == (4, 7)
    assert instances.dtype == np.int32
    assert not np.any(instances)


@pytest.mark.parametrize(
    "classes",
    [
        np.zeros((4, 4, 1), dtype=np.uint8),
        np.array([[0.0, 1.0]], dtype=np.float32),
        np.array([[0, 3]], dtype=np.uint8),
    ],
)
def test_rejects_invalid_semantic_class_maps(classes: np.ndarray) -> None:
    with pytest.raises(ValueError):
        split_boundary_instances(classes)


def test_production_and_evaluation_paths_share_boundary_aware_splitting() -> None:
    classes = _touching_boundary_map()
    logits = _logits_for(classes)
    image = np.ones(classes.shape, dtype=np.uint16)

    class FixedModel:
        def __call__(self, _image: torch.Tensor) -> torch.Tensor:
            return logits

    expected = split_boundary_instances(classes)
    outputs = [
        _split_instances(logits),
        split_bbbc039(logits),
        split_manifest(logits),
        split_s_biad634(classes),
        model_predict_with_padding(FixedModel(), image)[0],
        predict_instances(FixedModel(), image),
    ]

    for output in outputs:
        assert np.array_equal(output, expected)
        assert _instance_count(output) == 2
