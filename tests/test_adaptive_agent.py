from pathlib import Path

import numpy as np
import tifffile

from bionuclei.adaptive_agent import _cnn_pattern_status, CNNPatternCheck, build_plan, to_dict


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
    import gc
    import weakref
    import torch
    import bionuclei.inference

    image = np.full((512, 512), 512, dtype=np.uint16)
    image[120:392, 120:392] = 8192
    path = tmp_path / "large.tif"
    tifffile.imwrite(path, image)
    image_refs = []
    original_imread = tifffile.imread

    def tracked_imread(image_path):
        loaded = original_imread(image_path)
        image_refs.append(weakref.ref(loaded))
        return loaded

    monkeypatch.setattr(tifffile, "imread", tracked_imread)
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
        gc.collect()
        assert image_refs and image_refs[0]() is None
        assert checkpoint_path == checkpoint
        assert device == "cpu"
        loader_calls.append((checkpoint_path, device))
        events.append("load")
        return FakeModel()

    monkeypatch.setattr(bionuclei.inference, "_load_model", fake_load_model)

    def fake_trim_allocator():
        assert lock.held is True
        events.append("trim_allocator")
        return True

    monkeypatch.setattr(bionuclei.inference, "_trim_cpu_allocator", fake_trim_allocator)
    result = __import__("bionuclei.adaptive_agent", fromlist=["cnn_pattern_check"]).cnn_pattern_check(path)
    assert result.executed is True
    assert result.status == "PASS"
    assert seen_shapes == [(1, 1, 192, 192)]
    assert loader_calls == [(checkpoint, "cpu")]
    assert events == ["acquire", "load", "model_cleanup", "trim_allocator", "release"]
    assert lock.held is False


def test_uncalibrated_cnn_foreground_extremes_remain_caution_not_blocked() -> None:
    cases = (
        (0.001, "CNN found negligible nuclear foreground support."),
        (0.98, "CNN classified nearly the entire image as foreground."),
        (1.0, "CNN classified nearly the entire image as foreground."),
    )
    for fraction, expected_reason in cases:
        status, reasons = _cnn_pattern_status(fraction, 0.9, 1)
        assert status == "CAUTION"
        assert expected_reason in reasons


def test_extreme_foreground_caution_is_preserved_in_analysis_plan(tmp_path: Path, monkeypatch) -> None:
    image = np.zeros((32, 32), dtype=np.uint16)
    image[2:30, 2:30] = 1000
    path = tmp_path / "dense-image.tif"
    tifffile.imwrite(path, image)
    monkeypatch.setattr(
        "bionuclei.adaptive_agent.cnn_pattern_check",
        lambda _path: CNNPatternCheck(
            True,
            "Boundary U Net",
            0.99,
            0.9,
            0.2,
            1,
            "CAUTION",
            ("CNN classified nearly the entire image as foreground.",),
        ),
    )
    plan = build_plan(path, {"nuclei"})
    assert plan.status == "CAUTION"
    assert "CNN classified nearly the entire image as foreground." in plan.warnings

