#!/usr/bin/env python3
"""Run BioNuclei on this computer. Everything is saved locally.

    python scripts/run_local.py --checkpoint path/to/bionuclei.pt

This starts the analysis server and the website together, both reachable only
from this computer (127.0.0.1), and opens the Lab in your browser. Results,
reports and job files are saved under ./data (change with --data). Nothing is
sent to Render or any other server; sign-in with an account still uses
Supabase, but guest mode needs nothing external.

Make a backup copy of the data folder at any time:

    python scripts/run_local.py --backup D:\\BioNuclei-backups

Files in ./data are encrypted with a key kept at ~/.bionuclei/data.key, outside
the data folder. Back that key up somewhere safe (a password manager or a USB
stick): a backup cannot be opened without it.
"""
from __future__ import annotations

import argparse
import base64
import http.server
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT / "src"))

PUBLIC_API = "https://bionuclei-community-analyzer.onrender.com"


def ensure_key(path: Path) -> str:
    """Load or create the local data key (256-bit, URL-safe base64), readable only by this user."""
    path = path.expanduser()
    if path.is_file():
        return path.read_text(encoding="ascii").strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="ascii") as handle:
        handle.write(key + "\n")
    return key


def local_config(api_base: str) -> bytes:
    """The site's browser config, pointed at the local analysis server."""
    text = (DOCS / "assets" / "bionuclei-config.js").read_text(encoding="utf-8")
    if PUBLIC_API not in text:
        raise SystemExit("Could not find the public API address in docs/assets/bionuclei-config.js.")
    return text.replace(PUBLIC_API, api_base).encode("utf-8")


class SiteHandler(http.server.SimpleHTTPRequestHandler):
    """Serves docs/ and swaps in the local config. No directory listings."""

    config: bytes = b""

    def do_GET(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path.endswith("/assets/bionuclei-config.js"):
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(self.config)))
            self.end_headers()
            self.wfile.write(self.config)
            return
        if path.endswith("/") and path != "/":
            self.send_error(404)
            return
        super().do_GET()

    def list_directory(self, path):  # never expose folder listings
        self.send_error(404)
        return None

    def log_message(self, *args):
        pass


def port_free(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def wait_for(url: str, seconds: float) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except Exception:
            time.sleep(0.3)
    return False


def make_backup(data: Path, key: str, destination: Path) -> Path:
    from bionuclei.storage import SecureStore, _decode_key, verify_backup
    store = SecureStore(data, _decode_key(key))
    archive, digest, manifest = store.build_backup(destination)
    report = verify_backup(archive, digest, _decode_key(key))
    print(f"Backup saved: {archive}\n{manifest['file_count']} files, {manifest['total_bytes']:,} bytes, all verified (sha256 {digest[:16]}…).")
    return archive


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoint", type=Path, default=Path(os.getenv("BIONUCLEI_CHECKPOINT", "")) if os.getenv("BIONUCLEI_CHECKPOINT") else None,
                    help="Released BioNuclei model checkpoint (.pt)")
    ap.add_argument("--data", type=Path, default=ROOT / "data", help="Where results are saved (default ./data)")
    ap.add_argument("--key-file", type=Path, default=Path("~/.bionuclei/data.key"), help="Encryption key file, kept outside the data folder")
    ap.add_argument("--keep-days", type=int, default=30, help="How long results are kept (default 30 days)")
    ap.add_argument("--api-port", type=int, default=8000)
    ap.add_argument("--site-port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--backup", type=Path, metavar="FOLDER", help="Write a verified backup of the data folder to FOLDER and exit")
    args = ap.parse_args(argv)

    data = args.data.expanduser().resolve()
    data.mkdir(parents=True, exist_ok=True)
    key = ensure_key(args.key_file)
    if args.backup:
        make_backup(data, key, args.backup.expanduser().resolve())
        return 0

    if not args.checkpoint or not args.checkpoint.expanduser().is_file():
        print("A model checkpoint is required: --checkpoint path/to/bionuclei.pt (or set BIONUCLEI_CHECKPOINT).", file=sys.stderr)
        return 2
    for port in (args.api_port, args.site_port):
        if not port_free(port):
            print(f"Port {port} is already in use. Close the other program or pick another port.", file=sys.stderr)
            return 2

    api = f"http://127.0.0.1:{args.api_port}"
    site = f"http://127.0.0.1:{args.site_port}"
    env = {**os.environ,
           "BIONUCLEI_CHECKPOINT": str(args.checkpoint.expanduser().resolve()),
           "BIONUCLEI_DATA_ROOT": str(data), "BIONUCLEI_DATA_KEY": key,
           "BIONUCLEI_JOB_DIR": str(data / "jobs"),
           "BIONUCLEI_RESULT_RETENTION_HOURS": str(max(1, args.keep_days) * 24),
           "BIONUCLEI_ALLOWED_ORIGINS": f"{site},http://localhost:{args.site_port}",
           "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), str(ROOT), os.environ.get("PYTHONPATH", "")])}
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "webapp.community_app:app", "--host", "127.0.0.1", "--port", str(args.api_port)], cwd=ROOT, env=env)
    SiteHandler.config = local_config(api)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", args.site_port), partial(SiteHandler, directory=str(DOCS)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        if not wait_for(f"{api}/health", 90):
            print("The analysis server did not start. See the messages above.", file=sys.stderr)
            return 1
        lab = f"{site}/bionuclei-app.html"
        print(f"\nBioNuclei is running on this computer.\n  Lab:     {lab}\n  Website: {site}/index.html\n  Data:    {data}\n  Key:     {args.key_file.expanduser()}  (back this up separately)\nPress Ctrl+C to stop.\n")
        if not args.no_browser:
            webbrowser.open(lab)
        server.wait()
        return server.returncode or 0
    except KeyboardInterrupt:
        print("\nStopping BioNuclei…")
        return 0
    finally:
        httpd.shutdown()
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
