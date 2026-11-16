from pathlib import Path

import numpy as np
import tifffile

from bionuclei.adaptive_agent import CNNPatternCheck, build_plan, inspect_image, to_dict


def test_adaptive_plan_flags_flat_image(tmp_path: Path) -> None:
    path = tmp_path / "flat.tif"
    tifffile.imwrite(path, np.zeros((32, 32), dtype=np.uint16))
    plan = build_plan(path)
    assert plan.status == "BLOCKED"
    assert any("no usable intensity variation" in warning.lower() for warning in plan.warnings)
    assert to_dict(plan)["profile"]["shape"] == [32, 32]


def test_adaptive_plan_accepts_nonflat_image_when_cnn_gate_passes(tmp_path: Path, monkeypatch) -> None:
    image = np.zeros((32, 32), dtype=np.uint16)
    image[8:24, 8:24] = 1000
    path = tmp_path / "image.tif"
    tifffile.imwrite(path, image)
    monkeypatch.setattr(
        "bionuclei.adaptive_agent.cnn_pattern_check",
        lambda _path: CNNPatternCheck(True, "Boundary U Net", 0.25, 0.9, 0.2, 1, "PASS", ()),
    )
    plan = build_plan(path, {"nuclei", "morphology"})
    assert plan.status in {"READY", "CAUTION"}
    assert plan.recommended_modules == ("morphology", "nuclei")


def test_adaptive_plan_fails_closed_when_checkpoint_is_unavailable(tmp_path: Path, monkeypatch) -> None:
    image = np.zeros((32, 32), dtype=np.uint16)
    image[8:24, 8:24] = 1000
    path = tmp_path / "image.tif"
    tifffile.imwrite(path, image)
    monkeypatch.setattr(
        "bionuclei.adaptive_agent.cnn_pattern_check",
        lambda _path: CNNPatternCheck(
            False, "Boundary U Net", 0.0, 0.0, 0.0, 0, "NOT_RUN",
            ("Released checkpoint is not available for the CNN gate.",),
        ),
    )
    plan = build_plan(path)
    assert plan.status == "BLOCKED"
    assert any("checkpoint is not available" in warning.lower() for warning in plan.warnings)


def test_cnn_preflight_downsamples_large_image_and_uses_frozen_weights(tmp_path: Path, monkeypatch) -> None:
    import torch
    import bionuclei.inference

    image = np.full((512, 512), 512, dtype=np.uint16)
    image[120:392, 120:392] = 8192
    path = tmp_path / "large.tif"
    tifffile.imwrite(path, image)
    checkpoint = tmp_path / "checkpoint.pt"
    checkpoint.write_bytes(b"test checkpoint placeholder")
    monkeypatch.setenv("BIONUCLEI_CHECKPOINT", str(checkpoint))
    seen_shapes = []
    events = []

    class TrackingLock:
        def __init__(self):
            self.held = False

        def __enter__(self):
            assert not self.held
            self.held = True
            events.append("acquire")
            return self

        def __exit__(self, exc_type, exc, traceback):
            events.append("release")
            self.held = False
            return False

    lock = TrackingLock()
    monkeypatch.setattr(bionuclei.inference, "_INFERENCE_LOCK", lock)

    class FakeModel:
        def __del__(self):
            events.append("model_cleanup")

        def __call__(self, x):
            seen_shapes.append(tuple(x.shape))
            logits = torch.zeros((1, 3, x.shape[-2], x.shape[-1]))
            logits[:, 0] = 4.0
            logits[:, 1, x.shape[-2] // 4 : 3 * x.shape[-2] // 4,
                   x.shape[-1] // 4 : 3 * x.shape[-1] // 4] = 8.0
            return logits

    loader_calls = []

    def fake_load_model(checkpoint_path, device):
        assert lock.held is True
        assert checkpoint_path == checkpoint
        assert device == "cpu"
        loader_calls.append((checkpoint_path, device))
        events.append("load")
        return FakeModel()

    monkeypatch.setattr(bionuclei.inference, "_load_model", fake_load_model)
    result = __import__("bionuclei.adaptive_agent", fromlist=["cnn_pattern_check"]).cnn_pattern_check(path)
    assert result.executed is True
    assert result.status == "PASS"
    assert seen_shapes == [(1, 1, 192, 192)]
    assert loader_calls == [(checkpoint, "cpu")]
    assert events == ["acquire", "load", "model_cleanup", "release"]
    assert lock.held is False


def test_uint16_image_profile_preserves_full_range_and_statistics(tmp_path: Path, monkeypatch) -> None:
    image = np.array(
        [
            [0, 1, 512, 1024],
            [2048, 4096, 8192, 16384],
            [32768, 49152, 65534, 65535],
        ],
        dtype=np.uint16,
    )
    path = tmp_path / "uint16-profile.tif"
    tifffile.imwrite(path, image)

    real_percentile = np.percentile
    percentile_calls = []

    def record_percentile(values, quantiles, *args, **kwargs):
        percentile_calls.append(quantiles)
        return real_percentile(values, quantiles, *args, **kwargs)

    monkeypatch.setattr("bionuclei.adaptive_agent.np.percentile", record_percentile)
    profile = inspect_image(path)

    reference = image.astype(np.float64).reshape(-1)
    expected_p01, expected_median, expected_p995 = real_percentile(
        reference, (1.0, 50.0, 99.5)
    )
    assert profile.finite is True
    assert profile.dtype == "uint16"
    assert profile.min == float(reference.min())
    assert profile.max == float(reference.max()) == 65535.0
    assert profile.p01 == float(expected_p01)
    assert profile.median == float(expected_median)
    assert profile.p995 == float(expected_p995)
    assert profile.mean == float(reference.mean())
    assert profile.std == float(reference.std())
    assert profile.saturation_fraction == float(np.mean(reference >= 65535))
    assert percentile_calls == [(1.0, 50.0, 99.5)]


def test_float_image_profile_ignores_non_finite_values_but_reports_them(tmp_path: Path) -> None:
    image = np.array([[1.0, np.nan], [3.0, 5.0]], dtype=np.float32)
    path = tmp_path / "float-profile.tif"
    tifffile.imwrite(path, image)

    profile = inspect_image(path)

    assert profile.finite is False
    assert profile.min == 1.0
    assert profile.max == 5.0
    assert profile.mean == 3.0
