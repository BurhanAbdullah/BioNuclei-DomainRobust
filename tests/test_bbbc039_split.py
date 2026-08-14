from pathlib import Path

import pytest

from scripts.build_bbbc039_split import discover_partition_files, parse_partition_file


def test_partition_parser_normalizes_filenames(tmp_path: Path):
    p = tmp_path / "train.txt"
    p.write_text("field_001.tif\nfield_002.tiff\n\n")
    assert parse_partition_file(p, "train") == {"field_001.tif", "field_002.tiff"}


def test_partition_discovery_requires_all_splits(tmp_path: Path):
    (tmp_path / "train.txt").write_text("a.tif\n")
    with pytest.raises(SystemExit, match="validation"):
        discover_partition_files(tmp_path)


def test_partition_discovery_uses_distinct_files(tmp_path: Path):
    for name in ("train", "validation", "test"):
        (tmp_path / f"{name}.txt").write_text(f"{name}.tif\n")
    found = discover_partition_files(tmp_path)
    assert set(found) == {"train", "validation", "test"}
