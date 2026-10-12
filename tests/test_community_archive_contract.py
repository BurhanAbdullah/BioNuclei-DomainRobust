from pathlib import Path
from zipfile import ZipFile


def test_public_service_archive_excludes_transient_source_images(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("BIONUCLEI_JOB_DIR", str(tmp_path))

    import importlib
    import webapp.community as community
    import webapp.community_app as community_app

    community = importlib.reload(community)
    community_app = importlib.reload(community_app)
    job_id = "archive-contract"
    root = community._job_dir(job_id)
    (root / "results").mkdir(parents=True)
    (root / "input.tif").write_bytes(b"SOURCE")
    (root / "input_plane.tif").write_bytes(b"DERIVED-TRANSIENT")
    (root / "results" / "segmentation_mask.tif").write_bytes(b"MASK")
    (root / "results" / "results.json").write_text("{}", encoding="utf-8")

    archive = community._archive(job_id)
    with ZipFile(archive) as zf:
        names = set(zf.namelist())

    assert "results/segmentation_mask.tif" in names
    assert "results/results.json" in names
    assert "input.tif" not in names
    assert "input_plane.tif" not in names
