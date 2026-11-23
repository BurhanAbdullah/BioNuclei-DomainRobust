import importlib.util
import io
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Response(io.BytesIO):
    headers = {"Content-Length": "5"}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.mark.parametrize("name", ["download_s_biad634", "download_bbbc038", "download_bbbc039"])
def test_server_errors_are_retried_then_succeed(name, tmp_path, monkeypatch):
    module = _load(name)
    calls = []

    def fake_urlopen(url, timeout):
        calls.append(url)
        if len(calls) < 3:
            raise urllib.error.HTTPError(url, 500, "server error", {}, None)
        return _Response(b"hello")

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr("time.sleep", lambda s: None)
    target = tmp_path / "file.zip"
    module.download("https://example.org/file.zip", target)
    assert len(calls) == 3
    assert target.read_bytes() == b"hello"
    assert not (tmp_path / "file.zip.part").exists()


def test_client_errors_fail_immediately(tmp_path, monkeypatch):
    module = _load("download_s_biad634")
    calls = []

    def fake_urlopen(url, timeout):
        calls.append(url)
        raise urllib.error.HTTPError(url, 404, "missing", {}, None)

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr("time.sleep", lambda s: None)
    with pytest.raises(urllib.error.HTTPError):
        module.download("https://example.org/missing.zip", tmp_path / "x.zip")
    assert len(calls) == 1
    assert not (tmp_path / "x.zip").exists()
