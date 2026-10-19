from __future__ import annotations

from datetime import timedelta
import hashlib
import io
import json
import shutil
import subprocess
import time
from pathlib import Path
from zipfile import ZipFile
from types import SimpleNamespace

import numpy as np
import pytest
import tifffile
import pandas as pd
from fastapi.testclient import TestClient

from bionuclei.adaptive_agent import CNNPatternCheck

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
        "analysis_modules": ["intensity", "morphology", "nuclei"],
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
            "intensity": {"mean_nuclear_intensity": 1250.0, "median_nuclear_intensity": 1240.0, "mean_max_intensity": 30000.0, "max_nuclear_intensity": 65535},
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


def test_archive_excludes_original_tiff_and_nd2_plane(community):
    job_id = "archive-source-exclusion"
    root = community._job_dir(job_id)
    (root / "results").mkdir(parents=True)
    (root / "input.tif").write_bytes(b"source-tiff")
    (root / "input_plane.tif").write_bytes(b"source-plane")
    (root / "results" / "results.json").write_text('{"status":"synthetic"}', encoding="utf-8")
    archive = community._archive(job_id)
    with ZipFile(archive) as zf:
        names = set(zf.namelist())
    assert "input.tif" not in names
    assert "input_plane.tif" not in names
    assert "results/results.json" in names


def test_expired_active_job_is_preserved_by_result_purge(community):
    job_id = "expired-running-job"
    user_id = "user-running"
    root = community._job_dir(job_id)
    root.mkdir(parents=True)
    marker = root / "worker-state.txt"
    marker.write_text("active", encoding="utf-8")
    expiry = (community._now() - timedelta(minutes=5)).isoformat()
    now = community._now().isoformat()
    with community.DB_LOCK, community._db() as conn:
        conn.execute(
            "INSERT INTO jobs(id,status,created_at,updated_at,expires_at,user_id,input_sha256,input_name,retained_copy,research_consent,algorithm_profile,analysis_modules) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (job_id,"running",now,now,expiry,user_id,"b"*64,"x.tif",0,0,"auto","intensity,nuclei"),
        )
        conn.commit()

    assert community.purge_expired() == 0
    assert community._get_job(job_id, user_id) is not None
    assert marker.read_text(encoding="utf-8") == "active"

def test_expired_completed_job_is_denied_before_periodic_cleanup(community):
    job_id = "expired-at-access"
    user_id = "user-expired"
    root = community._job_dir(job_id)
    (root / "results").mkdir(parents=True)
    (root / "results" / "results.json").write_text("{}", encoding="utf-8")
    expiry = (community._now() - timedelta(minutes=5)).isoformat()
    now = community._now().isoformat()
    with community.DB_LOCK, community._db() as conn:
        conn.execute(
            "INSERT INTO jobs(id,status,created_at,updated_at,expires_at,user_id,input_sha256,input_name,retained_copy,research_consent,algorithm_profile,analysis_modules) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (job_id,"completed",now,now,expiry,user_id,"a"*64,"x.tif",0,0,"auto","intensity,nuclei"),
        )
        conn.commit()
    assert community.get_job(job_id, user_id) is None
    with pytest.raises(FileNotFoundError):
        community.get_file(job_id, user_id, "results.json")
    with pytest.raises(FileNotFoundError):
        community.get_archive(job_id, user_id)
    assert community._get_job(job_id, user_id) is not None
    assert community.purge_expired() == 1
    assert community._get_job(job_id, user_id) is None


def test_unverified_training_reference_cannot_be_published_as_verified(community):
    result = _complete_uint16_result()
    result["model"]["training_reference"] = "BBBC039v1"
    artifact = run_expert_agents(result)
    with pytest.raises(ValueError, match="must be labeled Not established"):
        community._validate_specialist_artifact(result, artifact)


