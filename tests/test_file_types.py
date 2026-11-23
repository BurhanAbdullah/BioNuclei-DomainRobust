import re
from pathlib import Path

import pytest

from bionuclei.file_types import check_upload, sniff

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = {
    "tiff": b"II*\x00" + b"\x00" * 60,
    "bigtiff": b"MM\x00+" + b"\x00" * 60,
    "nd2": b"\xda\xce\xbe\x0a" + b"\x00" * 60,
    "png": b"\x89PNG\r\n\x1a\n" + b"\x00" * 60,
    "jpeg": b"\xff\xd8\xff\xe0\x00\x10JFIF",
    "gif": b"GIF89a" + b"\x00" * 10,
    "webp": b"RIFF\x00\x00\x00\x00WEBPVP8 ",
    "heic": b"\x00\x00\x00\x18ftypheic\x00\x00",
    "video": b"\x00\x00\x00\x18ftypisom\x00\x00",
    "pdf": b"%PDF-1.7\n",
    "zip": b"PK\x03\x04" + b"\x00" * 20,
    "czi": b"ZISRAWFILE" + b"\x00" * 20,
    "executable": b"MZ\x90\x00" + b"\x00" * 20,
    "gzip": b"\x1f\x8b\x08\x00",
    "text": b"label,area\n1,120\n2,98\n",
    "empty": b"",
    "unknown": bytes([0, 1, 2, 250, 251, 252, 3, 4]),
}


@pytest.mark.parametrize("kind,head", SAMPLES.items())
def test_sniff_identifies_by_content(kind, head):
    assert sniff(head, "file.bin").kind == kind


def test_only_microscopy_formats_are_accepted():
    accepted = {k for k, h in SAMPLES.items() if sniff(h, "x").accepted}
    assert accepted == {"tiff", "bigtiff", "nd2"}


@pytest.mark.parametrize("head,name,expected", [
    (SAMPLES["jpeg"], "cells.tif", "named .tif but it is a JPEG photo"),
    (SAMPLES["pdf"], "scan.TIFF", "named .TIFF but it is a PDF document"),
    (SAMPLES["text"], "data.tif", "named .tif but it is a text file (for example CSV, notes or code)"),
    (SAMPLES["executable"], "x.nd2", "named .nd2 but it is a program"),
    (SAMPLES["unknown"], "x.tif", "contents are not a TIFF file"),
])
def test_name_and_content_mismatch_is_explained(head, name, expected):
    kind = check_upload(head, name)
    assert not kind.accepted and expected in kind.message()


def test_vendor_formats_get_export_advice():
    assert "export" in sniff(SAMPLES["czi"], "a.czi").advice.lower()
    assert "Leica" in sniff(b"\x70\x00\x00\x00" + b"\x00" * 20, "p.lif").label
    assert "unzip" in sniff(SAMPLES["zip"], "imgs.zip").advice.lower()


def test_server_rejects_disguised_upload_before_creating_a_job(tmp_path, monkeypatch):
    from webapp import community
    monkeypatch.setattr(community, "JOB_ROOT", tmp_path / "jobs")
    monkeypatch.setattr(community, "DB_PATH", tmp_path / "jobs" / "db.sqlite3")
    community.JOB_ROOT.mkdir(parents=True)
    with pytest.raises(ValueError, match="named .tif but it is a JPEG photo"):
        community.create_job(SAMPLES["jpeg"], "cells.tif", "user-1", False, "auto")
    with pytest.raises(ValueError, match="contents are a Nikon ND2"):
        community.create_job(SAMPLES["nd2"], "scan.tif", "user-1", False, "auto")
    assert not any(p.is_dir() for p in community.JOB_ROOT.iterdir())


def test_browser_sniffer_covers_the_same_kinds():
    js = (ROOT / "docs" / "assets" / "file-sniff.js").read_text(encoding="utf-8")
    kinds_js = set(re.findall(r"K\('([a-z0-9_]+)'", js))
    py = (ROOT / "src" / "bionuclei" / "file_types.py").read_text(encoding="utf-8")
    kinds_py = set(re.findall(r'(?:FileKind|_photo)\("([a-z0-9_]+)"', py))
    assert kinds_py <= kinds_js, sorted(kinds_py - kinds_js)
