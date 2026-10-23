import numpy as np
import pytest
import torch
import torch.nn.functional as F
import tifffile

from bionuclei.inference import (
    _axis_tile_starts,
    _measure,
    _normalise,
    _predict_logits,
    _tile_core_ranges,
)
from bionuclei.models import BoundaryUNet


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


@pytest.mark.parametrize("length", [32, 40, 64, 320, 328, 512, 768, 1024])
def test_tile_cores_cover_each_padded_axis_pixel_exactly_once(length):
    tile_size, overlap = 320, 128
    starts = _axis_tile_starts(length, tile_size, overlap)
    assert starts[0] == 0
    assert all(start % 8 == 0 for start in starts)
    assert starts == sorted(set(starts))

    tile_length = min(tile_size, length)
    cores = _tile_core_ranges(starts, tile_length, length)
    coverage = np.zeros(length, dtype=np.uint8)
    for start, (begin, end) in zip(starts, cores, strict=True):
        assert start <= begin < end <= start + tile_length
        coverage[begin:end] += 1
    assert np.all(coverage == 1)


class _PointwiseLogits(torch.nn.Module):
    """Deterministic model that isolates tile stitching from receptive-field effects."""

    def __init__(self):
        super().__init__()
        self.conv = torch.nn.Conv2d(1, 3, kernel_size=1, bias=True)
        with torch.no_grad():
            self.conv.weight.copy_(torch.tensor([[[[0.5]]], [[[-1.0]]], [[[2.0]]]]))
            self.conv.bias.copy_(torch.tensor([0.25, -0.5, 1.0]))

    def forward(self, x):
        return self.conv(x)


@pytest.mark.parametrize("shape", [(512, 512), (319, 321), (64, 328)])
def test_tiled_logits_preserve_shape_and_exact_pointwise_predictions(shape):
    model = _PointwiseLogits().eval()
    height, width = shape
    x = torch.arange(height * width, dtype=torch.float32).reshape(1, 1, height, width)
    x = x.remainder(997).div(997.0)

    pad_height = (-height) % 8
    pad_width = (-width) % 8
    padded = F.pad(x, (0, pad_width, 0, pad_height), mode="replicate")
    with torch.inference_mode():
        expected = model(padded)[..., :height, :width]
        actual = _predict_logits(model, x, tile_size=32, overlap=16)

    assert actual.shape == (1, 3, height, width)
    assert torch.isfinite(actual).all()
    assert torch.equal(actual, expected)


def test_tiled_logits_reject_invalid_geometry_and_channels():
    model = _PointwiseLogits().eval()
    x = torch.zeros((1, 1, 64, 64))
    with pytest.raises(ValueError, match="multiples of eight"):
        _predict_logits(model, x, tile_size=31, overlap=16)
    with pytest.raises(ValueError, match="single-image, single-channel"):
        _predict_logits(model, torch.zeros((1, 2, 64, 64)), tile_size=32, overlap=16)


class _RecordingPointwiseLogits(_PointwiseLogits):
    def __init__(self):
        super().__init__()
        self.forward_shapes = []

    def forward(self, x):
        self.forward_shapes.append(tuple(x.shape[-2:]))
        return super().forward(x)


def test_default_tiling_bounds_every_512px_forward_pass():
    model = _RecordingPointwiseLogits().eval()
    x = torch.arange(512 * 512, dtype=torch.float32).reshape(1, 1, 512, 512)
    x = x.remainder(997).div(997.0)

    with torch.inference_mode():
        expected = model(x)
        model.forward_shapes.clear()
        actual = _predict_logits(model, x)

    assert actual.shape == (1, 3, 512, 512)
    assert torch.equal(actual, expected)
    assert len(model.forward_shapes) == 9
    assert all(height <= 256 and width <= 256 for height, width in model.forward_shapes)


def test_tiled_logits_match_boundary_unet_receptive_field_context():
    """Exercise the actual U-Net topology, not only pointwise stitching fixtures."""
    torch.manual_seed(17)
    model = BoundaryUNet(base_channels=2).eval()
    x = torch.linspace(0.0, 1.0, 512 * 512, dtype=torch.float32).reshape(1, 1, 512, 512)

    with torch.inference_mode():
        expected = model(x)
        actual = _predict_logits(model, x)

    assert actual.shape == expected.shape == (1, 3, 512, 512)
    torch.testing.assert_close(actual, expected, rtol=0.0, atol=1e-6)
