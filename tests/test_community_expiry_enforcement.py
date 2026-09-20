from __future__ import annotations

import sqlite3
from datetime import timedelta

import pytest


@pytest.fixture
def community(tmp_path, monkeypatch):
    import webapp.community as module

    monkeypatch.setattr(module, "JOB_ROOT", tmp_path / "jobs")
    monkeypatch.setattr(module, "DB_PATH", tmp_path / "jobs" / "jobs.sqlite3")
    module.JOB_ROOT.mkdir(parents=True, exist_ok=True)
    return module


def _seed_expired_job(module, job_id: str, user_id: str) -> None:
    root = module._job_dir(job_id)
    (root / "results").mkdir(parents=True)
    (root / "results" / "results.json").write_text("{}", encoding="utf-8")
    (module.JOB_ROOT / f"{job_id}.zip").write_bytes(b"archive")
    now = module._now()
    with module.DB_LOCK, module._db() as conn:
        conn.execute(
            "INSERT INTO jobs(id,status,created_at,updated_at,expires_at,user_id,input_name,retained_copy,research_consent,algorithm_profile,analysis_modules) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                job_id,
                "completed",
                (now - timedelta(hours=2)).isoformat(),
                (now - timedelta(hours=2)).isoformat(),
                (now - timedelta(seconds=1)).isoformat(),
                user_id,
                "input.tif",
                0,
                0,
                "auto",
                "nuclei,morphology,intensity",
            ),
        )
        conn.commit()


def test_expired_job_is_removed_before_metadata_access(community):
    module = community
    job_id = "expired-job"
    user_id = "guest:test"
    _seed_expired_job(module, job_id, user_id)

    assert module.get_job(job_id, user_id) is None
    assert not module._job_dir(job_id).exists()
    assert not (module.JOB_ROOT / f"{job_id}.zip").exists()
    assert module._get_job(job_id, user_id) is None


def test_expired_job_is_removed_before_file_access(community):
    module = community
    job_id = "expired-file"
    user_id = "guest:test"
    _seed_expired_job(module, job_id, user_id)

    with pytest.raises(FileNotFoundError):
        module.get_file(job_id, user_id, "results.json")

    assert not module._job_dir(job_id).exists()
    assert not (module.JOB_ROOT / f"{job_id}.zip").exists()
    assert module._get_job(job_id, user_id) is None


def test_expired_job_is_removed_before_archive_access(community):
    module = community
    job_id = "expired-archive"
    user_id = "guest:test"
    _seed_expired_job(module, job_id, user_id)

    with pytest.raises(FileNotFoundError):
        module.get_archive(job_id, user_id)

    assert not module._job_dir(job_id).exists()
    assert not (module.JOB_ROOT / f"{job_id}.zip").exists()
    assert module._get_job(job_id, user_id) is None