def test_uint16_service_path_executes_specialists_from_computed_measurements(community, monkeypatch):
    """Exercise job/report/agent wiring with real TIFF/QC/measurement code and deterministic test inference."""
    module = community
    job_id = "e2e-512-uint16-specialists"
    user_id = "guest:e2e"
    root = module._job_dir(job_id)
    input_path = _seed_job(module, job_id, user_id, root)

    image = np.full((512, 512), 512, dtype=np.uint16)
    yy, xx = np.ogrid[:512, :512]
    circles = [(100, 100, 18, 4096), (100, 180, 16, 8192), (220, 280, 20, 16384), (360, 160, 17, 32768)]
    mask = np.zeros((512, 512), dtype=np.int32)
    for label, (cy, cx, radius, intensity) in enumerate(circles, start=1):
        disk = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius ** 2
        image[disk] = intensity
        mask[disk] = label
    image[100, 100] = np.uint16(65535)  # inside the first known segmented nucleus
    tifffile.imwrite(input_path, image)

    checkpoint = root / "checkpoint.pt"
    checkpoint.write_bytes(b"test-only checkpoint placeholder")
    monkeypatch.setattr(module, "_checkpoint", lambda: checkpoint)
    monkeypatch.setattr(
        "bionuclei.adaptive_agent.cnn_pattern_check",
        lambda _path: CNNPatternCheck(True, "Boundary U Net", 0.04, 0.95, 0.1, 4, "PASS", ()),
    )
    monkeypatch.setattr(module.gc, "collect", lambda: None)

    def deterministic_test_inference(inference_input, _checkpoint, output, device="cpu"):
        measured_image = tifffile.imread(inference_input)
        assert measured_image.dtype == np.uint16
        assert int(measured_image.max()) == 65535
        tifffile.imwrite(output / "segmentation_mask.tif", mask)
        overlay = np.repeat((measured_image.astype(np.float64) / 65535 * 255).astype(np.uint8)[..., None], 3, axis=2)
        tifffile.imwrite(output / "overlay.tif", overlay)
        return {"n_instances": int(mask.max()), "image_shape": list(measured_image.shape)}

    monkeypatch.setattr(module, "predict", deterministic_test_inference)
    module._run(
        job_id, user_id, input_path, "e2e-512-uint16.tif", False, "auto",
        {"nuclei", "morphology", "intensity"}, channel=0, time=0, z=0, field=0,
    )

    row = module._get_job(job_id, user_id)
    assert row is not None and row["status"] == "completed"
    assert row["retained_copy"] == 0 and row["research_consent"] == 0
    assert not input_path.exists()

    result_path = root / "results" / "results.json"
    artifact_path = root / "results" / "expert_agents.json"
    assert result_path.is_file() and artifact_path.is_file()
    result = __import__("json").loads(result_path.read_text(encoding="utf-8"))
    artifact = __import__("json").loads(artifact_path.read_text(encoding="utf-8"))
    assert result["job_id"] == job_id
    assert result["analysis_modules"] == ["intensity", "morphology", "nuclei"]

    profile = result["adaptive_plan"]["profile"]
    assert profile["shape"] == [512, 512] and profile["dtype"] == "uint16" and profile["max"] == 65535
    assert result["scientific_execution"] is True
    assert result["model"]["weights_updated_during_analysis"] is False
    assert result["model"]["training_reference"] == "Not established"
    assert result["reports"]["nuclei_count"] == 4
    mean_intensity = result["reports"]["intensity"]["mean_nuclear_intensity"]
    assert mean_intensity > 255
    measurement_rows = pd.read_csv(root / "results" / "nuclei_analysis.csv")
    assert int(measurement_rows.loc[measurement_rows["label"] == 1, "max_intensity"].iloc[0]) == 65535
    assert result["reports"]["intensity"]["max_nuclear_intensity"] == 65535

    execution = artifact["execution"]
    assert execution["status"] == "completed" and execution["job_id"] == job_id
    assert execution["input_sha256"] == result["input_sha256"]
    assert execution["agent_count"] == 8 and execution["completed_agent_count"] == 8
    assert execution["incomplete_agents"] == []
    assert artifact["training_status"]["verified"] is False
    assert artifact["training_status"]["claim_allowed"] is False

    intensity_agent = next(agent for agent in artifact["agents"] if agent["agent"] == "intensity_agent")
    assert intensity_agent["status"] == "completed"
    assert "Raw image max: 65535" in intensity_agent["observations"]
    assert any(claim["reference"] == "adaptive_plan.profile.max" and claim["value"] == 65535 for claim in intensity_agent["quantitative_claims"])
    assert any(claim["reference"] == "reports.intensity.mean_nuclear_intensity" and claim["value"] == mean_intensity for claim in intensity_agent["quantitative_claims"])

    with ZipFile(module._archive(job_id)) as archive:
        names = set(archive.namelist())
        for required in ("results/analysis_report.html", "results/analysis_report.pdf", "results/expert_agents.json", "results/nuclei_analysis.csv", "results/segmentation_mask.tif", "results/overlay.tif"):
            assert required in names
        assert not any(name.endswith("input.tif") or name.endswith("input_plane.tif") or "e2e-512-uint16.tif" in name for name in names)


