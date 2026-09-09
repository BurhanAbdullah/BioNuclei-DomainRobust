"""MCP client configuration adapters used by BioMCP install."""
from __future__ import annotations

from pathlib import Path
import json
import os
from typing import Any


def client_paths() -> dict[str, Path]:
    home = Path.home()
    paths: dict[str, Path] = {
        "generic": home / ".config" / "biomcp" / "mcp.json",
        "claude-desktop": home / ".config" / "claude" / "claude_desktop_config.json",
        "codex": home / ".codex" / "config.json",
    }
    if os.name == "nt":
        appdata = Path(os.getenv("APPDATA", home / "AppData/Roaming"))
        paths["claude-desktop"] = appdata / "Claude" / "claude_desktop_config.json"
        paths["codex"] = home / ".codex" / "config.toml"
    return paths


def _merge_json(path: Path, servers: dict[str, Any], dry_run: bool) -> str:
    data: dict[str, Any] = {}
    if path.exists():
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Refusing to overwrite invalid JSON: {path}: {exc}") from exc
        if isinstance(parsed, dict):
            data = parsed
    current = data.setdefault("mcpServers", {})
    if not isinstance(current, dict):
        raise RuntimeError(f"Invalid mcpServers object in {path}")
    current.update(servers)
    rendered = json.dumps(data, indent=2) + "\n"
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    return rendered


def write_client_config(client: str, servers: dict[str, Any], dry_run: bool = False) -> Path:
    paths = client_paths()
    if client not in paths:
        raise ValueError(f"Unsupported BioMCP client: {client}")
    path = paths[client]
    if client == "codex" and path.suffix == ".toml":
        raise ValueError("Codex TOML adapter is not enabled yet; use --clients generic for a portable MCP config")
    _merge_json(path, servers, dry_run)
    return path
