from __future__ import annotations

import http.client
import io
import urllib.error
from pathlib import Path

import pytest

from scripts import download_s_biad634 as downloader


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


def test_download_retries_remote_disconnect_and_replaces_destination_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "dataset.zip"
    destination.write_bytes(b"previous complete archive")
    delays: list[float] = []
    calls = 0

    def fake_urlopen(url: str, *, timeout: int):
        nonlocal calls
        calls += 1
        assert url == "https://example.test/dataset.zip"
        assert timeout == downloader.DOWNLOAD_TIMEOUT_SECONDS
        if calls == 1:
            return _DisconnectAfterFirstRead(b"partial transfer")
        assert destination.read_bytes() == b"previous complete archive"
        assert _part_files(destination) == []
        return io.BytesIO(b"complete archive")

    monkeypatch.setattr(downloader.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(downloader.time, "sleep", delays.append)

    downloader.download("https://example.test/dataset.zip", destination)

    assert calls == 2
    assert delays == [2]
    assert destination.read_bytes() == b"complete archive"
    assert _part_files(destination) == []


def test_download_retries_transient_http_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    destination = tmp_path / "dataset.zip"
    delays: list[float] = []
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
        return io.BytesIO(b"complete archive")

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

    def fake_urlopen(_url: str, *, timeout: int):
        nonlocal calls
        calls += 1
        assert timeout == downloader.DOWNLOAD_TIMEOUT_SECONDS
        raise urllib.error.HTTPError(
            "https://example.test/dataset.zip",
            404,
            "Not Found",
            {},
            io.BytesIO(b"missing dataset"),
        )

    monkeypatch.setattr(downloader.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(downloader.time, "sleep", delays.append)

    with pytest.raises(urllib.error.HTTPError) as exc_info:
        downloader.download("https://example.test/dataset.zip", destination)

    assert exc_info.value.code == 404
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
