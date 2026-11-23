import numpy as np
import pytest
import tifffile

from bionuclei.input_recognition import InputRejected, recognize_tiff
from bionuclei.report import _input_lines


def _fluorescence(shape=(128, 128), seed=0, peak=3000, background=200):
    """Bright round blobs on a dark, noisy background (fluorescence nuclei)."""
    rng = np.random.default_rng(seed)
    image = rng.normal(background, 20, shape)
    yy, xx = np.mgrid[: shape[0], : shape[1]]
    for _ in range(12):
        cy, cx = rng.integers(10, shape[0] - 10), rng.integers(10, shape[1] - 10)
        image += peak * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * 5.0 ** 2))
    return np.clip(image, 0, 65535).astype(np.uint16)


def test_plain_16bit_plane_is_ready_and_written_unchanged(tmp_path):
    image = _fluorescence()
    src, dst = tmp_path / "a.tif", tmp_path / "plane.tif"
    tifffile.imwrite(src, image)
    record = recognize_tiff(src, dst)
    assert record["decision"] == "ready"
    assert record["recognized_as"] == "16-bit 2-D fluorescence image"
    assert np.array_equal(tifffile.imread(dst), image)
    assert record["selected_plane_dtype"] == "uint16"


def test_imagej_zcyx_stack_selects_requested_plane(tmp_path):
    stack = np.stack([np.stack([_fluorescence(seed=z * 10 + c) for c in range(2)]) for z in range(3)])  # Z, C, Y, X
    src, dst = tmp_path / "stack.tif", tmp_path / "plane.tif"
    tifffile.imwrite(src, stack, imagej=True, metadata={"axes": "ZCYX"})
    record = recognize_tiff(src, dst, channel=1, z=2)
    assert record["source_axes"] == "ZCYX"
    assert record["selected_indices"] == {"z": 2, "channel": 1}
    assert record["decision"] == "plane_extracted"
    assert np.array_equal(tifffile.imread(dst), stack[2, 1])


def test_out_of_range_plane_index_is_rejected_with_reason(tmp_path):
    stack = np.stack([_fluorescence(seed=i) for i in range(3)])
    src = tmp_path / "z.tif"
    tifffile.imwrite(src, stack, imagej=True, metadata={"axes": "ZYX"})
    with pytest.raises(InputRejected, match=r"3 z entries \(0 to 2\); index 5"):
        recognize_tiff(src, tmp_path / "plane.tif", z=5)


