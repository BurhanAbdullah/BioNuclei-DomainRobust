"""Serialize and verify public E2E failure evidence before artifact upload."""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path


def serialize_failure_payload(state: Mapping[str, object]) -> str:
    """Return the single JSON payload used for both the artifact and job log."""
    return json.dumps(
        {"status": "FAIL", **state},
        indent=2,
        sort_keys=True,
        default=str,
    ) + "\n"


def persist_failure_payload(path: Path, payload_text: str) -> None:
    """Write the exact logged payload and fail if read-back differs."""
    path.write_text(payload_text, encoding="utf-8")
    if path.read_text(encoding="utf-8") != payload_text:
        raise OSError("Persisted failure evidence differs from the logged payload")
