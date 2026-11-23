import base64
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import threading
import time
from pathlib import Path

import pytest

from bionuclei.storage import (IntegrityError, Owner, SecureStore, StorageConfigError, UnsafePathError,
                               generate_key, verify_backup)

ROOT = Path(__file__).resolve().parents[1]
ALICE = Owner("user", "3f1c2a9e-7b44-4d8e-9a10-2b6f0c1d5e77")
BOB = Owner("user", "9a8b7c6d-1111-4222-8333-444455556666")
GUEST = Owner.from_auth_id("guest:" + hashlib.sha256(b"guest-token").hexdigest())
SECRET = b"unpublished nuclei measurements 42.7"


def key():
    return base64.urlsafe_b64decode(generate_key())


@pytest.fixture
def store(tmp_path):
    return SecureStore(tmp_path / "data", key())


def test_round_trip_and_ciphertext_on_disk(store):
    path = store.write_bytes(ALICE, "reports", "run1.json", SECRET)
    assert store.read_bytes(ALICE, "reports", "run1.json") == SECRET
    on_disk = path.read_bytes()
    assert SECRET not in on_disk and on_disk.startswith(b"BNE1")
    assert path.is_relative_to(store.root / "users" / ALICE.ident / "reports")


def test_same_plaintext_encrypts_differently_each_time(store):
    a = store.write_bytes(ALICE, "reports", "a.json", SECRET).read_bytes()
    b = store.write_bytes(ALICE, "reports", "b.json", SECRET).read_bytes()
    assert a != b  # fresh nonce per write


def test_tampering_is_detected(store):
    path = store.write_bytes(ALICE, "images", "img.tif", SECRET)
    blob = bytearray(path.read_bytes())
    blob[-5] ^= 0x01
    path.write_bytes(bytes(blob))
    with pytest.raises(IntegrityError):
        store.read_bytes(ALICE, "images", "img.tif")


def test_ciphertext_moved_to_another_user_does_not_decrypt(store):
    src = store.write_bytes(ALICE, "reports", "r.json", SECRET)
    dst = store.path_for(BOB, "reports", "r.json")
    dst.parent.mkdir(parents=True)
    dst.write_bytes(src.read_bytes())
    with pytest.raises(IntegrityError):
        store.read_bytes(BOB, "reports", "r.json")


def test_wrong_key_cannot_read(store, tmp_path):
    store.write_bytes(ALICE, "reports", "r.json", SECRET)
    other = SecureStore(store.root, key())
    with pytest.raises(IntegrityError):
        other.read_bytes(ALICE, "reports", "r.json")


@pytest.mark.parametrize("name", ["../x", "..", "a/b", "/etc/passwd", ".hidden", "a\\b", "x\x00y", "", "é.tif", "a" * 200])
def test_unsafe_names_are_rejected(store, name):
    with pytest.raises(UnsafePathError):
        store.write_bytes(ALICE, "images", name, b"x")


def test_unknown_category_and_email_ids_are_rejected(store):
    with pytest.raises(UnsafePathError):
        store.write_bytes(ALICE, "../../system", "x.json", b"x")
    with pytest.raises(UnsafePathError):
        Owner("user", "alice@example.com")
    with pytest.raises(UnsafePathError):
        Owner("user", "../../etc")


