from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def community(tmp_path, monkeypatch):
    # Import the production API composition first so its failure-cleanup
    # integration hook is installed before importing the worker module under test.
    import webapp.community_app  # noqa: F401
    import webapp.community as module

    monkeypatch.setattr(module, "JOB_ROOT", tmp_path / "jobs")
    monkeypatch.setattr(module, "DB_PATH", tmp_path / "jobs" / "jobs.sqlite3")
    module.JOB_ROOT.mkdir(parents=True, exist_ok=True)
    return module


def _seed_job(module, job_id: str, user_id: str, root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    input_path = root / "input.tif"
    input_path.write_bytes(b"synthetic-input")
    with module.DB_LOCK, module._db() as conn:
        now = module._now().isoformat()
        conn.execute(
            "INSERT INTO jobs(id,status,created_at,updated_at,expires_at,user_id,input_name,retained_copy,research_consent,algorithm_profile,analysis_modules) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (job_id, "queued", now, now, now, user_id, "input.tif", 0, 0, "auto", "nuclei,morphology,intensity"),
        )
        conn.commit()
    return input_path


def _assert_failed_job_preserved_for_query(module, job_id: str, user_id: str) -> None:
    row = module._get_job(job_id, user_id)
    assert row is not None
    assert row["status"] == "failed"
    assert row["error"] == "Analysis worker failed before producing a complete result. Please retry the analysis."


def test_inference_failure_removes_transient_artifacts_but_preserves_failed_status(community, monkeypatch):
    module = community
    job_id = "failure-inference"
    user_id = "guest:test"
    root = module._job_dir(job_id)
    input_path = _seed_job(module, job_id, user_id, root)
    (root / "results").mkdir()
    (root / "results" / "segmentation_mask.tif").write_bytes(b"derived")
    (module.JOB_ROOT / f"{job_id}.zip").write_bytes(b"archive")

    checkpoint = root / "checkpoint.pt"
    checkpoint.write_bytes(b"checkpoint")
    monkeypatch.setattr(module, "_checkpoint", lambda: checkpoint)
    monkeypatch.setattr(module, "build_plan", lambda *_args: SimpleNamespace(status="READY", warnings=[]))
    monkeypatch.setattr(module, "to_dict", lambda _plan: {})

    def fail_inference(_input, _checkpoint, output, device="cpu"):
        (output / "overlay.tif").write_bytes(b"overlay")
        (output / "results.json").write_text("{}", encoding="utf-8")
        raise RuntimeError("synthetic inference failure")

    monkeypatch.setattr(module, "predict", fail_inference)
    monkeypatch.setattr(module.gc, "collect", lambda: None)

    module._run(
        job_id,
        user_id,
        input_path,
        "input.tif",
        False,
        "auto",
        {"nuclei", "morphology", "intensity"},
        channel=0,
        time=0,
        z=0,
        field=0,
    )

    assert not root.exists()
    assert not (module.JOB_ROOT / f"{job_id}.zip").exists()
    _assert_failed_job_preserved_for_query(module, job_id, user_id)


def test_report_failure_removes_transient_results_but_preserves_failed_status(community, monkeypatch):
    module = community
    job_id = "failure-report"
    user_id = "guest:test"
    root = module._job_dir(job_id)
    input_path = _seed_job(module, job_id, user_id, root)

    checkpoint = root / "checkpoint.pt"
    checkpoint.write_bytes(b"checkpoint")
    monkeypatch.setattr(module, "_checkpoint", lambda: checkpoint)
    monkeypatch.setattr(module, "build_plan", lambda *_args: SimpleNamespace(status="READY", warnings=[]))
    monkeypatch.setattr(module, "to_dict", lambda _plan: {})

    def successful_inference(_input, _checkpoint, output, device="cpu"):
        (output / "segmentation_mask.tif").write_bytes(b"mask")
        (output / "overlay.tif").write_bytes(b"overlay")
        return {"prediction": "synthetic"}

    monkeypatch.setattr(module, "predict", successful_inference)
    monkeypatch.setattr(module.gc, "collect", lambda: None)
    monkeypatch.setattr(module, "_extended_reports", lambda *_args: {"nuclei_count": 1})
    monkeypatch.setattr(module, "run_expert_agents", lambda result: {"status": "ok"})
    monkeypatch.setattr(module, "_archive", lambda job: (module.JOB_ROOT / f"{job}.zip").write_bytes(b"archive") or module.JOB_ROOT / f"{job}.zip")

    def fail_report(_result, _output):
        raise RuntimeError("synthetic report failure")

    monkeypatch.setattr(module, "build_report", fail_report)

    module._run(
        job_id,
        user_id,
        input_path,
        "input.tif",
        False,
        "auto",
        {"nuclei", "morphology", "intensity"},
        channel=0,
        time=0,
        z=0,
        field=0,
    )

    assert not root.exists()
    assert not (module.JOB_ROOT / f"{job_id}.zip").exists()
    _assert_failed_job_preserved_for_query(module, job_id, user_id)
