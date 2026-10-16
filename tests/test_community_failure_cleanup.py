from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from zipfile import ZipFile
from types import SimpleNamespace

import pytest

from bionuclei.expert_agents import run_expert_agents


@pytest.fixture
def community(tmp_path, monkeypatch):
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


def test_incomplete_specialist_result_is_never_published(community, monkeypatch):
    module = community
    job_id = "failure-incomplete-specialist"
    user_id = "guest:test"
    root = module._job_dir(job_id)
    input_path = _seed_job(module, job_id, user_id, root)
    checkpoint = root / "checkpoint.pt"
    checkpoint.write_bytes(b"checkpoint")
    monkeypatch.setattr(module, "_checkpoint", lambda: checkpoint)
    monkeypatch.setattr(module, "build_plan", lambda *_args: SimpleNamespace(status="READY", warnings=[]))
    monkeypatch.setattr(module, "to_dict", lambda _plan: {
        "status": "PASS", "warnings": [],
        "profile": {"shape": [512, 512], "dtype": "uint16", "max": 65535},
        "cnn_pattern_check": {"executed": True, "status": "PASS"},
    })

    def successful_inference(_input, _checkpoint, output, device="cpu"):
        (output / "segmentation_mask.tif").write_bytes(b"mask")
        (output / "overlay.tif").write_bytes(b"overlay")
        return {"prediction": "synthetic"}

    monkeypatch.setattr(module, "predict", successful_inference)
    monkeypatch.setattr(module.gc, "collect", lambda: None)
    monkeypatch.setattr(module, "_extended_reports", lambda *_args: {
        "nuclei_count": 1,
        "morphology": {"mean_area": 10.0},
        "intensity": {"mean_nuclear_intensity": 1200.0},
        "spatial": {"instance_count": 1, "mean_nearest_neighbor_distance_px": None},
    })
    monkeypatch.setattr(module, "run_expert_agents", lambda _result: {
        "agent_version": "1.1",
        "execution": {"status": "incomplete", "incomplete_reasons": ["missing_or_invalid_job_id"]},
        "agents": [],
        "training_status": {"verified": False, "claim_allowed": False},
    })
    report_calls = []
    monkeypatch.setattr(module, "build_report", lambda *_args: report_calls.append(True))
    module._run(
        job_id, user_id, input_path, "input.tif", False, "auto",
        {"nuclei", "morphology", "intensity"},
        channel=0, time=0, z=0, field=0,
    )
    assert report_calls == []
    assert not root.exists()
    assert not (module.JOB_ROOT / f"{job_id}.zip").exists()
    _assert_failed_job_preserved_for_query(module, job_id, user_id)


def _complete_uint16_result() -> dict:
    return {
        "job_id": "test-job-uint16",
        "input_sha256": "a" * 64,
        "scientific_execution": True,
        "model": {"architecture": "Boundary U-Net", "training_reference": "Not established", "weights_updated_during_analysis": False},
        "analysis_modules": ["nuclei", "morphology", "intensity"],
        "adaptive_plan": {
            "status": "PASS", "warnings": [],
            "cnn_pattern_check": {"executed": True, "status": "PASS"},
            "profile": {
                "shape": [512, 512], "dtype": "uint16", "min": 1024, "p01": 1200,
                "median": 1400, "p995": 65535, "max": 65535, "mean": 1500.0,
                "std": 120.0, "saturation_fraction": 1 / 262144,
                "zero_fraction": 0.0, "finite": True,
            },
        },
        "reports": {
            "nuclei_count": 2,
            "morphology": {"mean_area": 12.0, "median_area": 11.5, "mean_circularity": 0.91},
            "intensity": {"mean_nuclear_intensity": 1250.0, "median_nuclear_intensity": 1240.0},
            "spatial": {
                "instance_count": 2, "unit": "pixels",
                "mean_nearest_neighbor_distance_px": 8.0,
                "median_nearest_neighbor_distance_px": 8.0,
                "min_nearest_neighbor_distance_px": 8.0,
                "max_nearest_neighbor_distance_px": 8.0,
            },
        },
    }


def test_complete_specialist_artifact_passes_server_publication_gate(community):
    result = _complete_uint16_result()
    artifact = run_expert_agents(result)
    community._validate_specialist_artifact(result, artifact)


def test_tampered_specialist_evidence_is_rejected_before_publication(community):
    result = _complete_uint16_result()
    artifact = run_expert_agents(result)
    artifact["agents"][0]["evidence_payload"] += " "
    with pytest.raises(ValueError, match="evidence digest mismatch"):
        community._validate_specialist_artifact(result, artifact)


def test_archive_excludes_original_tiff_and_nd2_plane(isolated_jobs):
    job_id = "archive-source-exclusion"
    root = isolated_jobs._job_dir(job_id)
    (root / "results").mkdir(parents=True)
    (root / "input.tif").write_bytes(b"source-tiff")
    (root / "input_plane.tif").write_bytes(b"source-plane")
    (root / "results" / "results.json").write_text('{"status":"synthetic"}', encoding="utf-8")
    archive = isolated_jobs._archive(job_id)
    with ZipFile(archive) as zf:
        names = set(zf.namelist())
    assert "input.tif" not in names
    assert "input_plane.tif" not in names
    assert "results/results.json" in names


def test_expired_completed_job_is_denied_before_periodic_cleanup(isolated_jobs):
    job_id = "expired-at-access"
    user_id = "user-expired"
    root = isolated_jobs._job_dir(job_id)
    (root / "results").mkdir(parents=True)
    (root / "results" / "results.json").write_text("{}", encoding="utf-8")
    expiry = (isolated_jobs._now() - timedelta(minutes=5)).isoformat()
    now = isolated_jobs._now().isoformat()
    with isolated_jobs.DB_LOCK, isolated_jobs._db() as conn:
        conn.execute(
            "INSERT INTO jobs(id,status,created_at,updated_at,expires_at,user_id,input_sha256,input_name,retained_copy,research_consent,algorithm_profile,analysis_modules) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (job_id,"completed",now,now,expiry,user_id,"a"*64,"x.tif",0,0,"auto","intensity,nuclei"),
        )
        conn.commit()
    assert isolated_jobs.get_job(job_id, user_id) is None
    with pytest.raises(FileNotFoundError):
        isolated_jobs.get_file(job_id, user_id, "results.json")
    with pytest.raises(FileNotFoundError):
        isolated_jobs.get_archive(job_id, user_id)
    assert isolated_jobs._get_job(job_id, user_id) is not None
    assert isolated_jobs.purge_expired() == 1
    assert isolated_jobs._get_job(job_id, user_id) is None


def test_unverified_training_reference_cannot_be_published_as_verified(community):
    result = _complete_uint16_result()
    result["model"]["training_reference"] = "BBBC039v1"
    artifact = run_expert_agents(result)
    with pytest.raises(ValueError, match="must be labeled Not established"):
        community._validate_specialist_artifact(result, artifact)
