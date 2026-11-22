#!/usr/bin/env python3
"""Copy the latest encrypted BioNuclei backup into a Google Drive folder.

Flow: download /admin/backup from the analysis server -> verify checksum and
per-file hashes -> resumable upload to Drive -> confirm Drive's MD5 matches ->
delete only older backups this tool created (tagged with an app property).

The archive is encrypted on the server before it leaves, so Google stores
ciphertext only. The data key is never uploaded.

Environment (GitHub Actions secrets or a local shell):
  BIONUCLEI_SERVER_URL          e.g. https://bionuclei-community-analyzer.onrender.com
  BIONUCLEI_BACKUP_TOKEN        backup-only token (see scripts/make_storage_secrets.py)
  GDRIVE_FOLDER_ID              target folder, e.g. 1IUcF1OuF0beo1e1sLgDOHKyOOF9n8wAY
  GDRIVE_CLIENT_ID / GDRIVE_CLIENT_SECRET / GDRIVE_REFRESH_TOKEN
                                from scripts/drive_authorize.py (one-time consent)
Optional: GDRIVE_KEEP (default 30), BIONUCLEI_DATA_KEY (also prove decryptability).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from bionuclei.storage import IntegrityError, StorageConfigError, _decode_key, verify_backup  # noqa: E402
from pull_backup import download  # noqa: E402

OAUTH_URL = os.getenv("BIONUCLEI_GOOGLE_OAUTH_URL", "https://oauth2.googleapis.com/token")
API = os.getenv("BIONUCLEI_GDRIVE_API", "https://www.googleapis.com")
TAG = "bionuclei_backup"
CHUNK = 8 * 1024 * 1024


class DriveError(RuntimeError):
    pass


def validate_server_url(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    allowed_host = os.getenv(
        "BIONUCLEI_BACKUP_ALLOWED_HOST", "bionuclei-community-analyzer.onrender.com"
    ).strip().lower()
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.hostname.lower() != allowed_host
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise DriveError(
            "Backup server URL must be HTTPS on the configured allowed host, "
            "without embedded credentials, query, or fragment."
        )


def verify_drive_backup(archive: Path, expected_sha256: str, key: bytes | None) -> dict:
    if key is None:
        raise IntegrityError("Drive backup requires BIONUCLEI_DATA_KEY to verify encrypted files.")
    report = verify_backup(archive, expected_sha256, key)
    if report.get("encrypted") is not True:
        raise IntegrityError("Refusing to upload an unencrypted backup to Drive.")
    if report.get("decryption_verified") != report.get("file_count"):
        raise IntegrityError("Backup decryption verification was incomplete.")
    return report


def _request(method: str, url: str, *, token: str | None = None, data: bytes | None = None, headers: dict | None = None, timeout: int = 120):
    h = dict(headers or {})
    if token:
        h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        if exc.code == 308:  # resumable upload: "resume incomplete" is not an error
            return exc
        body = exc.read()[:400].decode("utf-8", "replace")
        raise DriveError(f"{method} {urllib.parse.urlsplit(url).path} failed: HTTP {exc.code} {body}") from exc


def access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    form = urllib.parse.urlencode({"client_id": client_id, "client_secret": client_secret, "refresh_token": refresh_token, "grant_type": "refresh_token"}).encode()
    with _request("POST", OAUTH_URL, data=form, headers={"Content-Type": "application/x-www-form-urlencoded"}) as r:
        payload = json.loads(r.read())
    if "access_token" not in payload:
        raise DriveError("Google did not return an access token. Re-run scripts/drive_authorize.py.")
    return payload["access_token"]


def upload(token: str, folder_id: str, archive: Path, sha256: str) -> dict:
    """Resumable upload; returns Drive's file record (id, name, size, md5Checksum)."""
    size = archive.stat().st_size
    meta = {"name": archive.name, "parents": [folder_id], "mimeType": "application/gzip",
            "appProperties": {TAG: "1", "sha256": sha256}, "description": "Encrypted BioNuclei backup (AES-256-GCM). Restore needs BIONUCLEI_DATA_KEY."}
    with _request("POST", f"{API}/upload/drive/v3/files?uploadType=resumable&supportsAllDrives=true&fields=id", token=token,
                  data=json.dumps(meta).encode(), headers={"Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Type": "application/gzip",
                                                           "X-Upload-Content-Length": str(size)}) as r:
        session = r.headers.get("Location")
    if not session:
        raise DriveError("Drive did not open an upload session.")
    result = None
    with archive.open("rb") as handle:
        offset = 0
        while offset < size:
            chunk = handle.read(CHUNK)
            end = offset + len(chunk) - 1
            r = _request("PUT", session, data=chunk, headers={"Content-Length": str(len(chunk)), "Content-Range": f"bytes {offset}-{end}/{size}"}, timeout=600)
            status = getattr(r, "status", None) or getattr(r, "code", None)
            if status in (200, 201):
                result = json.loads(r.read())
            r.close()
            offset = end + 1
    if not result or "id" not in result:
        raise DriveError("Upload finished without a file id.")
    with _request("GET", f"{API}/drive/v3/files/{result['id']}?fields=id,name,size,md5Checksum&supportsAllDrives=true", token=token) as r:
        info = json.loads(r.read())
    local_md5 = hashlib.md5(archive.read_bytes()).hexdigest()  # Drive reports MD5; used only to confirm transfer integrity
    if int(info.get("size", -1)) != size or info.get("md5Checksum") != local_md5:
        _request("DELETE", f"{API}/drive/v3/files/{info['id']}?supportsAllDrives=true", token=token).close()
        raise DriveError("Drive copy does not match the local archive; the incomplete copy was deleted.")
    return info


