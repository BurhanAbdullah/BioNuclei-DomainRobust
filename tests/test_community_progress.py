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



def test_analyze_returns_429_before_creating_a_job_when_capacity_is_full(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(community_app.community_service, "_checkpoint", lambda: None)
    monkeypatch.setattr(
        community_app,
        "authenticate_optional",
        lambda _request: SimpleNamespace(id="owner-a", email=None, guest=True),
    )

    def reject_admission():
        raise community_app.community_service.JobCapacityError("Analyzer is at capacity.")

    def unexpected_job_creation(*_args, **_kwargs):
        pytest.fail("A full worker must reject the upload before creating a job.")

    monkeypatch.setattr(community_app.community_service, "reserve_job_slot", reject_admission)
    monkeypatch.setattr(community_app, "create_job", unexpected_job_creation)

    with TestClient(community_app.app) as client:
        response = client.post(
            "/analyze",
            files={"image": ("sample.tif", b"not-read-when-full", "image/tiff")},
        )

    assert response.status_code == 429, response.text
    assert response.headers["Retry-After"] == "60"
    assert "at capacity" in response.json()["detail"].lower()


def test_analyze_releases_worker_slot_when_upload_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slots = community_app.community_service.threading.BoundedSemaphore(1)
    monkeypatch.setattr(community_app.community_service, "_ACTIVE_JOB_SLOTS", slots)
    monkeypatch.setattr(community_app.community_service, "_checkpoint", lambda: None)
    monkeypatch.setattr(
        community_app,
        "authenticate_optional",
        lambda _request: SimpleNamespace(id="owner-a", email=None, guest=True),
    )

    with TestClient(community_app.app) as client:
        response = client.post(
            "/analyze",
            files={"image": ("empty.tif", b"", "image/tiff")},
        )

    assert response.status_code == 400, response.text
    reservation = community_app.community_service.reserve_job_slot()
    reservation.release()