def test_rgb_export_uses_the_channel_with_the_signal(tmp_path):
    rgb = np.zeros((128, 128, 3), dtype=np.uint8)
    rgb[..., 2] = (_fluorescence() // 256).astype(np.uint8)  # DAPI exported as blue
    src, dst = tmp_path / "dapi_rgb.tif", tmp_path / "plane.tif"
    tifffile.imwrite(src, rgb, photometric="rgb")
    record = recognize_tiff(src, dst)
    assert record["selected_indices"]["color channel"] == 2
    assert "blue channel" in " ".join(record["notes"])
    assert np.array_equal(tifffile.imread(dst), rgb[..., 2])


def test_greyscale_saved_as_rgb_is_recognised(tmp_path):
    grey = (_fluorescence() // 256).astype(np.uint8)
    src = tmp_path / "grey_rgb.tif"
    tifffile.imwrite(src, np.repeat(grey[..., None], 3, axis=2), photometric="rgb")
    record = recognize_tiff(src, tmp_path / "plane.tif")
    assert "identical" in " ".join(record["notes"])


def test_brightfield_like_image_is_rejected(tmp_path):
    # Dark objects on a bright background: the inverse of fluorescence.
    brightfield = (60000 - _fluorescence(peak=20000, background=0).astype(np.int64)).clip(0, 65535).astype(np.uint16)
    src = tmp_path / "bf.tif"
    tifffile.imwrite(src, brightfield)
    with pytest.raises(InputRejected, match="brightfield"):
        recognize_tiff(src, tmp_path / "plane.tif")


def test_colour_histology_like_rgb_is_rejected(tmp_path):
    rng = np.random.default_rng(3)
    he = np.full((128, 128, 3), 235, dtype=np.uint8)
    yy, xx = np.mgrid[:128, :128]
    for _ in range(15):
        cy, cx = rng.integers(10, 118, 2)
        blob = ((yy - cy) ** 2 + (xx - cx) ** 2) < 36
        he[blob] = (90, 40, 140)  # purple haematoxylin nuclei
    src = tmp_path / "he.tif"
    tifffile.imwrite(src, he, photometric="rgb")
    with pytest.raises(InputRejected, match="histology"):
        recognize_tiff(src, tmp_path / "plane.tif")


def test_tiny_blank_and_unreadable_inputs_are_rejected(tmp_path):
    tifffile.imwrite(tmp_path / "tiny.tif", _fluorescence()[:16, :16])
    with pytest.raises(InputRejected, match="at least 32 px"):
        recognize_tiff(tmp_path / "tiny.tif", tmp_path / "p.tif")
    tifffile.imwrite(tmp_path / "blank.tif", np.full((64, 64), 7, dtype=np.uint16))
    with pytest.raises(InputRejected, match="no intensity variation"):
        recognize_tiff(tmp_path / "blank.tif", tmp_path / "p.tif")
    (tmp_path / "junk.tif").write_bytes(b"not a tiff at all")
    with pytest.raises(InputRejected, match="could not be read"):
        recognize_tiff(tmp_path / "junk.tif", tmp_path / "p.tif")


def test_report_lines_describe_recognition_and_units(tmp_path):
    src = tmp_path / "a.tif"
    tifffile.imwrite(src, _fluorescence(), imagej=True, resolution=(1 / 0.325, 1 / 0.325), metadata={"unit": "um"})
    record = recognize_tiff(src, tmp_path / "plane.tif")
    lines = _input_lines({"input_metadata": record})
    text = " ".join(lines)
    assert "Recognized as: 16-bit 2-D fluorescence image" in text
    assert "0.325" in text and "Measurements remain in pixels" in text


def test_fluorophore_identification_by_name_and_wavelength():
    from bionuclei.fluorophores import identify
    assert identify("DAPI")["nuclear_stain"] is True
    assert identify("ch01_Hoechst")["fluorophore"] == "Hoechst 33342"
    assert identify("Alexa Fluor 488")["nuclear_stain"] is False
    assert identify("pipette")["fluorophore"] != "Propidium iodide"  # short aliases need word boundaries
    blue = identify(None, 405, 461)
    assert blue["nuclear_stain"] is True and {"DAPI", "Hoechst 33342"} <= set(blue["candidates"])
    assert identify(None, None, 900)["matched_by"] is None


def test_ome_channels_identify_the_nuclear_channel_and_warn_on_mismatch(tmp_path):
    stack = np.stack([_fluorescence(seed=1), _fluorescence(seed=2)])
    src = tmp_path / "two.ome.tif"
    tifffile.imwrite(src, stack, ome=True, metadata={"axes": "CYX", "Channel": {"Name": ["Alexa Fluor 488", "DAPI"]}})
    record = recognize_tiff(src, tmp_path / "plane.tif", channel=0)
    info = record["channel_identification"]
    assert info["nuclear_channel"] == 1
    assert info["channels"][1]["emission_peak_nm"] == 461
    notes = " ".join(record["notes"])
    assert "Channel 1 identified as DAPI" in notes
    assert "channel 0 was analyzed, but the metadata identifies channel 1" in notes


def test_browser_fluorophore_table_matches_python_source():
    import json
    from pathlib import Path
    from bionuclei.fluorophores import public_table
    published = json.loads((Path(__file__).resolve().parents[1] / "docs" / "assets" / "fluorophores.json").read_text())
    assert published == public_table()
