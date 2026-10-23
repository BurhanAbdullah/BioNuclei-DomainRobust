"""Regression tests for bounded, integrity-checked Aitslab archive downloads."""
from __future__ import annotations

import hashlib
import io
import json
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError

import pytest

from scripts import download_aitslab_bioimaging1 as downloader


class FakeResponse:
    def __init__(self, payload: bytes, headers: dict[str, str] | None = None) -> None:
        self._stream = io.BytesIO(payload)
        self.read_sizes: list[int] = []
        self.headers = Message()
        for key, value in (headers or {}).items():
            self.headers[key] = value

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args) -> None:
        self._stream.close()

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return self._stream.read(size)


def _http_error(url: str, code: int) -> HTTPError:
    headers = Message()
    if code == 429:
        headers["Retry-After"] = "1"
    return HTTPError(url, code, "temporary failure", headers, io.BytesIO(b"temporary"))


def test_get_json_retries_temporary_zenodo_response(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    payload = json.dumps({"id": 6657260, "files": []}).encode()

    def fake_urlopen(_request, timeout):
        nonlocal calls
        assert timeout == downloader.DOWNLOAD_TIMEOUT_SECONDS
        calls += 1
        if calls == 1:
            raise _http_error(downloader.RECORD_API, 429)
        return FakeResponse(payload)

    monkeypatch.setattr(downloader, "urlopen", fake_urlopen)
    monkeypatch.setattr(downloader.time, "sleep", lambda _seconds: None)

    result = downloader.get_json(downloader.RECORD_API)

    assert result == {"id": 6657260, "files": []}
    assert calls == 2


def test_archive_download_retries_and_publishes_only_verified_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"authoritative publisher archive bytes"
    expected_md5 = hashlib.md5(payload, usedforsecurity=False).hexdigest()
    calls = 0

    def fake_urlopen(_request, timeout):
        nonlocal calls
        assert timeout == downloader.DOWNLOAD_TIMEOUT_SECONDS
        calls += 1
        if calls == 1:
            raise _http_error("https://example.test/train.zip", 503)
        return FakeResponse(payload, {"Content-Length": str(len(payload))})

    monkeypatch.setattr(downloader, "urlopen", fake_urlopen)
    monkeypatch.setattr(downloader.time, "sleep", lambda _seconds: None)
    destination = tmp_path / "train.zip"

    resolved = downloader.download_archive(
        "https://example.test/train.zip",
        destination,
        {"checksum": f"md5:{expected_md5}"},
    )

    assert resolved == destination
    assert destination.read_bytes() == payload
    assert not destination.with_name(destination.name + ".part").exists()
    assert calls == 2


def test_archive_checksum_mismatch_never_publishes_partial_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"corrupt publisher download"
    expected_md5 = hashlib.md5(b"different bytes", usedforsecurity=False).hexdigest()
    calls = 0

    def fake_urlopen(_request, timeout):
        nonlocal calls
        calls += 1
        return FakeResponse(payload, {"Content-Length": str(len(payload))})

    monkeypatch.setattr(downloader, "urlopen", fake_urlopen)
    monkeypatch.setattr(downloader.time, "sleep", lambda _seconds: None)
    destination = tmp_path / "train.zip"

    with pytest.raises(RuntimeError, match="Could not download archive"):
        downloader.download_archive(
            "https://example.test/train.zip",
            destination,
            {"checksum": f"md5:{expected_md5}"},
        )

    assert calls == downloader.DOWNLOAD_ATTEMPTS
    assert not destination.exists()
    assert not destination.with_name(destination.name + ".part").exists()

def test_archive_download_verifies_sha256_publisher_checksum(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"publisher archive with sha256 metadata"
    expected_sha256 = hashlib.sha256(payload).hexdigest()
    calls = 0

    def fake_urlopen(_request, timeout):
        nonlocal calls
        assert timeout == downloader.DOWNLOAD_TIMEOUT_SECONDS
        calls += 1
        return FakeResponse(payload, {"Content-Length": str(len(payload))})

    monkeypatch.setattr(downloader, "urlopen", fake_urlopen)
    destination = tmp_path / "train.zip"

    resolved = downloader.download_archive(
        "https://example.test/train.zip",
        destination,
        {"checksum": f"sha256:{expected_sha256}"},
    )

    assert resolved == destination
    assert destination.read_bytes() == payload
    assert calls == 1


def test_archive_download_rejects_unsupported_checksum_algorithm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    def fake_urlopen(_request, timeout):
        nonlocal calls
        calls += 1
        return FakeResponse(b"archive bytes")

    monkeypatch.setattr(downloader, "urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="Unsupported publisher checksum algorithm"):
        downloader.download_archive(
            "https://example.test/train.zip",
            tmp_path / "train.zip",
            {"checksum": "sha1:abc123"},
        )

    assert calls == 0



def test_get_json_rejects_declared_oversized_metadata_without_reading_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(downloader, "MAX_METADATA_BYTES", 32)
    response = FakeResponse(b'{"id":6657260,"files":[]}' + b" " * 64, {"Content-Length": "88"})
    monkeypatch.setattr(downloader, "urlopen", lambda *_args, **_kwargs: response)

    with pytest.raises(RuntimeError, match="Could not download Zenodo metadata") as exc_info:
        downloader.get_json(downloader.RECORD_API)

    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert "exceeds the 32-byte limit" in str(exc_info.value.__cause__)
    assert response.read_sizes == []


def test_get_json_bounds_read_when_content_length_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(downloader, "MAX_METADATA_BYTES", 32)
    response = FakeResponse(b'{"id":6657260,"files":[]}' + b" " * 64)
    monkeypatch.setattr(downloader, "urlopen", lambda *_args, **_kwargs: response)

    with pytest.raises(RuntimeError, match="Could not download Zenodo metadata") as exc_info:
        downloader.get_json(downloader.RECORD_API)

    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert "exceeds the 32-byte limit" in str(exc_info.value.__cause__)
    assert response.read_sizes == [33]
