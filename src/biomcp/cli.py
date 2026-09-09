"""Small PowerMCP-style installer/launcher for the BioMCP product.

BioMCP is a separate interoperability layer. Scientific measurements remain
implemented by the BioNuclei backend; this CLI only configures and launches
that backend through MCP.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import __version__

SERVER_COMMAND = "bionuclei-mcp"
SERVER_NAME = "biomcp_bionuclei"
TOOLS = [
    ("bionuclei", "BioNuclei MCP server; deterministic bioimage tools and read-only research resources"),
]


def _config_payload() -> dict[str, Any]:
    return {
        "mcpServers": {
            SERVER_NAME: {
                "command": SERVER_COMMAND,
                "args": [],
            }
        }
    }


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
            parsed = json.loads(path.read_text())
            if isinstance(parsed, dict):
                existing = parsed
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Refusing to overwrite invalid JSON: {path}: {exc}") from exc
    servers = existing.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise SystemExit(f"Invalid mcpServers object in {path}")
    servers.update(payload["mcpServers"])
    path.write_text(json.dumps(existing, indent=2) + "\n")


def cmd_list(_: argparse.Namespace) -> int:
    print(f"BioMCP {__version__}")
    for name, description in TOOLS:
        print(f"  {name:12} {description}")
    return 0


def cmd_doctor(_: argparse.Namespace) -> int:
    print(f"BioMCP {__version__} doctor")
    server = shutil.which(SERVER_COMMAND)
    print(f"  MCP server command: {'FOUND ' + server if server else 'MISSING'}")
    try:
        import mcp  # type: ignore
        print(f"  MCP SDK:           {getattr(mcp, '__version__', 'installed')}")
    except Exception:
        print("  MCP SDK:           MISSING (install BioNuclei with the [mcp] extra)")
    checkpoint = os.getenv("BIONUCLEI_CHECKPOINT")
    if checkpoint and Path(checkpoint).expanduser().is_file():
        print("  checkpoint:        configured")
    else:
        print("  checkpoint:        not configured (required for model inference)")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    payload = _config_payload()
    targets: list[Path]
    if args.path:
        targets = [Path(args.path).expanduser()]
    elif args.clients == "generic":
        targets = [_default_config_paths()["generic"]]
    else:
        paths = _default_config_paths()
        targets = [paths[name] for name in args.clients.split(",") if name in paths]
    for path in targets:
        if args.dry_run:
            print(path)
        else:
            _merge_config(path, payload)
            print(f"configured {path}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    if args.server != "bionuclei":
        raise SystemExit(f"Unknown server: {args.server}")
    command = [SERVER_COMMAND, *args.extra]
    completed = subprocess.run(command, check=False)
    return int(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="biomcp", description="BioMCP installer and MCP launcher")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_install = sub.add_parser("install", help="generate/update MCP client configuration")
    p_install.add_argument("--clients", default="generic", help="generic, or comma-separated generic/claude/codex")
    p_install.add_argument("--path", help="write a specific config JSON path")
    p_install.add_argument("--dry-run", action="store_true")
    p_install.set_defaults(func=cmd_install)

    p_list = sub.add_parser("list", help="list available BioMCP server packs")
    p_list.set_defaults(func=cmd_list)

    p_doctor = sub.add_parser("doctor", help="check local BioMCP prerequisites")
    p_doctor.set_defaults(func=cmd_doctor)

    p_run = sub.add_parser("run", help="launch an MCP server over stdio")
    p_run.add_argument("server", choices=["bionuclei"])
    p_run.add_argument("extra", nargs=argparse.REMAINDER)
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
