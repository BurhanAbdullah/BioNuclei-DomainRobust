#!/usr/bin/env python3
"""Live browser E2E: public upload -> real inference -> evidence-backed specialists -> reports.

This intentionally does not monkeypatch the model. A failure is a release blocker,
not a reason to substitute synthetic inference.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
import zipfile
from pathlib import Path

import numpy as np
import requests
import tifffile
from playwright.sync_api import sync_playwright

SITE_URL = os.environ.get(
    "BIONUCLEI_PUBLIC_SITE_URL",
    "https://burhanabdullah.github.io/BioNuclei-DomainRobust/bionuclei-app.html",
)
API_BASE = os.environ.get(
    "BIONUCLEI_PUBLIC_API_URL",
    "https://bionuclei-community-analyzer.onrender.com",
).rstrip("/")
ANALYSIS_TIMEOUT_MS = int(os.environ.get("BIONUCLEI_ANALYSIS_TIMEOUT_MS", "1200000"))


def build_uint16_fixture(path: Path) -> str:
    """Create a deterministic, microscopy-like 512x512 uint16 TIFF with a 65535 sentinel."""
    image = np.full((512, 512), 512, dtype=np.uint16)
    yy, xx = np.ogrid[:512, :512]
    circles = [
        (100, 100, 18, 4096),
        (100, 180, 16, 8192),
        (220, 280, 20, 16384),
        (360, 160, 17, 32768),
    ]
    for cy, cx, radius, intensity in circles:
        image[(yy - cy) ** 2 + (xx - cx) ** 2 <= radius ** 2] = np.uint16(intensity)
    image[100, 100] = np.uint16(65535)
    tifffile.imwrite(path, image)
    reread = tifffile.imread(path)
    assert reread.shape == (512, 512) and reread.dtype == np.uint16
    assert int(reread.min()) == 512 and int(reread.max()) == 65535
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    state: dict[str, object] = {
        "site_url": SITE_URL,
        "api_base": API_BASE,
        "guest_token_seen": False,
        "job_id_seen": False,
    }
    deleted = False
    credentials: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="bionuclei-live-e2e-") as tmp:
        root = Path(tmp)
        fixture = root / "live-uint16-sentinel.tif"
        state["fixture_sha256"] = build_uint16_fixture(fixture)
        browser = None
        page = None
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(accept_downloads=True)
                page = context.new_page()

                def capture_response(response) -> None:
                    try:
                        if "/guest-session" in response.url and response.request.method == "POST":
                            body = response.json()
                            if isinstance(body, dict) and body.get("guest_token"):
                                credentials["guest_token"] = body["guest_token"]
                                state["guest_token_seen"] = True
                        elif response.url.rstrip("/").endswith("/analyze") and response.request.method == "POST":
                            body = response.json()
                            if isinstance(body, dict) and body.get("job_id"):
                                credentials["job_id"] = body["job_id"]
                                state["job_id_seen"] = True
                        elif re.search(r"/jobs/[^/]+$", response.url) and response.request.method == "GET":
                            body = response.json()
                            if isinstance(body, dict):
                                state["last_job_status"] = body.get("status")
                    except Exception:
                        pass

                page.on("response", capture_response)
                page.goto(SITE_URL, wait_until="domcontentloaded", timeout=90000)
                page.wait_for_function(
                    "() => window.BIONUCLEI_CONFIG && window.BIONUCLEI_CONFIG.apiBase",
                    timeout=30000,
                )
                configured_api = page.evaluate("window.BIONUCLEI_CONFIG.apiBase")
                require(
                    str(configured_api).rstrip("/") == API_BASE,
                    f"Published UI API mismatch: page={configured_api!r}, expected={API_BASE!r}",
                )
                page.locator("#guestButton").click(timeout=30000)
                page.wait_for_function(
                    "() => /guest session ready/i.test(document.querySelector('#guestMsg')?.textContent || '')",
                    timeout=45000,
                )
                require(state["guest_token_seen"] is True, "Guest session response/token was not observed")
                page.locator("#image").set_input_files(str(fixture))
                page.locator("#analyzeButton").click(timeout=30000)
                page.wait_for_function(
                    "() => { const p=document.querySelector('#resultPanel'); "
                    "const m=document.querySelector('#runMsg')?.textContent || ''; "
                    "return (p && !p.hidden) || /analysis status: failed/i.test(m); }",
                    timeout=ANALYSIS_TIMEOUT_MS,
                )
                status_text = page.locator("#runMsg").inner_text()
                state["run_message"] = status_text
                if re.search(r"analysis status: failed", status_text, re.IGNORECASE):
                    raise AssertionError(f"Real model job failed in the public workflow: {status_text}")
                require(state["job_id_seen"] is True, "Browser upload did not return a job ID")
                job_id = credentials["job_id"]
                token = credentials["guest_token"]
                headers = {"X-BioNuclei-Guest-Token": token}

                # Read through the same owner-scoped API that the browser uses.
                job_response = requests.get(f"{API_BASE}/jobs/{job_id}", headers=headers, timeout=30)
                state["job_http_status"] = job_response.status_code
                require(job_response.status_code == 200, f"Owned job GET returned {job_response.status_code}")
                job = job_response.json()
                require(job.get("status") == "completed", f"Job status is {job.get('status')!r}, not completed")
                result = job.get("result")
                if not isinstance(result, dict):
                    result_response = requests.get(
                        f"{API_BASE}/jobs/{job_id}/files/results.json", headers=headers, timeout=30
                    )
                    require(result_response.status_code == 200, "Completed job did not expose results.json")
                    result = result_response.json()
                state["input_sha256"] = result.get("input_sha256")
                require(result.get("scientific_execution") is True, "Result is not marked as scientific execution")
                require(
                    result.get("model", {}).get("weights_updated_during_analysis") is False,
                    "Released model did not assert frozen weights during user analysis",
                )
                require(
                    result.get("model", {}).get("training_reference") == "Not established",
                    "Unverified training provenance was not labeled Not established",
                )
                profile = result.get("adaptive_plan", {}).get("profile", {})
                require(profile.get("shape") == [512, 512], f"Unexpected input shape: {profile.get('shape')!r}")
                require(profile.get("dtype") == "uint16", f"Input dtype was not preserved: {profile.get('dtype')!r}")
                require(profile.get("max") == 65535, f"Full uint16 range lost before specialist reasoning: {profile.get('max')!r}")
                intensity = result.get("reports", {}).get("intensity", {})
                require(
                    intensity.get("max_nuclear_intensity") == 65535,
                    "65535 did not survive into the measured nuclear intensity; the real model did not segment the sentinel-containing object",
                )
                require(
                    float(intensity.get("mean_nuclear_intensity", 0)) > 255,
                    "Nuclear intensity measurements do not demonstrate values above 8-bit range",
                )

                artifact_response = requests.get(
                    f"{API_BASE}/jobs/{job_id}/files/expert_agents.json", headers=headers, timeout=30
                )
                require(artifact_response.status_code == 200, "Verified specialist artifact is unavailable")
                artifact = artifact_response.json()
                require(artifact.get("execution", {}).get("status") == "completed", "Specialist execution is incomplete")
                require(artifact.get("execution", {}).get("job_id") == job_id, "Specialist artifact is not bound to this job")
                require(
                    artifact.get("execution", {}).get("input_sha256") == result.get("input_sha256"),
                    "Specialist artifact input hash differs from the scientific result",
                )
                agents = artifact.get("agents", [])
                require(len(agents) == 8, f"Expected eight specialist outputs, received {len(agents)}")
                require(
                    artifact.get("execution", {}).get("completed_agent_count") == 8,
                    "Not all eight specialist reviewers completed",
                )
                intensity_agent = next((a for a in agents if a.get("agent") == "intensity_agent"), None)
                require(isinstance(intensity_agent, dict), "Intensity specialist output is missing")
                require(
                    "Raw image max: 65535" in intensity_agent.get("observations", []),
                    "Intensity specialist did not reason about the 16-bit raw-image maximum",
                )
                require(
                    any(
                        c.get("reference") == "adaptive_plan.profile.max" and c.get("value") == 65535
                        for c in intensity_agent.get("quantitative_claims", [])
                    ),
                    "Intensity specialist lacks an evidence-bound 65535 claim",
                )
                state["specialist_agents"] = [
                    {"agent": a.get("agent"), "status": a.get("status"), "evidence_sha256": a.get("evidence_sha256")}
                    for a in agents
                ]

                # This assertion is the public UI gate, not merely an API/artifact check.
                require(not page.locator("#resultPanel").is_hidden(), "Public browser did not display completed results")
                require(page.locator("#agentDetails .agent-finding").count() == 8, "Public browser did not render all eight specialist cards")
                require(page.locator("#agentDetails").get_by_text("Evidence SHA-256", exact=False).count() >= 8,
                        "Public browser did not display evidence digests for all specialist outputs")
                require(not page.locator("#downloadButton").is_disabled(), "Browser withheld download despite successful artifact verification")

                with page.expect_download(timeout=60000) as download_info:
                    page.locator("#downloadButton").click()
                download = download_info.value
                zip_path = root / "public-analysis.zip"
                download.save_as(str(zip_path))
                with zipfile.ZipFile(zip_path) as archive:
                    names = set(archive.namelist())
                    required = {
                        "results/analysis_report.html",
                        "results/analysis_report.pdf",
                        "results/results.json",
                        "results/expert_agents.json",
                        "results/nuclei_analysis.csv",
                        "results/segmentation_mask.tif",
                        "results/overlay.tif",
                    }
                    require(required.issubset(names), f"ZIP missing required artifacts: {sorted(required - names)}")
                    require(
                        not any(Path(name).name in {"input.tif", "input.tiff", "input.nd2", "input_plane.tif", fixture.name}
                                for name in names),
                        "ZIP contains the uploaded source image or an extracted source plane",
                    )
                state["zip_artifacts"] = sorted(names)

                page.locator("#deleteButton").click()
                page.wait_for_function(
                    "() => /analysis data deleted from the server/i.test(document.querySelector('#runMsg')?.textContent || '')",
                    timeout=30000,
                )
                deleted = True
                deleted_response = requests.get(f"{API_BASE}/jobs/{job_id}", headers=headers, timeout=30)
                require(deleted_response.status_code == 404, f"Deleted job remained accessible: HTTP {deleted_response.status_code}")
                state["deleted_job_http_status"] = deleted_response.status_code
                print(json.dumps({"status": "PASS", **state}, indent=2, sort_keys=True))
                context.close()
                browser.close()
        except Exception:
            try:
                if page is not None:
                    (Path("live-agent-e2e-failure.png")).parent.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path="live-agent-e2e-failure.png", full_page=True, timeout=15000)
            except Exception:
                pass
            print(json.dumps({"status": "FAIL", **state}, indent=2, sort_keys=True, default=str))
            raise
        finally:
            # Delete only the disposable job created by this run, even on assertion failure.
            job_id = credentials.get("job_id")
            token = credentials.get("guest_token")
            if job_id and token and not deleted:
                try:
                    requests.delete(
                        f"{API_BASE}/jobs/{job_id}",
                        headers={"X-BioNuclei-Guest-Token": str(token)},
                        timeout=30,
                    )
                except Exception:
                    pass
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass


if __name__ == "__main__":
    main()
