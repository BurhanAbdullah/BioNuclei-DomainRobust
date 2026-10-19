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
    # A small saturated nuclear core survives ordinary instance masks more
    # reliably than a single-pixel sentinel while affecting far less than 1%
    # of the field. The test still requires real inference and real measurements.
    image[97:104, 97:104] = np.uint16(65535)
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

                # Test-only observation wrapper. It never substitutes, rewrites, or
                # mocks an API response; it clones real responses so the E2E harness
                # can record the ephemeral guest token/job ID even if Playwright's
                # response event body is unavailable on a specific browser build.
                page.add_init_script("""
                (() => {
                  const nativeFetch = window.fetch.bind(window);
                  window.__BIONUCLEI_E2E_TRACE = [];
                  window.__BIONUCLEI_E2E_GUEST_TOKEN = "";
                  window.__BIONUCLEI_E2E_JOB_ID = "";
                  window.fetch = async (...args) => {
                    const input = args[0];
                    const options = args[1] || {};
                    const rawUrl = typeof input === "string" ? input : (input && input.url) || String(input);
                    const method = String(options.method || (input && input.method) || "GET").toUpperCase();
                    const response = await nativeFetch(...args);
                    try {
                      const url = new URL(rawUrl, window.location.href);
                      if (url.pathname.includes("/guest-session") || url.pathname.endsWith("/analyze") || /\/jobs\/[^/]+$/.test(url.pathname)) {
                        const record = {path: url.pathname, method, status: response.status, ok: response.ok};
                        window.__BIONUCLEI_E2E_TRACE.push(record);
                        if (window.__BIONUCLEI_E2E_TRACE.length > 60) window.__BIONUCLEI_E2E_TRACE.shift();
                        response.clone().json().then(body => {
                          if (url.pathname.includes("/guest-session") && body && typeof body.guest_token === "string") {
                            window.__BIONUCLEI_E2E_GUEST_TOKEN = body.guest_token;
                            record.response_keys = Object.keys(body).sort();
                          }
                          if (url.pathname.endsWith("/analyze") && body && typeof body.job_id === "string") {
                            window.__BIONUCLEI_E2E_JOB_ID = body.job_id;
                            record.response_keys = Object.keys(body).sort();
                          }
                          if (body && typeof body.detail === "string") record.detail = body.detail.slice(0, 240);
                        }).catch(error => { record.clone_parse_error = String(error && error.name || "Error"); });
                      }
                    } catch (error) {
                      window.__BIONUCLEI_E2E_TRACE.push({path:"<unparsed>", method, capture_error:String(error && error.name || "Error")});
                    }
                    return response;
                  };
                })();
                """)

                def capture_response(response) -> None:
                    try:
                        if "/guest-session" in response.url and response.request.method == "POST":
                            state["guest_session_response_seen"] = True
                            state["guest_session_http_status"] = response.status
                            state["guest_session_response_url_path"] = response.url.split("?", 1)[0][-160:]
                            try:
                                body = response.json()
                            except Exception as exc:
                                state["guest_session_response_parse_error"] = type(exc).__name__
                                body = {}
                            if isinstance(body, dict):
                                state["guest_session_response_keys"] = sorted(body.keys())
                                if body.get("guest_token"):
                                    credentials["guest_token"] = body["guest_token"]
                                    state["guest_token_seen"] = True
                        elif response.url.rstrip("/").endswith("/analyze") and response.request.method == "POST":
                            state["analyze_http_status"] = response.status
                            try:
                                body = response.json()
                            except Exception:
                                body = {"detail": (response.text() or "")[:300]}
                            if isinstance(body, dict) and body.get("job_id"):
                                credentials["job_id"] = body["job_id"]
                                state["job_id_seen"] = True
                            elif response.status >= 400:
                                # Keep server diagnostics but never copy bearer or guest-token headers.
                                state["analyze_error"] = str(body.get("detail") or body.get("error") or f"HTTP {response.status}")[:300]
                        elif re.search(r"/jobs/[^/]+$", response.url) and response.request.method == "GET":
                            body = response.json()
                            if isinstance(body, dict):
                                state["last_job_status"] = body.get("status")
                    except Exception:
                        pass

                page.on("response", capture_response)
                page.on("pageerror", lambda exc: state.setdefault("browser_page_errors", []).append(str(exc)[:240]))
                page.on("console", lambda msg: state.setdefault("browser_console_errors", []).append(msg.text[:240])
                           if msg.type == "error" and len(state.get("browser_console_errors", [])) < 12 else None)
                page.on("requestfailed", lambda req: state.setdefault("browser_request_failures", []).append({
                    "path": re.sub(r"^https?://[^/]+", "", req.url).split("?", 1)[0][-160:],
                    "method": req.method,
                    "failure": (req.failure or "unknown")[:160],
                }) if ("/guest-session" in req.url or "/analyze" in req.url or "bionuclei" in req.url.lower())
                     and len(state.get("browser_request_failures", [])) < 20 else None)
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
                page.locator('[data-access-tab="guest"]').click(timeout=30000)
                page.locator("#guestButton").click(timeout=30000)
                try:
                    page.wait_for_function(
                        "() => /guest session ready/i.test(document.querySelector('#guestMsg')?.textContent || '')",
                        timeout=45000,
                    )
                except Exception:
                    state["guest_message"] = page.locator("#guestMsg").inner_text()[:300]
                    state["run_message_before_upload"] = page.locator("#runMsg").inner_text()[:300]
                    state["guest_button_disabled"] = page.locator("#guestButton").is_disabled()
                    state["guest_panel_visible"] = page.locator('[data-access-panel="guest"]').is_visible()
                    state["page_url_path"] = page.url.split("?", 1)[0][-180:]
                    state["browser_fetch_trace"] = page.evaluate("window.__BIONUCLEI_E2E_TRACE || []")
                    state["browser_page_errors"] = state.get("browser_page_errors", [])
                    state["browser_console_errors"] = state.get("browser_console_errors", [])
                    state["browser_request_failures"] = state.get("browser_request_failures", [])
                    raise AssertionError("Guest session did not reach the ready state; inspect sanitized browser diagnostics.")
                if not credentials.get("guest_token"):
                    # JSON parsing of the cloned response is asynchronous. Let that
                    # observer finish briefly before reading it; never log the token.
                    try:
                        page.wait_for_function("() => Boolean(window.__BIONUCLEI_E2E_GUEST_TOKEN)", timeout=5000)
                    except Exception:
                        pass
                    observed_token = page.evaluate("window.__BIONUCLEI_E2E_GUEST_TOKEN || ''")
                    if isinstance(observed_token, str) and observed_token:
                        credentials["guest_token"] = observed_token
                        state["guest_token_seen"] = True
                        state["guest_token_source"] = "cloned browser response"
                state["browser_fetch_trace"] = page.evaluate("window.__BIONUCLEI_E2E_TRACE || []")
                if not state["guest_token_seen"]:
                    state["guest_message"] = page.locator("#guestMsg").inner_text()[:300]
                    state["run_message_before_upload"] = page.locator("#runMsg").inner_text()[:300]
                    state["browser_page_errors"] = state.get("browser_page_errors", [])
                    state["browser_console_errors"] = state.get("browser_console_errors", [])
                    state["browser_request_failures"] = state.get("browser_request_failures", [])
                require(state["guest_token_seen"] is True, "Guest session response/token was not observed")
                page.locator("#image").set_input_files(str(fixture))
                page.locator("#analyzeButton").click(timeout=30000)
                # Get the job ID from the real response clone if the browser event
                # listener did not receive the response body.
                if not credentials.get("job_id"):
                    try:
                        page.wait_for_function("() => Boolean(window.__BIONUCLEI_E2E_JOB_ID)", timeout=10000)
                        observed_job_id = page.evaluate("window.__BIONUCLEI_E2E_JOB_ID || ''")
                        if isinstance(observed_job_id, str) and observed_job_id:
                            credentials["job_id"] = observed_job_id
                            state["job_id_seen"] = True
                            state["job_id_source"] = "cloned browser response"
                    except Exception:
                        pass

                # Poll the owner-scoped job record directly and track actual stage
                # transitions. A native worker that stalls at "planning" should
                # produce a diagnosis in minutes, not consume a 20-minute blind wait.
                analysis_started = time.monotonic()
                deadline = analysis_started + ANALYSIS_TIMEOUT_MS / 1000.0
                stall_timeout = int(os.environ.get("BIONUCLEI_JOB_STALL_TIMEOUT_SECONDS", "240"))
                last_signature = None
                last_transition_at = analysis_started
                last_successful_job_poll_at = analysis_started
                state["job_timeline"] = []
                job_response = None
                job = None
                while time.monotonic() < deadline:
                    elapsed = time.monotonic() - analysis_started
                    if not credentials.get("job_id") or not credentials.get("guest_token"):
                        if state.get("analyze_http_status", 0) >= 400:
                            raise AssertionError(
                                f"Public /analyze returned HTTP {state['analyze_http_status']}: "
                                f"{state.get('analyze_error', 'no response details')}"
                            )
                        if elapsed > stall_timeout:
                            raise AssertionError(
                                f"Browser did not obtain an owner-scoped job ID within {stall_timeout}s; "
                                f"guest_token_seen={state.get('guest_token_seen')}, "
                                f"analyze_http_status={state.get('analyze_http_status')!r}"
                            )
                        time.sleep(0.5)
                        continue
                    job_id = credentials["job_id"]
                    token = credentials["guest_token"]
                    headers = {"X-BioNuclei-Guest-Token": token}
                    try:
                        job_response = requests.get(f"{API_BASE}/jobs/{job_id}", headers=headers, timeout=20)
                        state["last_job_http_status"] = job_response.status_code
                        if job_response.status_code == 200:
                            last_successful_job_poll_at = time.monotonic()
                            job = job_response.json()
                            status = str(job.get("status") or "unknown")
                            updated_at = str(job.get("updated_at") or "")
                            signature = (status, updated_at)
                            if signature != last_signature:
                                state["job_timeline"].append({
                                    "status": status,
                                    "updated_at": updated_at,
                                    "seconds_since_submit": round(time.monotonic() - analysis_started, 1),
                                })
                                last_signature = signature
                                last_transition_at = time.monotonic()
                            state["last_job_status"] = status
                            if status == "failed":
                                state["backend_error"] = job.get("error")
                                raise AssertionError(
                                    f"Real model job failed in the public workflow: {job.get('error') or 'no error detail'}"
                                )
                            if status == "completed":
                                break
                            if time.monotonic() - last_transition_at > stall_timeout:
                                raise AssertionError(
                                    f"Analysis worker made no status/heartbeat progress for {stall_timeout}s; "
                                    f"status={status!r}, updated_at={updated_at!r}. "
                                    "Inspect Render worker logs and memory limits."
                                )
                        elif job_response.status_code not in {429, 502, 503, 504}:
                            raise AssertionError(
                                f"Owned job polling returned HTTP {job_response.status_code}: "
                                f"{job_response.text[:300]}"
                            )
                        else:
                            state["last_poll_http_error"] = job_response.status_code
                            state["last_poll_http_body"] = job_response.text[:200]
                    except requests.RequestException as exc:
                        state["last_poll_error"] = type(exc).__name__
                    if time.monotonic() - last_successful_job_poll_at > stall_timeout:
                        raise AssertionError(
                            f"Public job endpoint has not returned a successful owner-scoped poll for "
                            f"{stall_timeout}s; last HTTP error={state.get('last_poll_http_error')!r}, "
                            f"network error={state.get('last_poll_error')!r}"
                        )
                    time.sleep(5)
                else:
                    raise AssertionError(
                        f"Analysis timed out after {ANALYSIS_TIMEOUT_MS / 1000:.0f}s; "
                        f"last observed status={state.get('last_job_status')!r}"
                    )
                require(job is not None and job.get("status") == "completed",
                        f"Public job did not complete: {None if job is None else job.get('status')!r}")
                page.wait_for_function(
                    "() => { const p=document.querySelector('#resultPanel'); return !!p && !p.hidden; }",
                    timeout=60000,
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
                if page is not None and not page.is_closed():
                    page.screenshot(path="live-agent-e2e-failure.png", full_page=True, timeout=15000)
            except Exception:
                pass
            # Persist redacted status/timing diagnostics even if the browser or
            # screenshot fails. Never serialize guest tokens or auth headers.
            try:
                Path("live-agent-e2e-failure.json").write_text(
                    json.dumps({"status": "FAIL", **state}, indent=2, sort_keys=True, default=str) + "\n",
                    encoding="utf-8",
                )
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
