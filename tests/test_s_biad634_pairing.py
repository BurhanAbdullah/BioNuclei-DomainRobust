from pathlib import Path

import numpy as np
import tifffile

from scripts.evaluate_s_biad634 import pair_files


def test_s_biad634_pairing_ignores_unmatched_groundtruth_files(tmp_path: Path) -> None:
    raw = tmp_path / "extracted" / "rawimages"
    gt = tmp_path / "extracted" / "groundtruth"
    raw.mkdir(parents=True)
    gt.mkdir(parents=True)

    image = np.zeros((8, 8), dtype=np.uint16)
    mask = np.zeros((8, 8), dtype=np.uint16)
    tifffile.imwrite(raw / "sample01.tif", image)
    tifffile.imwrite(gt / "sample01.tif", mask)
    tifffile.imwrite(gt / "unrelated_reference.tif", mask)

    pairs = pair_files(tmp_path)

    assert len(pairs) == 1
    assert pairs[0][0].stem == "sample01"
    assert pairs[0][1].stem == "sample01"


def test_s_biad634_pairing_rejects_ambiguous_matching_masks(tmp_path: Path) -> None:
    raw = tmp_path / "extracted" / "rawimages"
    gt = tmp_path / "extracted" / "groundtruth"
    raw.mkdir(parents=True)
    gt.mkdir(parents=True)

    image = np.zeros((8, 8), dtype=np.uint16)
    mask = np.zeros((8, 8), dtype=np.uint16)
    tifffile.imwrite(raw / "sample01.tif", image)
    tifffile.imwrite(gt / "sample01.tif", mask)
    tifffile.imwrite(gt / "sample01.png", mask)

    try:
        pair_files(tmp_path)
    except RuntimeError as exc:
        assert "ambiguous" in str(exc)
    else:
        raise AssertionError("Expected ambiguous matching masks to fail")