def test_planted_symlink_cannot_redirect_writes(store, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    folder = store.owner_dir(ALICE)
    folder.mkdir(parents=True)
    (folder / "images").symlink_to(outside, target_is_directory=True)
    with pytest.raises(UnsafePathError):
        store.write_bytes(ALICE, "images", "x.tif", b"x")
    assert not any(outside.iterdir())


def test_owners_are_isolated_and_deletion_is_scoped(store):
    store.write_bytes(ALICE, "projects", "p.json", b"alice")
    store.write_bytes(BOB, "projects", "p.json", b"bob")
    store.write_bytes(GUEST, "projects", "p.json", b"guest")
    assert store.list(BOB, "projects") == ["p.json"]
    assert store.read_bytes(BOB, "projects", "p.json") == b"bob"
    assert store.owner_dir(GUEST).parent.name == "guests"
    assert store.delete_owner(ALICE)
    assert not store.owner_dir(ALICE).exists()
    assert store.read_bytes(BOB, "projects", "p.json") == b"bob"
    assert store.read_bytes(GUEST, "projects", "p.json") == b"guest"
    assert store.usage_bytes(BOB) > 0 and store.usage_bytes(ALICE) == 0


def test_refuses_to_store_without_key_unless_dev_flag(tmp_path, monkeypatch):
    monkeypatch.delenv("BIONUCLEI_DATA_KEY", raising=False)
    monkeypatch.delenv("BIONUCLEI_ALLOW_UNENCRYPTED_STORAGE", raising=False)
    monkeypatch.setenv("BIONUCLEI_DATA_ROOT", str(tmp_path / "d"))
    with pytest.raises(StorageConfigError):
        SecureStore.from_env()
    monkeypatch.setenv("BIONUCLEI_DATA_KEY", "too-short")
    with pytest.raises(StorageConfigError):
        SecureStore.from_env()
    monkeypatch.delenv("BIONUCLEI_DATA_KEY")
    monkeypatch.setenv("BIONUCLEI_ALLOW_UNENCRYPTED_STORAGE", "1")
    assert SecureStore.from_env().encrypted is False


def test_backup_contains_only_ciphertext_and_verifies_with_key(store, tmp_path):
    k = store._key
    store.write_bytes(ALICE, "reports", "r.json", SECRET)
    store.write_bytes(GUEST, "images", "g.tif", SECRET * 3)
    archive, digest, manifest = store.build_backup(tmp_path / "out")
    assert manifest["file_count"] == 2 and manifest["encrypted"]
    raw = archive.read_bytes()
    with tarfile.open(archive) as tar:
        names = tar.getnames()
        contents = b"".join(tar.extractfile(m).read() for m in tar.getmembers() if m.isfile())
    assert "manifest.json" in names and all(n == "manifest.json" or n.startswith("data/") for n in names)
    assert SECRET not in contents and SECRET not in raw
    assert base64.urlsafe_b64encode(k).decode().rstrip("=") not in contents.decode("latin-1")
    report = verify_backup(archive, digest, k)
    assert report["decryption_verified"] == 2
    with pytest.raises(IntegrityError, match="key fingerprint"):
        verify_backup(archive, digest, key())
    with pytest.raises(IntegrityError, match="checksum"):
        verify_backup(archive, "0" * 64)


def test_backup_endpoint_requires_the_backup_token(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import webapp.community_app as app_module

    token = "t" * 48
    data_key = generate_key()
    monkeypatch.setenv("BIONUCLEI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("BIONUCLEI_DATA_KEY", data_key)
    SecureStore.from_env().write_bytes(ALICE, "reports", "r.json", SECRET)
    client = TestClient(app_module.app)

    monkeypatch.delenv("BIONUCLEI_BACKUP_TOKEN_SHA256", raising=False)
    assert client.get("/admin/backup", headers={"X-BioNuclei-Backup-Token": token}).status_code == 503
    monkeypatch.setenv("BIONUCLEI_BACKUP_TOKEN_SHA256", hashlib.sha256(token.encode()).hexdigest())
    assert client.get("/admin/backup").status_code == 401
    assert client.get("/admin/backup", headers={"X-BioNuclei-Backup-Token": "x" * 48}).status_code == 403
    # An account bearer token or a guest token is not a backup token.
    assert client.get("/admin/backup", headers={"X-BioNuclei-Guest-Token": token}).status_code == 401

    ok = client.get("/admin/backup", headers={"X-BioNuclei-Backup-Token": token})
    assert ok.status_code == 200 and ok.headers["x-backup-encrypted"] == "true"
    assert hashlib.sha256(ok.content).hexdigest() == ok.headers["x-backup-sha256"]
    assert SECRET not in ok.content


def test_pull_backup_script_end_to_end_against_live_server(tmp_path):
    """Real HTTP: uvicorn serves the app, the PC script pulls, verifies with the key, and prunes."""
    pytest.importorskip("uvicorn")
    token = "b" * 48
    data_key = generate_key()
    env = {**os.environ, "BIONUCLEI_DATA_ROOT": str(tmp_path / "server-data"), "BIONUCLEI_DATA_KEY": data_key,
           "BIONUCLEI_BACKUP_TOKEN_SHA256": hashlib.sha256(token.encode()).hexdigest(),
           "BIONUCLEI_JOB_DIR": str(tmp_path / "jobs"), "PYTHONPATH": str(ROOT / "src") + os.pathsep + str(ROOT)}
    store = SecureStore(tmp_path / "server-data", base64.urlsafe_b64decode(data_key))
    store.write_bytes(ALICE, "reports", "r.json", SECRET)
    port = 8000 + (os.getpid() % 900) + 37
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "webapp.community_app:app", "--port", str(port)],
                              cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        import urllib.request
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1)
                break
            except Exception:
                time.sleep(0.1)
        dest = tmp_path / "pc-backups"
        dest.mkdir()
        for i in range(3):
            (dest / f"bionuclei-backup-2026010{i}T000000Z.tar.gz").write_bytes(b"old")
        run_env = {**os.environ, "BIONUCLEI_BACKUP_TOKEN": token, "BIONUCLEI_DATA_KEY": data_key}
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "pull_backup.py"), "--url", f"http://127.0.0.1:{port}",
                                 "--dest", str(dest), "--keep", "2"], env=run_env, capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stderr
        assert "decryption verified for 1 files" in result.stdout
        kept = sorted(p.name for p in dest.glob("bionuclei-backup-*.tar.gz"))
        assert len(kept) == 2 and kept[-1] > "bionuclei-backup-2026010"
        bad = subprocess.run([sys.executable, str(ROOT / "scripts" / "pull_backup.py"), "--url", f"http://127.0.0.1:{port}",
                              "--dest", str(dest)], env={**os.environ, "BIONUCLEI_BACKUP_TOKEN": "w" * 48}, capture_output=True, text=True, timeout=60)
        assert bad.returncode == 1 and "HTTP 403" in bad.stderr
        insecure = subprocess.run([sys.executable, str(ROOT / "scripts" / "pull_backup.py"), "--url", "http://example.org", "--dest", str(dest)],
                                  env=run_env, capture_output=True, text=True, timeout=30)
        assert insecure.returncode == 2 and "plain HTTP" in insecure.stderr
    finally:
        server.terminate()
        server.wait(timeout=10)
