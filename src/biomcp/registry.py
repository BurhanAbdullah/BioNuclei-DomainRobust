"""BioMCP server-pack registry.

The registry is intentionally declarative: BioMCP may only expose packs whose
runtime command and scientific status are explicitly registered.  A registry
entry describes the MCP server boundary; it does not claim that every planned
scientific capability is implemented.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "biomcp" / "registry.json"


def load_registry(path: Path | None = None) -> dict[str, Any]:
    """Load and validate the BioMCP registry."""
    target = path or REGISTRY_PATH
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("servers"), list):
        raise ValueError("BioMCP registry must contain a servers list")
    seen: set[str] = set()
    for entry in payload["servers"]:
        if not isinstance(entry, dict):
            raise ValueError("Each registry server entry must be an object")
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Registry entries require a non-empty name")
        if name in seen:
            raise ValueError(f"Duplicate BioMCP server: {name}")
        seen.add(name)
        if entry.get("status") not in {"experimental", "validated", "planned", "deprecated"}:
            raise ValueError(f"Invalid registry status for {name}")
        if entry.get("installable") and not entry.get("command"):
            raise ValueError(f"Installable server {name} requires a command")
    return payload


def get_server(name: str, path: Path | None = None) -> dict[str, Any]:
    """Return one registered server or raise KeyError."""
    for entry in load_registry(path)["servers"]:
        if entry["name"] == name:
            return entry
    raise KeyError(f"Unknown BioMCP server: {name}")


def installable_servers(path: Path | None = None) -> list[dict[str, Any]]:
    """Return only packs that are explicitly installable."""
    return [entry for entry in load_registry(path)["servers"] if entry.get("installable") is True]
