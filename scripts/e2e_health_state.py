"""Helpers for keeping retryable public health diagnostics truthful."""
from __future__ import annotations


def clear_recovered_health_errors(state: dict[str, object]) -> None:
    """Remove stale error fields after a later health probe succeeds."""
    state.pop("api_health_request_error", None)
    state.pop("api_health_body", None)


def record_health_response(
    state: dict[str, object], status_code: int, body_excerpt: str
) -> None:
    """Keep diagnostics aligned with the latest HTTP response."""
    state.pop("api_health_request_error", None)
    if status_code == 200:
        clear_recovered_health_errors(state)
    else:
        state["api_health_body"] = body_excerpt


def record_health_request_error(state: dict[str, object], error: str) -> None:
    """Keep diagnostics aligned with the latest failed request."""
    state.pop("api_health_body", None)
    state["api_health_request_error"] = error
