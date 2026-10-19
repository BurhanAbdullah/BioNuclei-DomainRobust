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
        self.headers = Message()
        for key, value in (headers or {}).items():
            self.headers[key] = value

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args) -> None:
        self._stream.close()

    def read(self, size: int = -1) -> bytes:
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
