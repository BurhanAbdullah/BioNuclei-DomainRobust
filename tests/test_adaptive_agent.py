from pathlib import Path

import numpy as np
import tifffile

from bionuclei.adaptive_agent import CNNPatternCheck, build_plan, to_dict


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
