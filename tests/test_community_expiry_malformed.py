from webapp import community_app

import pytest


def test_malformed_expiry_fails_closed_and_is_deleted(monkeypatch):
    deleted: list[tuple[str, str]] = []
    monkeypatch.setattr(
        community_app,
        "get_job",
        lambda job_id, user_id: {
            "job_id": job_id,
            "status": "completed",
            "expires_at": "not-a-timestamp",
        },
    )
    monkeypatch.setattr(
        community_app,
        "delete_job",
        lambda job_id, user_id: deleted.append((job_id, user_id)) or True,
    )

    with pytest.raises(FileNotFoundError, match="invalid expiry"):
        community_app._ensure_live_job("job-1", "owner-1")

    assert deleted == [("job-1", "owner-1")]
