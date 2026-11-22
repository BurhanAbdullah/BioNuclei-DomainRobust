#!/usr/bin/env python3
"""One-time Google consent that yields GDRIVE_REFRESH_TOKEN for scripts/drive_backup.py.

1. In Google Cloud Console create an OAuth client of type "Desktop app" and
   enable the Google Drive API for that project.
2. Run:  python scripts/drive_authorize.py --client-id ... --client-secret ...
3. A browser opens. Sign in with the Google account that owns the backup
   folder and approve. The refresh token is printed. Store it, the client id
   and the client secret as GitHub repository secrets.

The scope is drive, because writing into a folder you created yourself in
Drive requires it (the narrower drive.file scope only reaches files the tool
created). The token is used only by the backup job; revoke it any time at
https://myaccount.google.com/permissions.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import http.server
import json
import secrets
import threading
import urllib.parse
import urllib.request
import webbrowser

SCOPE = "https://www.googleapis.com/auth/drive"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client-id", required=True)
    ap.add_argument("--client-secret", required=True)
    args = ap.parse_args()
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    result: dict = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            if query.get("state", [""])[0] == state and "code" in query:
                result["code"] = query["code"][0]
                message = b"BioNuclei backup authorised. You can close this tab."
            else:
                message = b"Authorisation failed or was cancelled."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(message)

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    redirect = f"http://127.0.0.1:{server.server_port}/"
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": args.client_id, "redirect_uri": redirect, "response_type": "code", "scope": SCOPE,
        "access_type": "offline", "prompt": "consent", "state": state, "code_challenge": challenge, "code_challenge_method": "S256"})
    threading.Thread(target=server.handle_request, daemon=True).start()
    print("Opening the Google consent page. If it does not open, visit:\n" + url)
    webbrowser.open(url)
    server_thread_wait = 300
    import time
    for _ in range(server_thread_wait * 10):
        if "code" in result:
            break
        time.sleep(0.1)
    if "code" not in result:
        print("No authorisation received.")
        return 1
    form = urllib.parse.urlencode({"code": result["code"], "client_id": args.client_id, "client_secret": args.client_secret,
                                   "redirect_uri": redirect, "grant_type": "authorization_code", "code_verifier": verifier}).encode()
    with urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=form)) as r:
        tokens = json.loads(r.read())
    if "refresh_token" not in tokens:
        print("Google did not return a refresh token. Remove the app at https://myaccount.google.com/permissions and run again.")
        return 1
    print("\nAdd these as GitHub repository secrets (Settings > Secrets and variables > Actions):")
    print(f"GDRIVE_CLIENT_ID={args.client_id}\nGDRIVE_CLIENT_SECRET=<your client secret>\nGDRIVE_REFRESH_TOKEN={tokens['refresh_token']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
