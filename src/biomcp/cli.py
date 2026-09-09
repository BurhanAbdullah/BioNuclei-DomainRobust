"""BioMCP registry, installer and MCP launcher."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from . import __version__
from .registry import get_server, installable_servers, load_registry


def _server_config(name: str) -> dict[str, Any]:
    entry = get_server(name)
    if not entry.get("installable"):
        raise SystemExit(f"BioMCP server '{name}' is not installable (status: {entry['status']}).")
    return {"command": entry["command"], "args": []}


def _config_payload(names: list[str]) -> dict[str, Any]:
    return {"mcpServers": {f"biomcp_{name}": _server_config(name) for name in names}}


def _default_config_paths() -> dict[str, Path]:
    home = Path.home()
    return {
        "generic": home / ".config" / "biomcp" / "mcp.json",
        "claude": home / ".config" / "claude" / "claude_desktop_config.json",
        "codex": home / ".codex" / "config.json",
    }


def _merge_config(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {}
    if path.exists():
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                existing = parsed
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Refusing to overwrite invalid JSON: {path}: {exc}") from exc
    servers = existing.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise SystemExit(f"Invalid mcpServers object in {path}")
    servers.update(payload["mcpServers"])
    path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")


def cmd_list(_: argparse.Namespace) -> int:
    print(f"BioMCP {__version__}")
    for entry in load_registry()["servers"]:
        state = "installable" if entry.get("installable") else entry["status"]
        print(f"  {entry['name']:14} {state:12} {entry['description']}")
    return 0


def cmd_doctor(_: argparse.Namespace) -> int:
    print(f"BioMCP {__version__} doctor")
    print(f"  Registry:             {len(load_registry()['servers'])} server packs")
    for entry in installable_servers():
        command = shutil.which(str(entry["command"]))
        print(f"  {entry['name']:21} {'FOUND ' + command if command else 'MISSING'}")
    try:
        import mcp  # type: ignore
        print(f"  MCP SDK:              {getattr(mcp, '__version__', 'installed')}")
    except Exception:
        print("  MCP SDK:              MISSING (install the [mcp] extra)")
    checkpoint = os.getenv("BIONUCLEI_CHECKPOINT")
    print(f"  BioNuclei checkpoint: {'configured' if checkpoint and Path(checkpoint).expanduser().is_file() else 'not configured'}")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    names = args.servers.split(",") if args.servers else [e["name"] for e in installable_servers()]
    for name in names:
        get_server(name)
    payload = _config_payload(names)
    if args.path:
        targets = [Path(args.path).expanduser()]
    elif args.clients == "generic":
        targets = [_default_config_paths()["generic"]]
    else:
        paths = _default_config_paths()
        targets = [paths[name] for name in args.clients.split(",") if name in paths]
        if not targets:
            raise SystemExit("No valid client target selected")
    for path in targets:
        if args.dry_run:
            print(path)
        else:
            _merge_config(path, payload)
            print(f"configured {path}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    entry = get_server(args.server)
    if not entry.get("installable"):
        raise SystemExit(f"BioMCP server '{args.server}' is not installable (status: {entry['status']}).")
    return int(subprocess.run([entry["command"], *args.extra], check=False).returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="biomcp", description="BioMCP registry, installer and MCP launcher")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_list = sub.add_parser("list", help="list registered BioMCP server packs")
    p_list.set_defaults(func=cmd_list)
    p_doctor = sub.add_parser("doctor", help="check BioMCP and server prerequisites")
    p_doctor.set_defaults(func=cmd_doctor)
    p_install = sub.add_parser("install", help="generate/update MCP client configuration")
    p_install.add_argument("--servers", help="comma-separated registered server names; defaults to installable packs")
    p_install.add_argument("--clients", default="generic", help="generic, or comma-separated generic/claude/codex")
    p_install.add_argument("--path", help="write a specific config JSON path")
    p_install.add_argument("--dry-run", action="store_true")
    p_install.set_defaults(func=cmd_install)
    p_run = sub.add_parser("run", help="launch a registered MCP server over stdio")
    p_run.add_argument("server", help="registered server name")
    p_run.add_argument("extra", nargs=argparse.REMAINDER)
    p_run.set_defaults(func=cmd_run)
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
