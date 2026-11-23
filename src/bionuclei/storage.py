"""Encrypted, owner-isolated storage for BioNuclei user data, plus backup archives.

Design
------
* One configurable root (``BIONUCLEI_DATA_ROOT``, default ``data``)::

      <root>/users/<account id>/<category>/<file>
      <root>/guests/<guest digest>/<category>/<file>
      <root>/system/...

  Directory names are opaque identifiers (Supabase account UUIDs, SHA-256
  guest digests), never e-mail addresses or user-supplied names.
* Every user-supplied name is validated and every resolved path must stay
  inside its owner's directory, so ``../`` and absolute paths are rejected.
* File contents are encrypted with AES-256-GCM (``cryptography`` library).
  The 32-byte key comes from ``BIONUCLEI_DATA_KEY`` (URL-safe base64) and is
  never written to disk by this module. Each file's path relative to the root
  is the GCM associated data, so copying one user's ciphertext into another
  user's folder makes it fail to decrypt.
* Without a key the store refuses to write, unless
  ``BIONUCLEI_ALLOW_UNENCRYPTED_STORAGE=1`` is set for local development.

Password hashing is not handled here: account passwords are managed by
Supabase Auth and never reach BioNuclei. Transport security is HTTPS at the
hosting layer. These are separate mechanisms from file encryption.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

MAGIC = b"BNE1"
NONCE_BYTES = 12
CATEGORIES = frozenset({"projects", "images", "analyses", "annotations", "reports", "exports"})
_ID = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class StorageError(Exception):
    """Base class for storage failures."""


class StorageConfigError(StorageError):
    """The store is not configured safely (for example, no encryption key)."""


class UnsafePathError(StorageError):
    """A name or path would escape its owner's directory or is not allowed."""


class IntegrityError(StorageError):
    """Stored bytes failed authentication: tampered, moved, or wrong key."""


@dataclass(frozen=True)
class Owner:
    """An account user or a guest session, as produced by ``webapp.auth``."""

    kind: str  # "user" or "guest"
    ident: str

    @classmethod
    def from_auth_id(cls, auth_id: str) -> "Owner":
        if auth_id.startswith("guest:"):
            return cls("guest", auth_id.removeprefix("guest:"))
        return cls("user", auth_id)

    def __post_init__(self) -> None:
        if self.kind not in {"user", "guest"}:
            raise UnsafePathError("Owner kind must be 'user' or 'guest'.")
        if not _ID.fullmatch(self.ident or ""):
            raise UnsafePathError("Owner identifier is not an opaque ID (letters, digits, '-' or '_', 8 to 128 characters).")


def generate_key() -> str:
    """A new 256-bit data key, URL-safe base64 encoded, for BIONUCLEI_DATA_KEY."""
    return base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")


def key_fingerprint(key: bytes) -> str:
    """Short public fingerprint so a backup can be matched to its key. Not the key."""
    return hashlib.sha256(b"bionuclei-key-fingerprint" + key).hexdigest()[:16]


