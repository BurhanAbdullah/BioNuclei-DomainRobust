"""Classify changed paths using the files copied into the Render images.

Unknown paths fail closed as runtime-affecting. Only files/prefixes proven not
to be copied into either Render Docker image are excluded from parity checks.
"""
from __future__ import annotations

NON_RUNTIME_PATHS = frozenset({"CHANGELOG.md", "LICENSE"})
NON_RUNTIME_PREFIXES = (".github/workflows/", "tests/", "scripts/")
RENDER_RUNTIME_DOCS = frozenset({"docs/RESEARCH_PROTOCOL.md", "docs/DATASETS.md"})


def is_non_runtime_path(path: str) -> bool:
    """Return true only when a changed path is not shipped into Render images."""
    if not isinstance(path, str) or not path:
        return False
    if path.startswith("docs/"):
        return path not in RENDER_RUNTIME_DOCS
    return path in NON_RUNTIME_PATHS or path.startswith(NON_RUNTIME_PREFIXES)
