"""Helpers for keeping retryable public health diagnostics truthful."""
from __future__ import annotations


def clear_recovered_health_errors(state: dict[str, object]) -> None:
    """Remove stale error fields after a later health probe succeeds."""
    state.pop("api_health_request_error", None)
    state.pop("api_health_body", None)
