from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from webapp import community


@pytest.fixture
def isolated_jobs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(community, "JOB_ROOT", tmp_path / "jobs")
    monkeypatch.setattr(community, "DB_PATH", tmp_path / "jobs" / "jobs.sqlite3")
    community.JOB_ROOT.mkdir(parents=True, exist_ok=True)
    return community


def test_job_slot_reservation_is_bounded_and_idempotent(isolated_jobs, monkeypatch):
    slots = isolated_jobs.threading.BoundedSemaphore(1)
    monkeypatch.setattr(isolated_jobs, "_ACTIVE_JOB_SLOTS", slots)

    reservation = isolated_jobs.reserve_job_slot()
    with pytest.raises(isolated_jobs.JobCapacityError, match="at capacity"):
        isolated_jobs.reserve_job_slot()

    reservation.release()
    reservation.release()
    replacement = isolated_jobs.reserve_job_slot()
    replacement.release()


def test_create_job_rejects_when_worker_capacity_is_reserved(isolated_jobs, monkeypatch):
    slots = isolated_jobs.threading.BoundedSemaphore(1)
    monkeypatch.setattr(isolated_jobs, "_ACTIVE_JOB_SLOTS", slots)
    reservation = isolated_jobs.reserve_job_slot()

    with pytest.raises(isolated_jobs.JobCapacityError, match="at capacity"):
        isolated_jobs.create_job(b"x", "x.tif", "user-1", False, "auto")

    assert list(isolated_jobs.JOB_ROOT.iterdir()) == []
    reservation.release()


def test_create_job_releases_slot_when_worker_start_fails(isolated_jobs, monkeypatch):
    slots = isolated_jobs.threading.BoundedSemaphore(1)
    monkeypatch.setattr(isolated_jobs, "_ACTIVE_JOB_SLOTS", slots)

    def fail_start(_thread):
        raise RuntimeError("thread start failed")

    monkeypatch.setattr(isolated_jobs.threading.Thread, "start", fail_start)
    with pytest.raises(RuntimeError, match="Could not start the analysis worker"):
        isolated_jobs.create_job(b"x", "x.tif", "user-1", False, "auto")

    replacement = isolated_jobs.reserve_job_slot()
    replacement.release()


