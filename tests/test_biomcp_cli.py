from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "biomcp", *args],
        text=True,
        capture_output=True,
        check=False,
    )


def test_biomcp_version_and_list() -> None:
    version = run_cli("--version")
    assert version.returncode == 0
    assert version.stdout.strip() == "0.1.0"

    listing = run_cli("list")
    assert listing.returncode == 0
    assert "bionuclei" in listing.stdout
    assert "deterministic bioimage tools" in listing.stdout


def test_biomcp_dry_run_does_not_write(tmp_path: Path) -> None:
    target = tmp_path / "mcp.json"
    result = run_cli("install", "--path", str(target), "--dry-run")
    assert result.returncode == 0
    assert target.exists() is False
    assert str(target) in result.stdout


def test_biomcp_install_writes_mcp_servers(tmp_path: Path) -> None:
    target = tmp_path / "mcp.json"
    result = run_cli("install", "--path", str(target))
    assert result.returncode == 0
    payload = json.loads(target.read_text())
    entry = payload["mcpServers"]["biomcp_bionuclei"]
    assert entry == {"command": "bionuclei-mcp", "args": []}
