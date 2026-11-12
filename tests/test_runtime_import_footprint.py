from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_public_community_import_defers_report_only_scientific_packages(tmp_path: Path) -> None:
    """The production app should not load pandas/scikit-image before inference."""
    root = Path(__file__).resolve().parents[1]
    script = """
import sys
import webapp.community_app

loaded = sorted(
    name for name in sys.modules
    if name == "pandas"
    or name.startswith("pandas.")
    or name == "skimage"
    or name.startswith("skimage.")
    or name == "bionuclei.data"
)
if loaded:
    raise SystemExit("report-only packages imported during app startup: " + ", ".join(loaded))
"""
    env = os.environ.copy()
    env["BIONUCLEI_JOB_DIR"] = str(tmp_path / "jobs")
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=90,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
