import hashlib
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import drive_backup  # noqa: E402


class FakeGoogle:
    """Minimal stand-in for Google's OAuth token endpoint and Drive v3 upload/list/delete."""

    def __init__(self, corrupt=False):
        self.files, self.uploads, self.deleted, self.corrupt, self.next_id = {}, {}, [], corrupt, 1
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _json(self, code, obj, headers=None):
                body = json.dumps(obj).encode()
                self.send_response(code)
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _body(self):
                return self.rfile.read(int(self.headers.get("Content-Length") or 0))

            def do_POST(self):
                u = urlsplit(self.path)
                if u.path == "/token":
                    form = parse_qs(self._body().decode())
                    return self._json(200, {"access_token": "AT"} if form.get("refresh_token") == ["RT"] else {"error": "invalid_grant"})
                assert self.headers["Authorization"] == "Bearer AT"
                meta = json.loads(self._body())
                sid = f"s{len(fake.uploads)}"
                fake.uploads[sid] = {"meta": meta, "data": b"", "size": int(self.headers["X-Upload-Content-Length"])}
                port = self.server.server_address[1]
                self._json(200, {}, {"Location": f"http://127.0.0.1:{port}/session/{sid}"})

            def do_PUT(self):
                sid = urlsplit(self.path).path.rsplit("/", 1)[1]
                up = fake.uploads[sid]
                up["data"] += self._body()
                if len(up["data"]) < up["size"]:
                    self.send_response(308); self.send_header("Content-Length", "0"); self.end_headers(); return
                fid = f"f{fake.next_id}"; fake.next_id += 1
                data = up["data"] + (b"x" if fake.corrupt else b"")
                fake.files[fid] = {"id": fid, "name": up["meta"]["name"], "data": data, "appProperties": up["meta"].get("appProperties", {}),
                                   "parents": up["meta"]["parents"], "createdTime": f"2026-11-22T00:00:{fake.next_id:02d}Z"}
                self._json(200, {"id": fid})

            def do_GET(self):
                assert self.headers["Authorization"] == "Bearer AT"
                u = urlsplit(self.path)
                if u.path == "/drive/v3/files":
                    q = parse_qs(u.query)["q"][0]
                    tagged = [f for f in fake.files.values() if f["appProperties"].get("bionuclei_backup") == "1" and q.startswith(f"'{f['parents'][0]}'")]
                    tagged.sort(key=lambda f: f["createdTime"], reverse=True)
                    return self._json(200, {"files": [{"id": f["id"], "name": f["name"], "createdTime": f["createdTime"]} for f in tagged]})
                f = fake.files[u.path.rsplit("/", 1)[1]]
                self._json(200, {"id": f["id"], "name": f["name"], "size": str(len(f["data"])), "md5Checksum": hashlib.md5(f["data"]).hexdigest()})

            def do_DELETE(self):
                fid = urlsplit(self.path).path.rsplit("/", 1)[1]
                fake.files.pop(fid, None); fake.deleted.append(fid)
                self.send_response(204); self.end_headers()

        self.server = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"


@pytest.fixture
def google(monkeypatch):
    fake = FakeGoogle()
    monkeypatch.setattr(drive_backup, "API", fake.url)
    monkeypatch.setattr(drive_backup, "OAUTH_URL", fake.url + "/token")
    monkeypatch.setattr(drive_backup, "CHUNK", 1024)  # force a multi-chunk resumable upload
    yield fake
    fake.server.shutdown()


def test_upload_is_chunked_verified_and_prune_spares_untagged_files(google, tmp_path):
    token = drive_backup.access_token("cid", "secret", "RT")
    google.files["user-doc"] = {"id": "user-doc", "name": "my-notes.docx", "data": b"mine", "appProperties": {}, "parents": ["FOLDER"], "createdTime": "2020-01-01T00:00:00Z"}
    names = []
    for i in range(4):
        archive = tmp_path / f"bionuclei-backup-2026112{i}T000000Z.tar.gz"
        archive.write_bytes(bytes(range(256)) * (10 + i))  # > CHUNK so several PUTs
        info = drive_backup.upload(token, "FOLDER", archive, "sha")
        names.append(info["name"])
        assert int(info["size"]) == archive.stat().st_size
    removed = drive_backup.prune(token, "FOLDER", keep=2)
    assert sorted(removed) == sorted(names[:2])
    assert "user-doc" in google.files  # never touches files it did not create
    remaining = sorted(f["name"] for f in google.files.values() if f["appProperties"])
    assert remaining == sorted(names[2:])


def test_bad_refresh_token_and_corrupted_upload_fail_loudly(monkeypatch, tmp_path):
    fake = FakeGoogle(corrupt=True)
    monkeypatch.setattr(drive_backup, "API", fake.url)
    monkeypatch.setattr(drive_backup, "OAUTH_URL", fake.url + "/token")
    try:
        with pytest.raises(drive_backup.DriveError, match="access token"):
            drive_backup.access_token("cid", "secret", "WRONG")
        archive = tmp_path / "bionuclei-backup-x.tar.gz"
        archive.write_bytes(b"payload" * 100)
        with pytest.raises(drive_backup.DriveError, match="does not match"):
            drive_backup.upload("AT", "FOLDER", archive, "sha")
        assert not any(f["appProperties"] for f in fake.files.values())  # mismatched copy was deleted
    finally:
        fake.server.shutdown()


def test_unconfigured_run_exits_with_code_3(monkeypatch, capsys):
    for k in ["BIONUCLEI_SERVER_URL", "BIONUCLEI_BACKUP_TOKEN", "GDRIVE_FOLDER_ID", "GDRIVE_CLIENT_ID", "GDRIVE_CLIENT_SECRET", "GDRIVE_REFRESH_TOKEN"]:
        monkeypatch.delenv(k, raising=False)
    assert drive_backup.main() == 3
    assert "not configured" in capsys.readouterr().err