def test_public_upload_route_returns_job_bound_verified_specialist_result(community, monkeypatch):
    """Exercise the real FastAPI upload/job/result/download path with deterministic inference."""
    import webapp.community_app as community_app

    module = community
    checkpoint = module.JOB_ROOT / "test-only-checkpoint.pt"
    checkpoint.write_bytes(b"test-only checkpoint placeholder")
    monkeypatch.setattr(module, "_checkpoint", lambda: checkpoint)
    monkeypatch.setattr(
        "bionuclei.adaptive_agent.cnn_pattern_check",
        lambda _path: CNNPatternCheck(True, "Boundary U-Net", 0.04, 0.95, 0.1, 4, "PASS", ()),
    )
    monkeypatch.setattr(module.gc, "collect", lambda: None)

    image = np.full((512, 512), 512, dtype=np.uint16)
    yy, xx = np.ogrid[:512, :512]
    circles = [
        (100, 100, 18, 4096),
        (100, 180, 16, 8192),
        (220, 280, 20, 16384),
        (360, 160, 17, 32768),
    ]
    mask = np.zeros((512, 512), dtype=np.int32)
    for label, (cy, cx, radius, intensity) in enumerate(circles, start=1):
        disk = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius ** 2
        image[disk] = intensity
        mask[disk] = label
    image[100, 100] = np.uint16(65535)  # inside the first segmented nucleus
    upload = io.BytesIO()
    tifffile.imwrite(upload, image)
    upload_bytes = upload.getvalue()

    def deterministic_test_inference(inference_input, _checkpoint, output, device="cpu"):
        measured_image = tifffile.imread(inference_input)
        assert measured_image.dtype == np.uint16
        assert int(measured_image.max()) == 65535
        tifffile.imwrite(output / "segmentation_mask.tif", mask)
        overlay = np.repeat(
            (measured_image.astype(np.float64) / 65535 * 255).astype(np.uint8)[..., None],
            3,
            axis=2,
        )
        tifffile.imwrite(output / "overlay.tif", overlay)
        return {"n_instances": int(mask.max()), "image_shape": list(measured_image.shape)}

    monkeypatch.setattr(module, "predict", deterministic_test_inference)

    # Use the same public guest-session and multipart-upload routes as the browser.
    with TestClient(community_app.app) as client:
        guest_response = client.post("/guest-session")
        assert guest_response.status_code == 200, guest_response.text
        guest_token = guest_response.json()["guest_token"]
        headers = {"X-BioNuclei-Guest-Token": guest_token}

        accepted = client.post(
            "/analyze",
            headers=headers,
            files={"image": ("e2e-512-uint16.tif", upload_bytes, "image/tiff")},
            data={
                "research_consent": "false",
                "algorithm_profile": "auto",
                "analysis_modules": "nuclei,morphology,intensity",
            },
        )
        assert accepted.status_code == 200, accepted.text
        queued = accepted.json()
        job_id = queued["job_id"]
        assert queued["status"] == "queued"
        assert queued["research_consent"] is False

        deadline = time.monotonic() + 20.0
        payload = None
        while time.monotonic() < deadline:
            response = client.get(f"/jobs/{job_id}", headers=headers)
            assert response.status_code == 200, response.text
            payload = response.json()
            if payload.get("status") in {"completed", "failed"}:
                break
            time.sleep(0.02)

        assert payload is not None
        assert payload.get("status") == "completed", payload
        result = payload["result"]
        assert result["job_id"] == job_id
        assert result["input_sha256"] == hashlib.sha256(upload_bytes).hexdigest()
        assert result["analysis_modules"] == ["intensity", "morphology", "nuclei"]
        assert result["adaptive_plan"]["profile"]["dtype"] == "uint16"
        assert result["adaptive_plan"]["profile"]["max"] == 65535
        assert result["model"]["weights_updated_during_analysis"] is False
        assert result["model"]["training_reference"] == "Not established"
        assert result["reports"]["intensity"]["max_nuclear_intensity"] == 65535

        specialist_response = client.get(
            f"/jobs/{job_id}/files/expert_agents.json", headers=headers
        )
        assert specialist_response.status_code == 200, specialist_response.text
        artifact = specialist_response.json()
        execution = artifact["execution"]
        assert execution["status"] == "completed"
        assert execution["job_id"] == job_id
        assert execution["input_sha256"] == result["input_sha256"]
        assert execution["analysis_modules"] == result["analysis_modules"]
        assert artifact["training_status"]["verified"] is False
        assert artifact["training_status"]["claim_allowed"] is False

        # Execute the real browser verifier (CommonJS export) against the HTTP-returned
        # result and specialist artifact, rather than relying on source grep alone.
        node = shutil.which("node")
        if node is None:
            pytest.skip("Node.js is needed to execute the browser specialist verifier")
        verification_input = module.JOB_ROOT / "browser-verification-input.json"
        verification_input.write_text(
            json.dumps(
                {"job": payload, "result": result, "artifact": artifact},
                allow_nan=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        verifier_path = (
            Path(__file__).resolve().parents[1]
            / "docs"
            / "assets"
            / "bionuclei-specialist-verification.js"
        )
        verifier_script = r"""
const fs = require("node:fs");
const { webcrypto } = require("node:crypto");
const verifier = require(process.argv[1]);
const input = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
(async () => {
  const expectedPath = "/jobs/" + encodeURIComponent(input.job.job_id) + "/files/expert_agents.json";
  const outcome = await verifier.verifySpecialistArtifact({
    job: input.job,
    result: input.result,
    embedded: input.result.expert_agents,
    fetchJson: async path => {
      if (path !== expectedPath) throw new Error("unexpected artifact fetch path: " + path);
      return input.artifact;
    },
    cryptoApi: webcrypto
  });
  if (!outcome || outcome.ok !== true) throw new Error(outcome && outcome.reason || "verification failed");
  process.stdout.write("browser-verifier-ok\\n");
})().catch(error => {
  console.error(error && error.stack || error);
  process.exit(1);
});
"""
        browser_verification = subprocess.run(
            [node, "-e", verifier_script, str(verifier_path), str(verification_input)],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        assert browser_verification.returncode == 0, (
            browser_verification.stdout + browser_verification.stderr
        )
        assert "browser-verifier-ok" in browser_verification.stdout

        intensity_agent = next(
            agent for agent in artifact["agents"] if agent["agent"] == "intensity_agent"
        )
        assert any(
            claim["reference"] == "reports.intensity.max_nuclear_intensity"
            and claim["value"] == 65535
            for claim in intensity_agent["quantitative_claims"]
        )

        for filename in (
            "results.json",
            "nuclei_analysis.csv",
            "analysis_report.html",
            "analysis_report.pdf",
            "segmentation_mask.tif",
            "overlay.tif",
        ):
            artifact_response = client.get(
                f"/jobs/{job_id}/files/{filename}", headers=headers
            )
            assert artifact_response.status_code == 200, (
                filename,
                artifact_response.status_code,
                artifact_response.text[:300],
            )

        download = client.get(f"/jobs/{job_id}/download", headers=headers)
        assert download.status_code == 200, download.text[:300]
        with ZipFile(io.BytesIO(download.content)) as archive:
            names = set(archive.namelist())
            assert "results/expert_agents.json" in names
            assert "results/nuclei_analysis.csv" in names
            assert "results/analysis_report.html" in names
            assert "results/analysis_report.pdf" in names
            assert not any(
                name.endswith("input.tif")
                or name.endswith("input_plane.tif")
                or "e2e-512-uint16.tif" in name
                for name in names
            )
