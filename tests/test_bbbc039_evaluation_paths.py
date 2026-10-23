from pathlib import Path

import pytest

from scripts.evaluate_bbbc039 import resolve_image_path


def test_resolve_manifest_png_name_to_nested_tiff_image(tmp_path: Path) -> None:
    image_root = tmp_path / "images" / "images"
    image_root.mkdir(parents=True)
    image = image_root / "IXMtest_A09_s1.tif"
    image.write_bytes(b"fixture")

    # Official split metadata may name the paired PNG mask while the image
    # archive stores the fluorescence image as TIFF with the same stem.
    assert resolve_image_path(tmp_path, "IXMtest_A09_s1.png") == image


def test_resolve_image_path_matches_stem_case_insensitively(tmp_path: Path) -> None:
    image_root = tmp_path / "images" / "Images"
    image_root.mkdir(parents=True)
    image = image_root / "ixmtest_a09_s1.TIFF"
    image.write_bytes(b"fixture")

    assert resolve_image_path(tmp_path, "IXMtest_A09_S1.png") == image


def test_resolve_image_path_rejects_ambiguous_stem(tmp_path: Path) -> None:
    image_root = tmp_path / "images"
    image_root.mkdir(parents=True)
    (image_root / "field_01.tif").write_bytes(b"one")
    (image_root / "field_01.tiff").write_bytes(b"two")

    with pytest.raises(RuntimeError, match="Ambiguous downloaded images"):
        resolve_image_path(tmp_path, "field_01.png")


def test_resolve_image_path_fails_when_no_stem_matches(tmp_path: Path) -> None:
    (tmp_path / "images").mkdir()

    with pytest.raises(FileNotFoundError, match="No downloaded image matches"):
        resolve_image_path(tmp_path, "missing.png")
