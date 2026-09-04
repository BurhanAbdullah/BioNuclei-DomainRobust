import json

import pytest

from scripts.verify_e6_split import load_ids_and_validate_annotations


def write_manifest(path, rows):
    path.write_text(json.dumps(rows))


def test_e6_manifest_requires_annotation_reference(tmp_path):
    p = tmp_path / "manifest.json"
    write_manifest(p, [{"image_id": "img-1"}])
    with pytest.raises(ValueError, match="annotation/mask reference"):
        load_ids_and_validate_annotations(p)


def test_e6_manifest_rejects_duplicate_image_ids(tmp_path):
    p = tmp_path / "manifest.json"
    write_manifest(
        p,
        [
            {"image_id": "img-1", "mask": "m1"},
            {"image_id": "img-1", "mask": "m2"},
        ],
    )
    with pytest.raises(ValueError, match="duplicate image identifiers"):
        load_ids_and_validate_annotations(p)


def test_e6_manifest_accepts_image_annotation_pairs(tmp_path):
    p = tmp_path / "manifest.json"
    write_manifest(
        p,
        [
            {"image_id": "img-1", "mask": "m1"},
            {"image_id": "img-2", "ground_truth_file": "m2"},
        ],
    )
    assert load_ids_and_validate_annotations(p) == {"img-1", "img-2"}
