from scripts.e2e_health_state import clear_recovered_health_errors


def test_successful_health_retry_clears_stale_error_fields() -> None:
    state: dict[str, object] = {
        "api_health_http_status": 200,
        "api_health_request_error": "ReadTimeout",
        "api_health_body": "stale upstream error body",
        "api_health_attempts": [
            {"attempt": 1, "error": "ReadTimeout"},
            {"attempt": 2, "http_status": 200, "result": "http_200"},
        ],
    }

    clear_recovered_health_errors(state)

    assert "api_health_request_error" not in state
    assert "api_health_body" not in state
    assert state["api_health_http_status"] == 200
    attempts = state["api_health_attempts"]
    assert isinstance(attempts, list)
    assert attempts[-1]["result"] == "http_200"
