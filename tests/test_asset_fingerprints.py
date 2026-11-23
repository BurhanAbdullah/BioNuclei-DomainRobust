import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("stamp_assets", ROOT / "scripts" / "stamp_assets.py")
stamp_assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stamp_assets)


def test_every_local_css_and_js_link_has_a_current_fingerprint():
    stale = []
    for page in sorted((ROOT / "docs").glob("*.html")):
        text = page.read_text(encoding="utf-8")
        if stamp_assets.stamp(text) != text:
            stale.append(page.name)
    assert not stale, f"Run python scripts/stamp_assets.py; stale fingerprints in {stale}"
