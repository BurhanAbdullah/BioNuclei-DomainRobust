#!/usr/bin/env python3
"""Smoke-test the deployed BioNuclei-DomainRobust website.

Usage:
    python scripts/check_website.py https://example.github.io/repo/
"""
from __future__ import annotations

import re
import sys
import urllib.request


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_website.py URL", file=sys.stderr)
        return 2

    url = sys.argv[1]
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "BioNuclei-DomainRobust-site-check/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
            body = response.read(200_000).decode("utf-8", "replace")
            final_url = response.geturl()
    except Exception as exc:
        print(f"WEBSITE_CHECK_FAILED: {exc}", file=sys.stderr)
        return 1

    if status != 200:
        print(f"WEBSITE_CHECK_FAILED: HTTP {status}", file=sys.stderr)
        return 1

    title = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
    if not title or "BioNuclei" not in title.group(1):
        print("WEBSITE_CHECK_FAILED: expected BioNuclei site title not found", file=sys.stderr)
        return 1

    required = (
        "Reliable AI for biological imaging.",
        "Explore the research programme.",
        "Open research. Public code. Evidence before claims.",
    )
    missing = [item for item in required if item not in body]
    if missing:
        print(f"WEBSITE_CHECK_FAILED: missing homepage content: {missing}", file=sys.stderr)
        return 1

    print(f"WEBSITE_CHECK_OK: HTTP {status}; final_url={final_url}")
    print(f"TITLE: {title.group(1).strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
