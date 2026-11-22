from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from webapp import community_app


@pytest.mark.parametrize(
    ("error", "expected_cleanup", "message_fragment"),
    [
        (
            community_app.community_service._FAILED_JOB_ERROR
            + community_app.community_service._FAILED_JOB_CLEANUP_SUFFIX,
            "incomplete",
            "transient artifacts may remain",
        ),
        (
            community_app.community_service._FAILED_JOB_ERROR,
            "verified",
            "cleanup was verified",
        ),
        (
            "Legacy failure record with no cleanup evidence",
            "unknown",
            "cleanup status is unknown",
        ),
    ],
)
def test_failed_progress_reports_cleanup_evidence_truthfully(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: str,
    expected_cleanup: str,
    message_fragment: str,
) -> None:
    job_id = "failed-progress-cleanup"
    output = tmp_path / job_id / "results"
    output.mkdir(parents=True)
    # A stale partial PDF must not make a failed job report-ready.
    (output / "analysis_report.pdf").write_bytes(b"partial report")

    monkeypatch.setattr(
        community_app.community_service,
        "_job_dir",
        lambda _job_id: tmp_path / job_id,
    )
    monkeypatch.setattr(
        community_app,
        "authenticate_optional",
        lambda _request: SimpleNamespace(id="owner-a", email=None, guest=True),
    )
    monkeypatch.setattr(
        community_app,
        "get_job",
        lambda _job_id, _user_id: {
            "job_id": job_id,
            "status": "failed",
            "error": error,
        },
    )

    with TestClient(community_app.app) as client:
        response = client.get(f"/jobs/{job_id}/progress")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["phase"] == "failed"
    assert payload["cleanup_status"] == expected_cleanup
    assert message_fragment in payload["message"].lower()
    assert payload["report_ready"] is False


def test_completed_progress_only_reports_ready_with_completed_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_id = "completed-progress-report"
    output = tmp_path / job_id / "results"
    output.mkdir(parents=True)
    (output / "analysis_report.pdf").write_bytes(b"complete report")

    monkeypatch.setattr(
        community_app.community_service,
        "_job_dir",
        lambda _job_id: tmp_path / job_id,
    )
    monkeypatch.setattr(
        community_app,
        "authenticate_optional",
        lambda _request: SimpleNamespace(id="owner-a", email=None, guest=True),
    )
    monkeypatch.setattr(
        community_app,
        "get_job",
        lambda _job_id, _user_id: {
            "job_id": job_id,
            "status": "completed",
            "error": None,
        },
    )

    with TestClient(community_app.app) as client:
        response = client.get(f"/jobs/{job_id}/progress")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["cleanup_status"] == "verified"
    assert payload["report_ready"] is True

def test_root_and_health_report_configured_result_retention(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(community_app.community_service, "DEFAULT_RESULT_RETENTION_HOURS", 24)

    root_payload = community_app.root()
    health_payload = community_app.health()

    assert root_payload["result_retention_hours"] == 24
    assert "expire after 24 hours" in root_payload["retention"]
    assert health_payload["result_retention_hours"] == 24