def test_run_releases_reserved_slot_after_failure_cleanup(isolated_jobs, monkeypatch):
    slots = isolated_jobs.threading.BoundedSemaphore(1)
    monkeypatch.setattr(isolated_jobs, "_ACTIVE_JOB_SLOTS", slots)
    reservation = isolated_jobs.reserve_job_slot()
    root = isolated_jobs.JOB_ROOT / "worker-failure"
    root.mkdir(parents=True)
    image_path = root / "input.tif"
    image_path.write_bytes(b"synthetic")

    monkeypatch.setattr(isolated_jobs, "_job_dir", lambda _job_id: root)

    def fail_status_update(*_args, **_kwargs):
        raise RuntimeError("synthetic worker failure")

    monkeypatch.setattr(isolated_jobs, "_set_job", fail_status_update)
    monkeypatch.setattr(isolated_jobs, "_cleanup_failed_job", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(isolated_jobs, "_get_job", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(isolated_jobs, "_remove_job_artifacts", lambda *_args, **_kwargs: True)

    isolated_jobs._run(
        "worker-failure",
        "user-1",
        image_path,
        "input.tif",
        False,
        "auto",
        {"nuclei"},
        channel=0,
        time=0,
        z=0,
        field=0,
        reservation=reservation,
    )

    replacement = isolated_jobs.reserve_job_slot()
    replacement.release()


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
            (job_id, "completed", "2020-01-01T00:00:00+00:00", "2020-01-01T00:00:00+00:00", "2020-01-02T00:00:00+00:00", "x.tif", 0, 0, "auto"),
        )
        conn.commit()
    assert isolated_jobs.purge_expired() == 1
    assert not root.exists()


def test_delete_research_copy_is_owner_scoped_and_requires_opt_in(isolated_jobs):
    module = isolated_jobs
    job_id = "research-copy-owned"
    root = module._job_dir(job_id) / "research_copy"
    root.mkdir(parents=True)
    (root / "private.txt").write_text("retained", encoding="utf-8")
    now = module._now().isoformat()
    expiry = (module._now() + timedelta(hours=1)).isoformat()
    with module.DB_LOCK, module._db() as conn:
        conn.execute(
            "INSERT INTO jobs(id,status,created_at,updated_at,expires_at,user_id,input_name,retained_copy,research_consent,algorithm_profile,analysis_modules) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (job_id,"completed",now,now,expiry,"owner-a","x.tif",1,1,"auto","nuclei"),
        )
        conn.commit()
    with pytest.raises(FileNotFoundError):
        module.delete_research_copy(job_id, "owner-b")
    assert (root / "private.txt").is_file()
    assert module.delete_research_copy(job_id, "owner-a") is True
    assert not root.exists()
    row = module._get_job(job_id, "owner-a")
    assert row is not None and row["retained_copy"] == 0 and row["research_consent"] == 0


def test_recover_interrupted_job_fails_orphan_and_removes_transient_data(isolated_jobs):
    module = isolated_jobs
    job_id = "orphaned-planning-job"
    user_id = "user-orphan"
    root = module._job_dir(job_id)
    root.mkdir(parents=True)
    (root / "input.tif").write_bytes(b"private transient input")
    (root / "results").mkdir()
    (root / "results" / "partial.json").write_text("{}", encoding="utf-8")
    archive = module.JOB_ROOT / f"{job_id}.zip"
    archive.write_bytes(b"partial archive")
    now = module._now()
    created = (now - timedelta(minutes=20)).isoformat()
    updated = (now - timedelta(minutes=10)).isoformat()
    expires = (now - timedelta(hours=2)).isoformat()
    with module.DB_LOCK, module._db() as conn:
        conn.execute(
            "INSERT INTO jobs(id,status,created_at,updated_at,expires_at,user_id,input_name,retained_copy,research_consent,algorithm_profile,analysis_modules) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (job_id, "planning", created, updated, expires, user_id, "input.tif", 0, 0, "auto", "intensity,nuclei"),
        )
        conn.commit()

    assert module.recover_interrupted_jobs(now=now, stale_after=timedelta(minutes=5)) == 1
    # Failure persistence starts a fresh, finite retention window even when
    # the abandoned active job's original expiry elapsed during the outage.
    assert module.purge_expired() == 0
    row = module._get_job(job_id, user_id)
    assert row is not None and row["status"] == "failed"
    assert "worker stopped" in row["error"].lower()
    assert module._get_job(job_id, user_id)["expires_at"] > now.isoformat()
    assert not root.exists()
    assert not archive.exists()
    assert module.get_job(job_id, user_id)["status"] == "failed"


def test_recover_interrupted_job_does_not_delete_a_live_worker(isolated_jobs):
    from types import SimpleNamespace

    module = isolated_jobs
    job_id = "live-planning-job"
    user_id = "user-live"
    root = module._job_dir(job_id)
    root.mkdir(parents=True)
    marker = root / "input.tif"
    marker.write_bytes(b"still owned by live worker")
    now = module._now()
    created = (now - timedelta(minutes=20)).isoformat()
    updated = (now - timedelta(minutes=10)).isoformat()
    expires = (now + timedelta(hours=1)).isoformat()
    with module.DB_LOCK, module._db() as conn:
        conn.execute(
            "INSERT INTO jobs(id,status,created_at,updated_at,expires_at,user_id,input_name,retained_copy,research_consent,algorithm_profile,analysis_modules) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (job_id, "planning", created, updated, expires, user_id, "input.tif", 0, 0, "auto", "intensity,nuclei"),
        )
        conn.commit()
    module.ACTIVE_JOB_THREADS[job_id] = SimpleNamespace(is_alive=lambda: True)
    try:
        assert module.recover_interrupted_jobs(now=now, stale_after=timedelta(minutes=5)) == 0
        row = module._get_job(job_id, user_id)
        assert row is not None and row["status"] == "planning"
        assert marker.read_bytes() == b"still owned by live worker"
    finally:
        module.ACTIVE_JOB_THREADS.pop(job_id, None)

def _seed_expired_terminal_job(
    module,
    job_id: str,
    user_id: str,
    *,
    status: str = "failed",
    expires_at: str | None = None,
):
    now = module._now()
    root = module._job_dir(job_id)
    root.mkdir(parents=True, exist_ok=True)
    (root / "input.tif").write_bytes(b"transient input")
    archive = module.JOB_ROOT / f"{job_id}.zip"
    archive.write_bytes(b"transient archive")
    expiry = expires_at or (now - timedelta(minutes=1)).isoformat()
    with module.DB_LOCK, module._db() as conn:
        conn.execute(
            "INSERT INTO jobs(id,status,created_at,updated_at,expires_at,input_name,retained_copy,research_consent,algorithm_profile,user_id) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (job_id, status, now.isoformat(), now.isoformat(), expiry, "input.tif", 0, 0, "auto", user_id),
        )
        conn.commit()
    return root, archive


def test_expired_failed_job_is_removed_before_metadata_access(isolated_jobs):
    module = isolated_jobs
    job_id = "expired-failed-access"
    user_id = "owner-a"
    root, archive = _seed_expired_terminal_job(module, job_id, user_id)

    assert module.get_job(job_id, user_id) is None
    assert module._get_job(job_id, user_id) is None
    assert not root.exists()
    assert not archive.exists()


def test_expired_failed_job_is_removed_before_user_listing(isolated_jobs):
    module = isolated_jobs
    job_id = "expired-failed-listing"
    user_id = "owner-a"
    root, archive = _seed_expired_terminal_job(module, job_id, user_id)

    assert module.get_jobs_for_user(user_id) == []
    assert module._get_job(job_id, user_id) is None
    assert not root.exists()
    assert not archive.exists()


def test_malformed_terminal_expiry_fails_closed_and_cleans_artifacts(isolated_jobs):
    module = isolated_jobs
    job_id = "malformed-expiry"
    user_id = "owner-a"
    root, archive = _seed_expired_terminal_job(
        module, job_id, user_id, status="completed", expires_at="not-a-timestamp"
    )

    assert module.get_job(job_id, user_id) is None
    assert module._get_job(job_id, user_id) is None
    assert not root.exists()
    assert not archive.exists()


def test_expired_job_cleanup_failure_denies_access_and_preserves_metadata(
    isolated_jobs, monkeypatch: pytest.MonkeyPatch
):
    module = isolated_jobs
    job_id = "expired-cleanup-failure"
    user_id = "owner-a"
    root, archive = _seed_expired_terminal_job(module, job_id, user_id)

    def fail_rmtree(_path):
        raise PermissionError("synthetic cleanup denial")

    monkeypatch.setattr(module.shutil, "rmtree", fail_rmtree)

    assert module.get_job(job_id, user_id) is None
    assert module._get_job(job_id, user_id) is not None
    assert root.exists()
    assert archive.exists()
    assert module.purge_expired() == 0
    assert module._get_job(job_id, user_id) is not None


def test_expired_timestamp_does_not_hide_active_job(isolated_jobs):
    module = isolated_jobs
    job_id = "active-expired-timestamp"
    user_id = "owner-a"
    now = module._now()
    root = module._job_dir(job_id)
    root.mkdir(parents=True)
    (root / "input.tif").write_bytes(b"live worker input")
    with module.DB_LOCK, module._db() as conn:
        conn.execute(
            "INSERT INTO jobs(id,status,created_at,updated_at,expires_at,input_name,retained_copy,research_consent,algorithm_profile,user_id) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                job_id, "running", now.isoformat(), now.isoformat(),
                (now - timedelta(minutes=1)).isoformat(), "input.tif", 0, 0, "auto", user_id,
            ),
        )
        conn.commit()

    payload = module.get_job(job_id, user_id)
    assert payload is not None and payload["status"] == "running"
    assert root.exists()



