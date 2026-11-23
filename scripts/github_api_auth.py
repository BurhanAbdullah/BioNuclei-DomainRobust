"""Shared authenticated headers for GitHub REST requests made by CI."""
from __future__ import annotations


def github_api_headers(token: str | None, *, user_agent: str) -> dict[str, str]:
    """Build read-only GitHub API headers without ever logging the credential."""
    credential = token.strip() if isinstance(token, str) else ""
    if not credential:
        raise RuntimeError("GITHUB_TOKEN is required for authenticated GitHub API requests")
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {credential}",
        "User-Agent": user_agent,
    }
