from __future__ import annotations

import json
from pathlib import Path

from biomcp.registry import get_server, installable_servers, load_registry


def test_registry_is_valid_and_has_bionuclei() -> None:
    registry = load_registry()
    assert registry["product"] == "BioMCP"
    names = {entry["name"] for entry in registry["servers"]}
    assert "bionuclei" in names


def test_only_explicitly_installable_packs_are_installable() -> None:
    names = {entry["name"] for entry in installable_servers()}
    assert "bionuclei" in names
    assert "bioimagej" not in names
    assert "cellprofiler" not in names


def test_planned_server_cannot_be_used_as_an_installable_pack() -> None:
    entry = get_server("bioimagej")
    assert entry["status"] == "planned"
    assert entry["installable"] is False


def test_registry_is_machine_readable() -> None:
    payload = json.loads(Path("biomcp/registry.json").read_text(encoding="utf-8"))
    assert isinstance(payload["servers"], list)
    assert all(isinstance(entry["name"], str) for entry in payload["servers"])