def test_create_job_cleans_partial_upload_and_reports_verified_cleanup(
    isolated_jobs, monkeypatch: pytest.MonkeyPatch
):
    from types import SimpleNamespace

    module = isolated_jobs
    job_id = "queue-upload-write-failure"
    owner_id = "owner-write-failure"
    monkeypatch.setattr(module.uuid, "uuid4", lambda: SimpleNamespace(hex=job_id))
    input_path = module._job_dir(job_id) / "input.tif"
    original_write_bytes = Path.write_bytes

    def fail_after_partial_write(path: Path, data: bytes) -> int:
        if path == input_path:
            original_write_bytes(path, data[:5])
            raise OSError("synthetic disk-full failure")
        return original_write_bytes(path, data)

    monkeypatch.setattr(Path, "write_bytes", fail_after_partial_write)
    with pytest.raises(module.JobCreationError, match="cleanup status is verified") as exc_info:
        module.create_job(b"private upload bytes", "input.tif", owner_id, False, "auto")

    assert exc_info.value.job_id == job_id
    assert exc_info.value.stage == "upload_persistence"
    assert exc_info.value.cleanup_status == "verified"
    row = module._get_job(job_id, owner_id)
    assert row is not None and row["status"] == "failed"
    assert row["error"] == module._FAILED_JOB_ERROR
    assert not module._job_dir(job_id).exists()
    assert not (module.JOB_ROOT / f"{job_id}.zip").exists()

    replacement = module.reserve_job_slot()
    replacement.release()


def test_create_job_reports_unknown_cleanup_when_database_is_unavailable(
    isolated_jobs, monkeypatch: pytest.MonkeyPatch
):
    from types import SimpleNamespace

    module = isolated_jobs
    job_id = "queue-database-failure"
    monkeypatch.setattr(module.uuid, "uuid4", lambda: SimpleNamespace(hex=job_id))

    def fail_database():
        raise RuntimeError("synthetic database unavailable")

    monkeypatch.setattr(module, "_db", fail_database)
    with pytest.raises(module.JobCreationError, match="cleanup status is unknown") as exc_info:
        module.create_job(b"private upload bytes", "input.tif", "owner-db-failure", False, "auto")

    assert exc_info.value.job_id == job_id
    assert exc_info.value.stage == "database_insert"
    assert exc_info.value.cleanup_status == "unknown"
    assert not module._job_dir(job_id).exists()

    replacement = module.reserve_job_slot()
    replacement.release()
