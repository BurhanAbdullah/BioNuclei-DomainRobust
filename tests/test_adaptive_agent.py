from pathlib import Path

import numpy as np
import tifffile

from bionuclei.adaptive_agent import build_plan, to_dict


def test_adaptive_plan_flags_flat_image(tmp_path: Path) -> None:
    path = tmp_path / "flat.tif"
    tifffile.imwrite(path, np.zeros((32, 32), dtype=np.uint16))
    plan = build_plan(path)
    assert plan.status == "BLOCKED"
    assert any("no usable intensity variation" in warning.lower() for warning in plan.warnings)
    assert to_dict(plan)["profile"]["shape"] == [32, 32]


def test_adaptive_plan_accepts_nonflat_image(tmp_path: Path) -> None:
    image = np.zeros((32, 32), dtype=np.uint16)
    image[8:24, 8:24] = 1000
    path = tmp_path / "image.tif"
    tifffile.imwrite(path, image)
    plan = build_plan(path, {"nuclei", "morphology"})
    assert plan.status in {"READY", "CAUTION"}
    assert plan.recommended_modules == ("morphology", "nuclei")
