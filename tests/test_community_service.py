from __future__ import annotations

from pathlib import Path

import pytest

from webapp import community


@pytest.fixture
def isolated_jobs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(community, "JOB_ROOT", tmp_path / "jobs")
    monkeypatch.setattr(community, "DB_PATH", tmp_path / "jobs" / "jobs.sqlite3")
    community.JOB_ROOT.mkdir(parents=True, exist_ok=True)
    return community


def test_create_job_rejects_unknown_algorithm(isolated_jobs):
    with pytest.raises(ValueError, match="Unsupported analysis profile"):
        isolated_jobs.create_job(b"x", "x.tif", "user-1", False, "unknown")


def test_delete_research_copy_requires_existing_job(isolated_jobs):
    with pytest.raises(FileNotFoundError):
        isolated_jobs.delete_research_copy("missing", "user-1")


def test_serialize_contains_consent_and_retention_fields(isolated_jobs):
    job_id = "example"
    with isolated_jobs.DB_LOCK, isolated_jobs._db() as conn:
        conn.execute(
            "INSERT INTO jobs(id,status,created_at,updated_at,expires_at,input_name,retained_copy,research_consent,algorithm_profile,user_id) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                job_id,
                "queued",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
                "2026-01-02T00:00:00+00:00",
                "x.tif",
                0,
                0,
                "auto",
                "user-1",
            ),
        )
        conn.commit()
    payload = isolated_jobs.get_job(job_id, "user-1")
    assert payload is not None
    assert payload["research_consent"] is False
    assert payload["retained_copy"] is False
    assert payload["algorithm_profile"] == "auto"


def test_purge_expired_removes_job(isolated_jobs):
    job_id = "expired"
    root = isolated_jobs.JOB_ROOT / job_id
    root.mkdir(parents=True)
    (root / "input.tif").write_bytes(b"x")
    with isolated_jobs.DB_LOCK, isolated_jobs._db() as conn:
        conn.execute(
            "INSERT INTO jobs(id,status,created_at,updated_at,expires_at,input_name,retained_copy,research_consent,algorithm_profile) VALUES(?,?,?,?,?,?,?,?,?)",
            (job_id, "queued", "2020-01-01T00:00:00+00:00", "2020-01-01T00:00:00+00:00", "2020-01-02T00:00:00+00:00", "x.tif", 0, 0, "auto"),
        )
        conn.commit()
    assert isolated_jobs.purge_expired() == 1
    assert not root.exists()
