from __future__ import annotations

from datetime import timedelta
import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
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


def test_create_job_streams_file_like_upload_in_bounded_chunks(isolated_jobs, monkeypatch):
    payload = bytes(range(256)) * 16384

    class ChunkReader:
        def __init__(self, value: bytes) -> None:
            self.value = value
            self.offset = 0
            self.requested_sizes: list[int] = []

        def read(self, size: int = -1) -> bytes:
            assert size > 0, "upload copying must never request an unbounded read"
            self.requested_sizes.append(size)
            end = min(self.offset + min(size, 4096), len(self.value))
            chunk = self.value[self.offset:end]
            self.offset = end
            return chunk

    class InertThread:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def start(self) -> None:
            pass

    monkeypatch.setattr(isolated_jobs.threading, "Thread", InertThread)
    source = ChunkReader(payload)
    job_id = isolated_jobs.create_job(
        source, "streamed.tif", "user-1", False, "auto"
    )
    try:
        input_path = isolated_jobs._job_dir(job_id) / "input.tif"
        assert input_path.read_bytes() == payload
        assert source.requested_sizes
        assert set(source.requested_sizes) == {isolated_jobs.UPLOAD_COPY_CHUNK_BYTES}
        row = isolated_jobs.get_job(job_id, "user-1")
        assert row is not None and row["status"] == "queued"
    finally:
        isolated_jobs.ACTIVE_JOB_THREADS.pop(job_id, None)


def test_create_job_rejects_oversized_stream_and_removes_partial_job(
    isolated_jobs, monkeypatch
) -> None:
    monkeypatch.setattr(isolated_jobs, "MAX_UPLOAD_BYTES", 8)

    class OversizedStream:
        def __init__(self) -> None:
            self.sent = False

        def read(self, _size: int) -> bytes:
            if self.sent:
                return b""
            self.sent = True
            return b"123456789"

    with pytest.raises(ValueError, match="Upload exceeds 8 bytes"):
        isolated_jobs.create_job(
            OversizedStream(), "oversized.tif", "user-1", False, "auto"
        )

    assert not [path for path in isolated_jobs.JOB_ROOT.iterdir() if path.is_dir()]


def test_create_job_rejects_empty_stream_and_removes_partial_job(isolated_jobs) -> None:
    class EmptyStream:
        def read(self, _size: int) -> bytes:
            return b""

    with pytest.raises(ValueError, match="Uploaded image is empty"):
        isolated_jobs.create_job(
            EmptyStream(), "empty.tif", "user-1", False, "auto"
        )

    assert not [path for path in isolated_jobs.JOB_ROOT.iterdir() if path.is_dir()]


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


def test_sha256_file_streams_large_inputs_without_read_bytes(
    isolated_jobs, monkeypatch, tmp_path: Path
) -> None:
    payload = bytes(range(256)) * 16384
    path = tmp_path / "large-input.tif"
    path.write_bytes(payload)

    def reject_read_bytes(_path):
        raise AssertionError("streaming hash must not materialize the entire source file")

    monkeypatch.setattr(Path, "read_bytes", reject_read_bytes)

    assert isolated_jobs._sha256_file(path, chunk_size=4096) == (
        hashlib.sha256(payload).hexdigest()
    )


def test_sha256_file_rejects_non_positive_chunk_size(isolated_jobs, tmp_path: Path) -> None:
    path = tmp_path / "input.tif"
    path.write_bytes(b"source")

    with pytest.raises(ValueError, match="chunk_size must be positive"):
        isolated_jobs._sha256_file(path, chunk_size=0)

