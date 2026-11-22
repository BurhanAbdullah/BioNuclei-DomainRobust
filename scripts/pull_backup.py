#!/usr/bin/env python3
"""Pull an encrypted BioNuclei backup from the server onto this computer.

Run this on the administrator's PC on a schedule (Windows Task Scheduler,
macOS launchd or cron). The PC only makes an outgoing HTTPS request; it opens
no ports and accepts no connections, so the server can never reach into it.

    set BIONUCLEI_BACKUP_TOKEN=...            (Windows: setx, or the task's environment)
    python scripts/pull_backup.py --url https://bionuclei-community-analyzer.onrender.com --dest D:\\BioNuclei\\backups

Optional: set BIONUCLEI_DATA_KEY as well to prove every file in the backup can
be decrypted (nothing is written in plaintext). Keep that key somewhere other
than the backup folder, for example a password manager: a backup is useless
without the key, and the key must not sit next to the data it protects.
"""
from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bionuclei.storage import IntegrityError, _decode_key, verify_backup  # noqa: E402


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not forward the backup bearer token to a redirect target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def download(url: str, token: str, dest: Path, timeout: int = 600) -> tuple[Path, str]:
    """Download /admin/backup to a temporary file; return its path and the server's checksum."""
    request = urllib.request.Request(url.rstrip("/") + "/admin/backup", headers={"X-BioNuclei-Backup-Token": token, "User-Agent": "BioNuclei-backup/1"})
    dest.mkdir(parents=True, exist_ok=True)
    partial = dest / ".incoming.tar.gz.part"
    opener = urllib.request.build_opener(_NoRedirect)
    with opener.open(request, timeout=timeout) as response:
        expected = response.headers.get("X-Backup-SHA256", "")
        disposition = response.headers.get("Content-Disposition", "")
        name = disposition.split("filename=")[-1].strip('"; ') if "filename=" in disposition else "bionuclei-backup.tar.gz"
        with open(partial, "wb") as handle:
            while chunk := response.read(1 << 20):
                handle.write(chunk)
    if not expected:
        partial.unlink(missing_ok=True)
        raise IntegrityError("Server did not send a backup checksum.")
    final = dest / Path(name).name
    return partial.replace(final), expected


def prune(dest: Path, keep: int) -> list[Path]:
    """Keep the newest `keep` backups; delete older ones. Only touches this script's files."""
    archives = sorted(dest.glob("bionuclei-backup-*.tar.gz"))
    removed = archives[:-keep] if keep > 0 else []
    for path in removed:
        path.unlink()
    return removed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", required=True, help="Base URL of the BioNuclei analysis server")
    parser.add_argument("--dest", required=True, type=Path, help="Backup folder on this computer")
    parser.add_argument("--keep", type=int, default=14, help="How many backups to keep (default 14)")
    args = parser.parse_args(argv)

    token = os.getenv("BIONUCLEI_BACKUP_TOKEN", "")
    if len(token) < 32:
        print("BIONUCLEI_BACKUP_TOKEN is not set. It is read from the environment, never from the command line.", file=sys.stderr)
        return 2
    if not args.url.startswith("https://") and not args.url.startswith("http://localhost") and not args.url.startswith("http://127.0.0.1"):
        print("Refusing to send the backup token over plain HTTP. Use an https:// URL.", file=sys.stderr)
        return 2
    key = _decode_key(os.environ["BIONUCLEI_DATA_KEY"]) if os.getenv("BIONUCLEI_DATA_KEY") else None
    archive: Path | None = None
    try:
        archive, expected = download(args.url, token, args.dest)
        report = verify_backup(archive, expected, key)
    except urllib.error.HTTPError as exc:
        print(f"Backup failed: server answered HTTP {exc.code} ({exc.reason}).", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"Backup failed: could not reach the server ({exc}). It may be asleep; try again in a minute.", file=sys.stderr)
        return 1
    except IntegrityError as exc:
        print(f"Backup failed verification and was not kept: {exc}", file=sys.stderr)
        if archive is not None:
            archive.unlink(missing_ok=True)  # only the archive that just failed; older good backups stay
        return 1
    removed = prune(args.dest, args.keep)
    check = f", decryption verified for {report['decryption_verified']} files" if report["decryption_verified"] is not None else ""
    print(f"Saved {archive.name}: {report['file_count']} files, {report['total_bytes']} bytes, sha256 {report['sha256'][:16]}…{check}. Removed {len(removed)} old backup(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
