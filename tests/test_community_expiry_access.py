from datetime import datetime, timedelta, timezone

import pytest

from webapp import community_app


def _payload(expires_at: datetime | str) -> dict[str, object]:
    return {
        "job_id": "job-1",
        "status": "completed",
        "expires_at": expires_at.isoformat() if isinstance(expires_at, datetime) else expires_at,
    }


def test_expired_job_is_deleted_and_rejected(monkeypatch):
    deleted: list[tuple[str, str]] = []
    monkeypatch.setattr(
        community_app,
        "get_job",
        lambda job_id, user_id: _payload(datetime.now(timezone.utc) - timedelta(seconds=1)),
    )
    monkeypatch.setattr(
        community_app,
        "delete_job",
        lambda job_id, user_id: deleted.append((job_id, user_id)) or True,
    )

    with pytest.raises(FileNotFoundError, match="expired"):
        community_app._ensure_live_job("job-1", "owner-1")

    assert deleted == [("job-1", "owner-1")]


def test_unexpired_job_remains_accessible(monkeypatch):
    payload = _payload(datetime.now(timezone.utc) + timedelta(minutes=5))
    monkeypatch.setattr(community_app, "get_job", lambda job_id, user_id: payload)
    monkeypatch.setattr(
        community_app,
        "delete_job",
        lambda job_id, user_id: pytest.fail("unexpired job must not be deleted"),
    )

    assert community_app._ensure_live_job("job-1", "owner-1") is payload


def test_malformed_expiry_fails_closed_and_is_deleted(monkeypatch):
    deleted: list[tuple[str, str]] = []
    monkeypatch.setattr(
        community_app,
        "get_job",
        lambda job_id, user_id: _payload("not-a-timestamp"),
    )
    monkeypatch.setattr(
        community_app,
        "delete_job",
        lambda job_id, user_id: deleted.append((job_id, user_id)) or True,
    )

    with pytest.raises(FileNotFoundError, match="invalid expiry"):
        community_app._ensure_live_job("job-1", "owner-1")

    assert deleted == [("job-1", "owner-1")]
