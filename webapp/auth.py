"""Minimal Supabase bearer-token verification for the Community Analyzer.

The browser uses Supabase Auth for account creation/sign-in. The server never
receives a password; it validates the user's access token against Supabase Auth
and uses the returned immutable user id as the owner of analysis jobs.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from fastapi import HTTPException, Request


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str | None


def _config() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    if not url or not key:
        raise HTTPException(status_code=503, detail="Account service is not configured")
    return url, key


def authenticate(request: Request) -> AuthenticatedUser:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in to use the BioNuclei Community Analyzer")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing access token")
    url, key = _config()
    req = urllib.request.Request(
        f"{url}/auth/v1/user",
        headers={"apikey": key, "Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        raise HTTPException(status_code=401, detail="Could not validate account session") from exc
    user_id = payload.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid account session")
    return AuthenticatedUser(id=str(user_id), email=payload.get("email"))
