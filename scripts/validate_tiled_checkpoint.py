#!/usr/bin/env python3
"""Run the released checkpoint through the real worker and evidence-bound specialists.

This is a CI integration gate for tiled inference, not a mocked model test. It
uses a deterministic uint16 fixture and the immutable, digest-pinned release
checkpoint. It does not train, fine-tune, or write to model weights.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import zipfile
from pathlib import Path

import numpy as np
import tifffile


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_fixture(path: Path) -> str:
    image = np.full((512, 512), 512, dtype=np.uint16)
    yy, xx = np.ogrid[:512, :512]
    for cy, cx, radius, intensity in [
        (100, 100, 18, 4096),
        (100, 180, 16, 8192),
        (220, 280, 20, 16384),
        (360, 160, 17, 32768),
    ]:
        image[(yy - cy) ** 2 + (xx - cx) ** 2 <= radius ** 2] = np.uint16(intensity)
    image[97:104, 97:104] = np.uint16(65535)
    tifffile.imwrite(path, image)
    reread = tifffile.imread(path)
    assert reread.shape == (512, 512)
    assert reread.dtype == np.uint16
    assert int(reread.min()) == 512
    assert int(reread.max()) == 65535
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    checkpoint_raw = os.environ.get("BIONUCLEI_CHECKPOINT", "")
    expected_checkpoint_sha = os.environ.get("BIONUCLEI_EXPECTED_CHECKPOINT_SHA256", "")
    require(bool(checkpoint_raw), "BIONUCLEI_CHECKPOINT is not configured")
    require(bool(expected_checkpoint_sha), "Pinned checkpoint SHA-256 is not configured")
    checkpoint = Path(checkpoint_raw).resolve()
    require(checkpoint.is_file(), f"Checkpoint file is missing: {checkpoint}")
    before_sha = sha256_file(checkpoint)
    require(before_sha == expected_checkpoint_sha,
            f"Checkpoint digest mismatch: expected={expected_checkpoint_sha}, actual={before_sha}")

    # Set isolated job storage before importing the production worker module.
    with tempfile.TemporaryDirectory(prefix="bionuclei-checkpoint-e2e-") as temp:
        root = Path(temp)
        job_root = root / "jobs"
        os.environ["BIONUCLEI_JOB_DIR"] = str(job_root)
        os.environ["BIONUCLEI_RESULT_RETENTION_HOURS"] = "1"
        fixture = root / "live-uint16-sentinel.tif"
        fixture_sha = build_fixture(fixture)

        import webapp.community as community

        owner = "checkpoint-validation-owner"
        payload = fixture.read_bytes()
        job_id = ""
        archive_path: Path | None = None
        timeline: list[dict[str, object]] = []
        try:
            job_id = community.create_job(
                payload,
                fixture.name,
                owner,
                False,
                "auto",
                ["nuclei", "morphology", "intensity"],
            )
            deadline = time.monotonic() + 900
            last_status = None
            job = None
            while time.monotonic() < deadline:
                job = community.get_job(job_id, owner)
                require(job is not None, "Created job disappeared before completion")
                status = str(job.get("status") or "unknown")
                if status != last_status:
                    timeline.append({"status": status, "updated_at": job.get("updated_at")})
                    last_status = status
                if status == "completed":
                    break
                if status == "failed":
                    raise AssertionError(
                        f"Real checkpoint worker failed: {job.get('error')!r}; timeline={timeline!r}"
                    )
                time.sleep(1)
            else:
                raise TimeoutError(f"Real checkpoint worker timed out; timeline={timeline!r}")

            result_path = community.get_file(job_id, owner, "results.json")
            result = json.loads(result_path.read_text(encoding="utf-8"))
            require(result.get("scientific_execution") is True,
                    "Result is not marked as scientific execution")
            require(result.get("input_sha256") == fixture_sha,
                    "Scientific result is not bound to the exact uploaded fixture bytes")
            profile = result.get("adaptive_plan", {}).get("profile", {})
            require(profile.get("shape") == [512, 512], f"Unexpected image shape: {profile.get('shape')!r}")
            require(profile.get("dtype") == "uint16", f"Input dtype was lost: {profile.get('dtype')!r}")
            require(profile.get("max") == 65535, f"Full uint16 maximum was lost: {profile.get('max')!r}")
            intensity = result.get("reports", {}).get("intensity", {})
            require(intensity.get("max_nuclear_intensity") == 65535,
                    "Real checkpoint segmentation did not preserve the saturated core in nuclear intensity measurements")
            require(float(intensity.get("mean_nuclear_intensity") or 0) > 255,
                    "Nuclear intensity measurements did not retain values above 8-bit range")
            require(result.get("model", {}).get("weights_updated_during_analysis") is False,
                    "Worker did not preserve its frozen-weight declaration")
            require(result.get("model", {}).get("training_reference") == "Not established",
                    "Worker asserted unsupported training provenance")

            artifact_path = community.get_file(job_id, owner, "expert_agents.json")
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
            execution = artifact.get("execution", {})
            require(execution.get("status") == "completed", "Specialist execution did not complete")
            require(execution.get("job_id") == job_id, "Specialist artifact is bound to a different job")
            require(execution.get("input_sha256") == fixture_sha,
                    "Specialist artifact is bound to a different input")
            agents = artifact.get("agents", [])
            require(len(agents) == 8, f"Expected 8 specialists; got {len(agents)}")
            require(execution.get("completed_agent_count") == 8,
                    "Specialist completion count is not eight")
            for agent in agents:
                digest = str(agent.get("evidence_sha256") or "")
                require(len(digest) == 64 and all(c in "0123456789abcdef" for c in digest),
                        f"Specialist {agent.get('agent')!r} has no valid evidence digest")
            intensity_agent = next((a for a in agents if a.get("agent") == "intensity_agent"), None)
            require(isinstance(intensity_agent, dict), "Intensity specialist output is missing")
            require("Raw image max: 65535" in intensity_agent.get("observations", []),
                    "Intensity specialist did not reason about the measured uint16 maximum")
            require(any(
                claim.get("reference") == "adaptive_plan.profile.max" and claim.get("value") == 65535
                for claim in intensity_agent.get("quantitative_claims", [])
            ), "Intensity specialist lacks an evidence-bound 65535 claim")

            required_files = [
                "segmentation_mask.tif",
                "overlay.tif",
                "measurements.csv",
                "results.json",
                "expert_agents.json",
                "nuclei_analysis.csv",
                "analysis_report.html",
                "analysis_report.json",
                "analysis_report.pdf",
            ]
            for name in required_files:
                path = community.get_file(job_id, owner, name)
                require(path.is_file() and path.stat().st_size > 0,
                        f"Required scientific artifact is missing or empty: {name}")

            archive_path = community.get_archive(job_id, owner)
            with zipfile.ZipFile(archive_path) as archive:
                names = set(archive.namelist())
                required_zip = {
                    "results/analysis_report.html",
                    "results/analysis_report.pdf",
                    "results/results.json",
                    "results/expert_agents.json",
                    "results/nuclei_analysis.csv",
                    "results/segmentation_mask.tif",
                    "results/overlay.tif",
                }
                require(required_zip.issubset(names),
                        f"ZIP missing required artifacts: {sorted(required_zip - names)}")
                forbidden = {
                    "input.tif",
                    "input.tiff",
                    "input.nd2",
                    "input_plane.tif",
                    fixture.name,
                }
                require(not any(Path(name).name in forbidden for name in names),
                        "ZIP contains the uploaded source image or extracted source plane")

            job_dir = community._job_dir(job_id)
            require(not (job_dir / "input.tif").exists(),
                    "Transient uploaded source image remained after successful processing")
            after_sha = sha256_file(checkpoint)
            require(after_sha == before_sha,
                    f"Checkpoint bytes changed during analysis: before={before_sha}, after={after_sha}")

            print(json.dumps({
                "status": "PASS",
                "job_id": job_id,
                "job_timeline": timeline,
                "fixture_sha256": fixture_sha,
                "checkpoint_sha256_before": before_sha,
                "checkpoint_sha256_after": after_sha,
                "image_shape": profile.get("shape"),
                "image_dtype": profile.get("dtype"),
                "raw_max": profile.get("max"),
                "measured_max_nuclear_intensity": intensity.get("max_nuclear_intensity"),
                "specialist_count": len(agents),
                "specialists": [
                    {"agent": a.get("agent"), "status": a.get("status"), "evidence_sha256": a.get("evidence_sha256")}
                    for a in agents
                ],
                "zip_artifacts": sorted(names),
                "source_image_excluded": True,
                "checkpoint_unchanged": True,
            }, indent=2, sort_keys=True))
        finally:
            if job_id:
                try:
                    community.delete_job(job_id, owner)
                except FileNotFoundError:
                    pass
                except Exception as exc:
                    print(f"cleanup warning: {type(exc).__name__}: {exc}", flush=True)
                require(community.get_job(job_id, owner) is None,
                        "Disposable validation job remained queryable after deletion")
                if archive_path is not None:
                    require(not archive_path.exists(),
                            "Disposable validation ZIP remained after deletion")


if __name__ == "__main__":
    main()
