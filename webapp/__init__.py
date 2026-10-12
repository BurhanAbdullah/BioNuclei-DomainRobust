"""Deployable web adapters for BioNuclei/BioMCP."""

# The Modal image copies the scientific package to /app/src while loading the
# web adapter from /app/webapp. Make that source tree importable before any
# web adapter imports bionuclei.*. This is a no-op for normal installed-package
# environments where /app/src is absent.
import sys
from pathlib import Path

_MODAL_SRC = Path("/app/src")
if _MODAL_SRC.is_dir() and str(_MODAL_SRC) not in sys.path:
    sys.path.insert(0, str(_MODAL_SRC))
