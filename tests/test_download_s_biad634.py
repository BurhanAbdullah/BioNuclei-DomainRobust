from __future__ import annotations

import http.client
import io
import json
import struct
import sys
import urllib.error
import zipfile
from pathlib import Path

import pytest

from scripts import download_s_biad634 as downloader
from scripts import extract_s_biad634_archive as extractor


class _DisconnectAfterFirstRead(io.BytesIO):
    def __init__(self, initial: bytes) -> None:
        super().__init__(initial)
        self._reads = 0

    def read(self, size: int = -1) -> bytes:
        self._reads += 1
        if self._reads == 2:
            raise http.client.RemoteDisconnected("connection closed during response body")
        return super().read(size)



def _part_files(destination: Path) -> list[Path]:
    return list(destination.parent.glob(f".{destination.name}.*.part"))



def _zip_bytes(payload: bytes = b"dataset member", *, corrupt: bool = False) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("dataset/rawimages/image_001.tif", payload)
    data = bytearray(buffer.getvalue())
    if corrupt:
        filename_length, extra_length = struct.unpack_from("<HH", data, 26)
        member_offset = 30 + filename_length + extra_length
        data[member_offset] ^= 0xFF
    return bytes(data)



def test_download_retries_remote_disconnect_and_replaces_destination_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "dataset.zip"
    destination.write_bytes(b"previous complete archive")
    delays: list[float] = []
    calls = 0

    valid_archive = _zip_bytes()

    def fake_urlopen(url: str, *, timeout: int):
        nonlocal calls
        calls += 1
        assert url == "https://example.test/dataset.zip"
        assert timeout == downloader.DOWNLOAD_TIMEOUT_SECONDS
        if calls == 1:
            return _DisconnectAfterFirstRead(b"partial transfer")
        assert destination.read_bytes() == b"previous complete archive"
        assert _part_files(destination) == []
        return io.BytesIO(valid_archive)

    monkeypatch.setattr(downloader.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(downloader.time, "sleep", delays.append)

    downloader.download("https://example.test/dataset.zip", destination)

    assert calls == 2
    assert delays == [2]
    assert destination.read_bytes() == valid_archive
    assert _part_files(destination) == []



def test_download_retries_transient_http_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    destination = tmp_path / "dataset.zip"
    delays: list[float] = []
    valid_archive = _zip_bytes()
    calls = 0

    def fake_urlopen(_url: str, *, timeout: int):
        nonlocal calls
        calls += 1
        assert timeout == downloader.DOWNLOAD_TIMEOUT_SECONDS
        if calls == 1:
            raise urllib.error.HTTPError(
                "https://example.test/dataset.zip",
                503,
                "Service Unavailable",
                {},
                io.BytesIO(b"temporary outage"),
            )
        return io.BytesIO(valid_archive)

    monkeypatch.setattr(downloader.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(downloader.time, "sleep", delays.append)

    downloader.download("https://example.test/dataset.zip", destination)

    assert calls == 2
    assert delays == [2]
    assert destination.read_bytes() == b"complete archive"
    assert _part_files(destination) == []



def test_download_does_not_retry_permanent_http_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    destination = tmp_path / "dataset.zip"
    destination.write_bytes(b"previous complete archive")
    delays: list[float] = []
    calls = 0
    response_body = io.BytesIO(b"missing dataset")

    def fake_urlopen(_url: str, *, timeout: int):
        nonlocal calls
        calls += 1
        assert timeout == downloader.DOWNLOAD_TIMEOUT_SECONDS
        raise urllib.error.HTTPError(
            "https://example.test/dataset.zip",
            404,
            "Not Found",
            {},
            response_body,
        )

    monkeypatch.setattr(downloader.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(downloader.time, "sleep", delays.append)

    with pytest.raises(urllib.error.HTTPError) as exc_info:
        downloader.download("https://example.test/dataset.zip", destination)

    assert exc_info.value.code == 404
    assert response_body.closed
    assert calls == 1
    assert delays == []
    assert destination.read_bytes() == b"previous complete archive"
    assert _part_files(destination) == []



def test_download_stops_after_bounded_transient_failures_without_partial_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "dataset.zip"
    destination.write_bytes(b"previous complete archive")
    delays: list[float] = []
    calls = 0

    def fake_urlopen(_url: str, *, timeout: int):
        nonlocal calls
        calls += 1
        assert timeout == downloader.DOWNLOAD_TIMEOUT_SECONDS
        raise http.client.RemoteDisconnected("remote server closed connection")

    monkeypatch.setattr(downloader.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(downloader.time, "sleep", delays.append)

    with pytest.raises(http.client.RemoteDisconnected):
        downloader.download("https://example.test/dataset.zip", destination)

    assert calls == downloader.MAX_DOWNLOAD_ATTEMPTS
    assert delays == [2, 4, 8]
    assert destination.read_bytes() == b"previous complete archive"
    assert _part_files(destination) == []


def test_download_retries_crc_invalid_archive_before_replacing_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "dataset.zip"
    destination.write_bytes(b"previous complete archive")
    corrupt_archive = _zip_bytes(corrupt=True)
    valid_archive = _zip_bytes()
    delays: list[float] = []
    calls = 0

    def fake_urlopen(_url: str, *, timeout: int):
        nonlocal calls
        calls += 1
        assert timeout == downloader.DOWNLOAD_TIMEOUT_SECONDS
        if calls == 1:
            return io.BytesIO(corrupt_archive)
        assert destination.read_bytes() == b"previous complete archive"
        assert _part_files(destination) == []
        return io.BytesIO(valid_archive)

    monkeypatch.setattr(downloader.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(downloader.time, "sleep", delays.append)

    downloader.download("https://example.test/dataset.zip", destination)

    assert calls == 2
    assert delays == [2]
    assert destination.read_bytes() == valid_archive
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
    assert _part_files(destination) == []



def test_download_stops_after_bounded_crc_invalid_archives_without_replacing_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "dataset.zip"
    destination.write_bytes(b"previous complete archive")
    corrupt_archive = _zip_bytes(corrupt=True)
    delays: list[float] = []
    calls = 0

    def fake_urlopen(_url: str, *, timeout: int):
        nonlocal calls
        calls += 1
        assert timeout == downloader.DOWNLOAD_TIMEOUT_SECONDS
        return io.BytesIO(corrupt_archive)

    monkeypatch.setattr(downloader.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(downloader.time, "sleep", delays.append)

    with pytest.raises(downloader.CorruptDatasetArchiveError, match="corrupt member"):
        downloader.download("https://example.test/dataset.zip", destination)

    assert calls == downloader.MAX_DOWNLOAD_ATTEMPTS
    assert delays == [2, 4, 8]
    assert destination.read_bytes() == b"previous complete archive"
    assert _part_files(destination) == []



def test_download_validates_expansion_limits_before_crc_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "dataset.zip"
    destination.write_bytes(b"previous complete archive")
    oversized_archive = _zip_bytes(payload=b"image-payload-too-large")
    monkeypatch.setattr(extractor, "MAX_MEMBER_UNCOMPRESSED_BYTES", 4)
    monkeypatch.setattr(
        downloader.urllib.request,
        "urlopen",
        lambda _url, *, timeout: io.BytesIO(oversized_archive),
    )
    monkeypatch.setattr(
        zipfile.ZipFile,
        "testzip",
        lambda _self: pytest.fail("expansion limits must be checked before CRC decompression"),
    )

    with pytest.raises(ValueError, match="per-file limit"):
        downloader.download("https://example.test/dataset.zip", destination)

    assert destination.read_bytes() == b"previous complete archive"
    assert _part_files(destination) == []



def _write_archive(path: Path, members: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)



def _stub_download(source: Path):
    def copy_archive(_url: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    return copy_archive



def test_skip_extract_inventories_zip_without_writing_archive_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.zip"
    _write_archive(
        source,
        {
            "dataset/rawimages/image_001.tif": b"raw",
            "dataset/groundtruth/mask_001.tif": b"mask",
            "dataset/readme.txt": b"CC0",
        },
    )
    root = tmp_path / "target"
    monkeypatch.setattr(downloader, "download", _stub_download(source))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "download_s_biad634.py",
            "--data-root",
            str(root),
            "--keep-archive",
            "--skip-extract",
        ],
    )

    downloader.main()

    manifest = json.loads((root / "download_manifest.json").read_text(encoding="utf-8"))
    assert manifest["files"] == [
        "dataset/groundtruth/mask_001.tif",
        "dataset/rawimages/image_001.tif",
        "dataset/readme.txt",
    ]
    assert (root / "dataset.zip").is_file()
    assert not (root / "extracted").exists()
    assert not (tmp_path / "escape.txt").exists()



def test_default_download_uses_manifest_verified_safe_extractor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.zip"
    _write_archive(
        source,
        {
            "dataset/rawimages/image_001.tif": b"raw",
            "dataset/groundtruth/mask_001.tif": b"mask",
            "dataset/readme.txt": b"CC0",
        },
    )
    root = tmp_path / "target"
    monkeypatch.setattr(downloader, "download", _stub_download(source))
    monkeypatch.setattr(
        sys,
        "argv",
        ["download_s_biad634.py", "--data-root", str(root), "--keep-archive"],
    )

    downloader.main()

    assert (root / "extracted/dataset/rawimages/image_001.tif").read_bytes() == b"raw"
    assert (root / "extracted/dataset/groundtruth/mask_001.tif").read_bytes() == b"mask"



def test_default_download_rejects_zip_path_traversal_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.zip"
    _write_archive(
        source,
        {
            "dataset/rawimages/image_001.tif": b"raw",
            "dataset/groundtruth/mask_001.tif": b"mask",
            "../escape.txt": b"must not be written",
        },
    )
    root = tmp_path / "target"
    monkeypatch.setattr(downloader, "download", _stub_download(source))
    monkeypatch.setattr(
        sys,
        "argv",
        ["download_s_biad634.py", "--data-root", str(root), "--keep-archive"],
    )

    with pytest.raises(ValueError, match="Unsafe target-dataset ZIP member"):
        downloader.main()

    assert not (tmp_path / "escape.txt").exists()
    assert not (root / "download_manifest.json").exists()
    assert not (root / "extracted").exists()


def test_custom_source_url_is_bound_and_safely_extracted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.zip"
    _write_archive(
        source,
        {
            "dataset/rawimages/image_001.tif": b"raw",
            "dataset/groundtruth/mask_001.tif": b"mask",
            "dataset/readme.txt": b"CC0",
        },
    )
    root = tmp_path / "target"
    source_url = "https://mirror.example.test/S-BIAD634/dataset.zip"
    monkeypatch.setattr(downloader, "download", _stub_download(source))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "download_s_biad634.py",
            "--data-root",
            str(root),
            "--url",
            source_url,
            "--keep-archive",
        ],
    )

    downloader.main()

    manifest = json.loads((root / "download_manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_url"] == source_url
    assert (root / "extracted/dataset/rawimages/image_001.tif").read_bytes() == b"raw"





def test_download_rejects_oversized_archive_without_replacing_existing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "dataset.zip"
    destination.write_bytes(b"previous complete archive")
    monkeypatch.setattr(downloader, "MAX_ARCHIVE_BYTES", 4)
    monkeypatch.setattr(
        downloader.urllib.request,
        "urlopen",
        lambda _url, *, timeout: io.BytesIO(b"12345"),
    )

    with pytest.raises(ValueError, match="compressed-size limit"):
        downloader.download("https://example.test/dataset.zip", destination)

    assert destination.read_bytes() == b"previous complete archive"
    assert _part_files(destination) == []



def test_skip_extract_validates_expansion_limits_before_crc_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.zip"
    _write_archive(
        source,
        {
            "dataset/rawimages/image_001.tif": b"raw-image-too-large",
            "dataset/groundtruth/mask_001.tif": b"mask",
            "dataset/readme.txt": b"CC0",
        },
    )
    root = tmp_path / "target"
    monkeypatch.setattr(extractor, "MAX_MEMBER_UNCOMPRESSED_BYTES", 4)
    monkeypatch.setattr(downloader, "download", _stub_download(source))
    monkeypatch.setattr(
        zipfile.ZipFile,
        "testzip",
        lambda _self: pytest.fail("inventory-only mode must validate limits before CRC scan"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "download_s_biad634.py",
            "--data-root",
            str(root),
            "--keep-archive",
            "--skip-extract",
        ],
    )

    with pytest.raises(ValueError, match="per-file limit"):
        downloader.main()

    assert not (root / "download_manifest.json").exists()
    assert not (root / "extracted").exists()
