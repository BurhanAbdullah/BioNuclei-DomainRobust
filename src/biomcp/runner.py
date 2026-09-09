"""Registry-backed BioMCP server launcher."""
from __future__ import annotations

import shutil
import subprocess

from .registry import get_server


def launch(name: str, extra: list[str] | None = None) -> int:
    entry = get_server(name)
    if not entry.get("installable"):
        raise RuntimeError(f"Server '{name}' is not installable (status: {entry['status']}).")
    command = str(entry["command"])
    if not shutil.which(command):
        raise RuntimeError(f"BioMCP server command not found on PATH: {command}")
    return int(subprocess.run([command, *(extra or [])], check=False).returncode)
