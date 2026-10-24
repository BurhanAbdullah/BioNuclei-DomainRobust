from __future__ import annotations

import threading
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from webapp import community, community_app


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


def test_delete_active_job_returns_conflict_without_removing_transient_data(
    isolated_jobs, monkeypatch: pytest.MonkeyPatch
):
    module = isolated_jobs
    job_id = "delete-active-job"
    user_id = "owner-active"
    now = module._now()
    root = module._job_dir(job_id)
    root.mkdir(parents=True)
    source = root / "input.tif"
    source.write_bytes(b"private source bytes")
    archive = module.JOB_ROOT / f"{job_id}.zip"
    archive.write_bytes(b"existing archive")
    with module.DB_LOCK, module._db() as conn:
        conn.execute(
            "INSERT INTO jobs(id,status,created_at,updated_at,expires_at,user_id,input_name,retained_copy,research_consent,algorithm_profile,analysis_modules) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                job_id, "running", now.isoformat(), now.isoformat(),
                (now + timedelta(hours=1)).isoformat(), user_id, "input.tif",
                0, 0, "auto", "intensity,nuclei",
            ),
        )
        conn.commit()

    with module.ACTIVE_JOB_THREADS_LOCK:
        module.ACTIVE_JOB_THREADS[job_id] = SimpleNamespace(is_alive=lambda: True)
    monkeypatch.setattr(
        community_app,
        "authenticate_optional",
        lambda _request: SimpleNamespace(id=user_id, email=None, guest=True),
    )
    try:
        with TestClient(community_app.app) as client:
            response = client.delete(f"/jobs/{job_id}")
        assert response.status_code == 409
        assert "deletion was not performed" in response.json()["detail"]
        row = module._get_job(job_id, user_id)
        assert row is not None and row["status"] == "running"
        assert source.read_bytes() == b"private source bytes"
        assert archive.read_bytes() == b"existing archive"
    finally:
        with module.ACTIVE_JOB_THREADS_LOCK:
            module.ACTIVE_JOB_THREADS.pop(job_id, None)


def test_delete_cannot_race_worker_start(isolated_jobs, monkeypatch: pytest.MonkeyPatch):
    module = isolated_jobs
    real_thread = threading.Thread
    start_entered = threading.Event()
    allow_start = threading.Event()
    delete_lookup_done = threading.Event()
    delete_done = threading.Event()
    outcome: dict[str, object] = {}

    class PausedWorker:
        def __init__(self, *args, **kwargs):
            self.started = False

        def start(self):
            start_entered.set()
            if not allow_start.wait(timeout=5):
                raise RuntimeError("test worker start was not released")
            self.started = True

        def is_alive(self):
            return self.started

    monkeypatch.setattr(module.threading, "Thread", PausedWorker)
    creator = real_thread(
        target=lambda: outcome.update(
            job_id=module.create_job(b"fixture", "race.tif", "owner-race", False, "auto")
        )
    )
    creator.start()
    assert start_entered.wait(timeout=5)

    with module.DB_LOCK, module._db() as conn:
        row = conn.execute("SELECT id FROM jobs WHERE user_id = ?", ("owner-race",)).fetchone()
    assert row is not None
    job_id = str(row["id"])

    original_get_job = module._get_job

    def observe_lookup(lookup_id, user_id=None):
        result = original_get_job(lookup_id, user_id)
        if lookup_id == job_id:
            delete_lookup_done.set()
        return result

    monkeypatch.setattr(module, "_get_job", observe_lookup)

    def delete_attempt():
        try:
            module.delete_job(job_id, "owner-race")
        except Exception as exc:
            outcome["delete_error"] = exc
        else:
            outcome["deleted"] = True
        finally:
            delete_done.set()

    deleter = real_thread(target=delete_attempt)
    deleter.start()
    assert delete_lookup_done.wait(timeout=5)
    # The creator holds the registry lock until Thread.start() has returned;
    # deletion must not pass the active-worker check during this window.
    assert not delete_done.wait(timeout=0.1)

    allow_start.set()
    creator.join(timeout=5)
    deleter.join(timeout=5)
    assert not creator.is_alive()
    assert not deleter.is_alive()
    assert outcome.get("job_id") == job_id
    assert isinstance(outcome.get("delete_error"), module.ActiveJobDeletionError)

    # Remove the synthetic worker and prove the owner can then delete the job.
    with module.ACTIVE_JOB_THREADS_LOCK:
        worker = module.ACTIVE_JOB_THREADS.pop(job_id)
        worker.started = False
    assert module.delete_job(job_id, "owner-race") is True


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

def test_recovery_uses_registry_before_database_lock(isolated_jobs, monkeypatch: pytest.MonkeyPatch):
    module = isolated_jobs
    job_id = "stale-recovery-lock-order"
    user_id = "owner-recovery"
    now = module._now()
    stale = (now - timedelta(hours=1)).isoformat()
    with module.DB_LOCK, module._db() as conn:
        conn.execute(
            "INSERT INTO jobs(id,status,created_at,updated_at,expires_at,user_id,input_name,"
            "retained_copy,research_consent,algorithm_profile,analysis_modules) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                job_id, "queued", stale, stale, (now + timedelta(hours=1)).isoformat(),
                user_id, "stale.tif", 0, 0, "auto", "nuclei",
            ),
        )
        conn.commit()

    class LockOrderGuard:
        state = threading.local()

        def __init__(self, name: str):
            self.name = name
            self.lock = threading.Lock()

        def __enter__(self):
            held = list(getattr(self.state, "held", []))
            if self.name == "active" and "db" in held:
                raise AssertionError("lock inversion: registry lock acquired while DB lock held")
            self.lock.acquire()
            held.append(self.name)
            self.state.held = held
            return self

        def __exit__(self, *_):
            held = list(getattr(self.state, "held", []))
            assert held and held[-1] == self.name
            held.pop()
            self.state.held = held
            self.lock.release()

    monkeypatch.setattr(module, "DB_LOCK", LockOrderGuard("db"))
    monkeypatch.setattr(module, "ACTIVE_JOB_THREADS_LOCK", LockOrderGuard("active"))
    monkeypatch.setattr(module, "_cleanup_failed_job", lambda *_args, **_kwargs: None)

    assert module.recover_interrupted_jobs(
        now=now, stale_after=timedelta(minutes=1)
    ) == 1
    row = module._get_job(job_id, user_id)
    assert row is not None and row["status"] == "failed"