def prune(token: str, folder_id: str, keep: int) -> list[str]:
    """Delete older backups in the folder, but only files this tool created and tagged."""
    q = f"'{folder_id}' in parents and trashed=false and appProperties has {{ key='{TAG}' and value='1' }}"
    url = f"{API}/drive/v3/files?" + urllib.parse.urlencode({"q": q, "orderBy": "createdTime desc", "fields": "files(id,name,createdTime)",
                                                             "pageSize": 1000, "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"})
    with _request("GET", url, token=token) as r:
        files = json.loads(r.read()).get("files", [])
    removed = []
    for f in files[max(keep, 1):]:
        _request("DELETE", f"{API}/drive/v3/files/{f['id']}?supportsAllDrives=true", token=token).close()
        removed.append(f["name"])
    return removed


def main() -> int:
    need = ["BIONUCLEI_SERVER_URL", "BIONUCLEI_BACKUP_TOKEN", "BIONUCLEI_DATA_KEY", "GDRIVE_FOLDER_ID", "GDRIVE_CLIENT_ID", "GDRIVE_CLIENT_SECRET", "GDRIVE_REFRESH_TOKEN"]
    missing = [k for k in need if not os.getenv(k)]
    if missing:
        print(f"Drive backup is not configured. Missing: {', '.join(missing)}. See docs/STORAGE_AND_BACKUP.md.", file=sys.stderr)
        return 3
    keep = int(os.getenv("GDRIVE_KEEP", "30"))
    try:
        key = _decode_key(os.environ["BIONUCLEI_DATA_KEY"])
    except StorageConfigError as exc:
        print(f"Drive backup refused: invalid data key configuration ({exc})", file=sys.stderr)
        return 2
    server_url = os.environ["BIONUCLEI_SERVER_URL"]
    try:
        validate_server_url(server_url)
    except DriveError as exc:
        print(f"Drive backup refused: {exc}", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        try:
            archive, expected = download(server_url, os.environ["BIONUCLEI_BACKUP_TOKEN"], Path(tmp))
            report = verify_drive_backup(archive, expected, key)
            token = access_token(os.environ["GDRIVE_CLIENT_ID"], os.environ["GDRIVE_CLIENT_SECRET"], os.environ["GDRIVE_REFRESH_TOKEN"])
            info = upload(token, os.environ["GDRIVE_FOLDER_ID"], archive, report["sha256"])
            removed = prune(token, os.environ["GDRIVE_FOLDER_ID"], keep)
        except (DriveError, IntegrityError, urllib.error.URLError, TimeoutError) as exc:
            print(f"Drive backup failed: {exc}", file=sys.stderr)
            return 1
    print(f"Uploaded {info['name']} to Drive ({int(info['size']):,} bytes, {report['file_count']} files, MD5 confirmed). Removed {len(removed)} older backup(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