def _decode_key(value: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode(value.strip() + "=" * (-len(value.strip()) % 4))
    except Exception as exc:
        raise StorageConfigError("BIONUCLEI_DATA_KEY is not valid URL-safe base64.") from exc
    if len(key) != 32:
        raise StorageConfigError("BIONUCLEI_DATA_KEY must decode to exactly 32 bytes (AES-256).")
    return key


class SecureStore:
    def __init__(self, root: Path, key: bytes | None, *, allow_unencrypted: bool = False) -> None:
        if key is None and not allow_unencrypted:
            raise StorageConfigError("No encryption key configured. Set BIONUCLEI_DATA_KEY (see scripts/make_storage_secrets.py).")
        if key is not None and len(key) != 32:
            raise StorageConfigError("Encryption key must be 32 bytes.")
        self.root = Path(root).expanduser().resolve()
        self._key = key
        self.encrypted = key is not None

    @classmethod
    def from_env(cls) -> "SecureStore":
        raw = os.getenv("BIONUCLEI_DATA_KEY", "")
        key = _decode_key(raw) if raw else None
        allow = os.getenv("BIONUCLEI_ALLOW_UNENCRYPTED_STORAGE", "") == "1"
        return cls(Path(os.getenv("BIONUCLEI_DATA_ROOT", "data")), key, allow_unencrypted=allow)

    # ---------- paths ----------
    def owner_dir(self, owner: Owner) -> Path:
        return self.root / ("users" if owner.kind == "user" else "guests") / owner.ident

    def path_for(self, owner: Owner, category: str, name: str) -> Path:
        if category not in CATEGORIES:
            raise UnsafePathError(f"Unknown storage category '{category}'.")
        if not isinstance(name, str) or not _NAME.fullmatch(name) or ".." in name:
            raise UnsafePathError("File name must be letters, digits, '.', '-' or '_' and must not contain '..'.")
        owner_root = self.owner_dir(owner).resolve(strict=False)
        path = self.owner_dir(owner) / category / name
        try:
            # resolve() follows any symlink already on disk, so a planted link cannot redirect writes.
            path.resolve(strict=False).relative_to(owner_root)
        except ValueError as exc:
            raise UnsafePathError("Resolved path escapes the owner's directory.") from exc
        return path

    def _aad(self, path: Path) -> bytes:
        return path.resolve().relative_to(self.root).as_posix().encode("utf-8")

    # ---------- crypto ----------
    def _seal(self, path: Path, data: bytes) -> bytes:
        if not self.encrypted:
            return data
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce = os.urandom(NONCE_BYTES)
        return MAGIC + nonce + AESGCM(self._key).encrypt(nonce, data, self._aad(path))

    def _open(self, path: Path, blob: bytes) -> bytes:
        if not self.encrypted:
            return blob
        from cryptography.exceptions import InvalidTag
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        if not blob.startswith(MAGIC) or len(blob) < len(MAGIC) + NONCE_BYTES + 16:
            raise IntegrityError("Stored file is not a BioNuclei encrypted blob.")
        nonce = blob[len(MAGIC):len(MAGIC) + NONCE_BYTES]
        try:
            return AESGCM(self._key).decrypt(nonce, blob[len(MAGIC) + NONCE_BYTES:], self._aad(path))
        except InvalidTag as exc:
            raise IntegrityError("Stored file failed authentication (tampered, moved, or wrong key).") from exc

    # ---------- operations ----------
    def write_bytes(self, owner: Owner, category: str, name: str, data: bytes) -> Path:
        path = self.path_for(owner, category, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        blob = self._seal(path, data)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(blob)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        return path

    def read_bytes(self, owner: Owner, category: str, name: str) -> bytes:
        path = self.path_for(owner, category, name)
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(name)
        return self._open(path, path.read_bytes())

    def delete(self, owner: Owner, category: str, name: str) -> bool:
        path = self.path_for(owner, category, name)
        if path.is_file() and not path.is_symlink():
            path.unlink()
            return True
        return False

    def list(self, owner: Owner, category: str) -> list[str]:
        if category not in CATEGORIES:
            raise UnsafePathError(f"Unknown storage category '{category}'.")
        folder = self.owner_dir(owner) / category
        return sorted(p.name for p in folder.iterdir() if p.is_file() and not p.name.startswith(".tmp-")) if folder.is_dir() else []

    def usage_bytes(self, owner: Owner) -> int:
        folder = self.owner_dir(owner)
        return sum(p.stat().st_size for p in folder.rglob("*") if p.is_file()) if folder.is_dir() else 0

    def delete_owner(self, owner: Owner) -> bool:
        """Remove every file of one owner (account deletion or guest expiry)."""
        folder = self.owner_dir(owner)
        if not folder.exists():
            return False
        shutil.rmtree(folder)
        return True

    # ---------- backup ----------
    def _backup_files(self) -> Iterator[Path]:
        for top in ("users", "guests", "system"):
            base = self.root / top
            if base.is_dir():
                for p in sorted(base.rglob("*")):
                    if p.is_file() and not p.is_symlink() and not p.name.startswith(".tmp-") and "backups" not in p.relative_to(self.root).parts:
                        yield p

    def build_backup(self, destination_dir: Path) -> tuple[Path, str, dict]:
        """Write a .tar.gz of the stored (still encrypted) files plus a manifest.

        Returns (archive path, SHA-256 of the archive, manifest). The archive
        never contains plaintext when the store is encrypted, and never contains the key.
        """
        destination_dir.mkdir(parents=True, exist_ok=True)
        created = datetime.now(timezone.utc)
        entries = []
        for p in self._backup_files():
            rel = p.relative_to(self.root).as_posix()
            entries.append({"path": rel, "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
        manifest = {
            "format": "bionuclei-backup/1",
            "created_utc": created.isoformat(),
            "encrypted": self.encrypted,
            "cipher": "AES-256-GCM, associated data = path relative to the data root" if self.encrypted else None,
            "key_fingerprint": key_fingerprint(self._key) if self.encrypted else None,
            "file_count": len(entries),
            "total_bytes": sum(e["bytes"] for e in entries),
            "files": entries,
        }
        archive = destination_dir / f"bionuclei-backup-{created.strftime('%Y%m%dT%H%M%SZ')}.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            data = json.dumps(manifest, indent=2).encode("utf-8")
            info = tarfile.TarInfo("manifest.json")
            info.size = len(data)
            info.mtime = int(created.timestamp())
            tar.addfile(info, io.BytesIO(data))
            for e in entries:
                tar.add(self.root / e["path"], arcname=f"data/{e['path']}", recursive=False)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        return archive, digest, manifest


def verify_backup(archive: Path, expected_sha256: str | None = None, key: bytes | None = None) -> dict:
    """Check a backup archive: checksum, manifest, per-file hashes and, with the key, decryptability.

    Never writes decrypted content to disk.
    """
    digest = hashlib.sha256(Path(archive).read_bytes()).hexdigest()
    if expected_sha256 and digest != expected_sha256:
        raise IntegrityError("Backup archive checksum does not match the server's checksum.")
    with tarfile.open(archive, "r:gz") as tar:
        member = tar.getmember("manifest.json")
        manifest = json.loads(tar.extractfile(member).read().decode("utf-8"))
        if manifest.get("format") != "bionuclei-backup/1":
            raise IntegrityError("Unknown backup format.")
        aes = None
        if key is not None:
            if manifest.get("key_fingerprint") != key_fingerprint(key):
                raise IntegrityError("The provided key does not match this backup's key fingerprint.")
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            aes = AESGCM(key)
        decrypted = 0
        for entry in manifest["files"]:
            name = f"data/{entry['path']}"
            if ".." in Path(entry["path"]).parts or entry["path"].startswith("/"):
                raise IntegrityError("Backup manifest contains an unsafe path.")
            blob = tar.extractfile(tar.getmember(name)).read()
            if hashlib.sha256(blob).hexdigest() != entry["sha256"]:
                raise IntegrityError(f"File hash mismatch inside backup: {entry['path']}")
            if aes is not None and manifest.get("encrypted"):
                from cryptography.exceptions import InvalidTag
                if not blob.startswith(MAGIC):
                    raise IntegrityError(f"Not an encrypted blob: {entry['path']}")
                try:
                    aes.decrypt(blob[len(MAGIC):len(MAGIC) + NONCE_BYTES], blob[len(MAGIC) + NONCE_BYTES:], entry["path"].encode("utf-8"))
                except InvalidTag as exc:
                    raise IntegrityError(f"File cannot be decrypted with this key: {entry['path']}") from exc
                decrypted += 1
    return {"sha256": digest, "file_count": manifest["file_count"], "total_bytes": manifest["total_bytes"],
            "created_utc": manifest["created_utc"], "decryption_verified": decrypted if key is not None else None}
