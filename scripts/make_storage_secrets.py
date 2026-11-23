#!/usr/bin/env python3
"""Generate the secrets for encrypted storage and PC backups. Run once, locally.

Prints three values:
  BIONUCLEI_DATA_KEY            -> server environment (Render) AND your password manager
  BIONUCLEI_BACKUP_TOKEN_SHA256 -> server environment (Render) only
  BIONUCLEI_BACKUP_TOKEN        -> your PC's backup task only

Nothing is written to disk. Never commit these values to git.
"""
from __future__ import annotations

import hashlib
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from bionuclei.storage import generate_key  # noqa: E402

if __name__ == "__main__":
    token = secrets.token_urlsafe(48)
    print("# Server (Render > Environment):")
    print(f"BIONUCLEI_DATA_KEY={generate_key()}")
    print(f"BIONUCLEI_BACKUP_TOKEN_SHA256={hashlib.sha256(token.encode()).hexdigest()}")
    print("\n# Your PC (backup task environment only):")
    print(f"BIONUCLEI_BACKUP_TOKEN={token}")
    print("\n# Also store BIONUCLEI_DATA_KEY in a password manager. Without it, backups cannot be restored.")
