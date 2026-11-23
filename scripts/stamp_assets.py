"""Add content fingerprints (?v=<sha256[:10]>) to local CSS/JS links in docs/*.html.

Browsers and the GitHub Pages CDN cache assets/*.css and assets/*.js. Without a
fingerprint, returning visitors can see new HTML styled by an old stylesheet.
Run after editing any asset:  python scripts/stamp_assets.py
tests/test_asset_fingerprints.py fails if a fingerprint is stale.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"
# The runtime config is rewritten in place by local mode and intercepted by the
# live end-to-end gate, so its URL must stay exact.
UNSTAMPED = {"assets/bionuclei-config.js"}
PATTERN = re.compile(r'((?:href|src)=")(assets/[\w./-]+\.(?:css|js))(?:\?v=[0-9a-f]+)?(")')


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:10]


def stamp(html: str) -> str:
    def replace(match: re.Match) -> str:
        asset = DOCS / match.group(2)
        if match.group(2) in UNSTAMPED:
            return f"{match.group(1)}{match.group(2)}{match.group(3)}"
        if not asset.is_file():
            return match.group(0)
        return f"{match.group(1)}{match.group(2)}?v={fingerprint(asset)}{match.group(3)}"
    return PATTERN.sub(replace, html)


def main() -> int:
    changed = 0
    for page in sorted(DOCS.glob("*.html")):
        text = page.read_text(encoding="utf-8")
        new = stamp(text)
        if new != text:
            page.write_text(new, encoding="utf-8")
            changed += 1
    print(f"stamped {changed} page(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