def test_nd2_to_tiff_reads_only_the_selected_frame(monkeypatch, tmp_path: Path) -> None:
    class FakeND2File:
        sizes = {"T": 2, "Z": 2, "C": 2, "Y": 3, "X": 4}
        shape = (2, 2, 2, 3, 4)
        is_legacy = False
        loop_indices = tuple(
            {"T": time, "Z": z, "C": channel}
            for time in range(2)
            for z in range(2)
            for channel in range(2)
        )

        def __init__(self) -> None:
            self.read_calls: list[int] = []
            self.frames = [
                np.full((3, 4), index, dtype=np.uint16)
                for index in range(len(self.loop_indices))
            ]

        def __enter__(self):
            return self

        def __exit__(self, *_exc) -> None:
            return None

        def asarray(self):
            raise AssertionError("ND2 conversion must not materialize the full stack")

        def read_frame(self, frame_index: int) -> np.ndarray:
            self.read_calls.append(frame_index)
            return self.frames[frame_index]

    reader = FakeND2File()
    monkeypatch.setitem(
        sys.modules,
        "nd2",
        SimpleNamespace(ND2File=lambda _source: reader, __version__="0.11.0"),
    )
    destination = tmp_path / "selected-plane.tif"

    metadata = community._nd2_to_tiff(
        tmp_path / "source.nd2",
        destination,
        channel=1,
        time=1,
        z=0,
    )

    assert reader.read_calls == [5]
    assert np.array_equal(community.tifffile.imread(destination), reader.frames[5])
    assert metadata["selected_indices"] == {"T": 1, "Z": 0, "C": 1}
    assert metadata["selected_frame_index"] == 5


def test_legacy_nd2_to_tiff_reads_one_frame_and_selects_channel(
    monkeypatch, tmp_path: Path
) -> None:
    class FakeLegacyND2File:
        sizes = {"T": 2, "C": 2, "Y": 3, "X": 4}
        shape = (2, 2, 3, 4)
        is_legacy = True
        loop_indices = ({"T": 0}, {"T": 1})

        def __init__(self) -> None:
            self.read_calls: list[int] = []
            self.frames = [
                np.stack(
                    (
                        np.full((3, 4), 10 + time, dtype=np.uint16),
                        np.full((3, 4), 20 + time, dtype=np.uint16),
                    ),
                    axis=0,
                )
                for time in range(2)
            ]

        def __enter__(self):
            return self

        def __exit__(self, *_exc) -> None:
            return None

        def asarray(self):
            raise AssertionError("legacy ND2 conversion must not materialize the full stack")

        def read_frame(self, frame_index: int) -> np.ndarray:
            self.read_calls.append(frame_index)
            return self.frames[frame_index]

    reader = FakeLegacyND2File()
    monkeypatch.setitem(
        sys.modules,
        "nd2",
        SimpleNamespace(ND2File=lambda _source: reader, __version__="0.11.0"),
    )
    destination = tmp_path / "legacy-selected-plane.tif"

    metadata = community._nd2_to_tiff(
        tmp_path / "legacy-source.nd2",
        destination,
        channel=1,
        time=1,
    )

    assert reader.read_calls == [1]
    assert np.array_equal(
        community.tifffile.imread(destination), reader.frames[1][1]
    )
    assert metadata["selected_indices"] == {"T": 1, "C": 1}
    assert metadata["selected_frame_index"] == 1
    assert metadata["legacy_reader"] is True


def test_create_job_enforces_memoryview_nbytes_upload_limit(isolated_jobs, monkeypatch, tmp_path: Path) -> None:
    from array import array

    monkeypatch.setattr(isolated_jobs, "MAX_UPLOAD_BYTES", 8)
    payload = memoryview(array("Q", [1, 2]))
    assert len(payload) == 2
    assert payload.nbytes == 16

    class MemoryviewReader:
        def __init__(self) -> None:
            self.sent = False

        def read(self, _size: int):
            if self.sent:
                return b""
            self.sent = True
            return payload

    destination = tmp_path / "oversized-memoryview.tif"
    with pytest.raises(ValueError, match="Upload exceeds 8 bytes"):
        isolated_jobs._write_upload(MemoryviewReader(), destination)

    assert not destination.exists()
