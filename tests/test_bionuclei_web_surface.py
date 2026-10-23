from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAGE = DOCS / "bionuclei.html"
APP = DOCS / "bionuclei-app.html"
ASSET = DOCS / "assets" / "bionuclei-microscopy-illustration.svg"


def test_bionuclei_product_page_has_local_visual_and_core_sections() -> None:
    html = PAGE.read_text(encoding="utf-8")
    assert ASSET.is_file()
    assert 'src="assets/bionuclei-microscopy-illustration.svg"' in html
    for section_id in ["what", "model", "analyze", "outputs"]:
        assert f'id="{section_id}"' in html
    assert "Boundary U-Net" in html
    assert "2-D analysis plane" in html
    assert "measurements" in html.lower()
    assert "provenance" in html.lower()
    assert "synthetic illustration" in html.lower()
    assert "No biological diagnosis" in html


def test_bionuclei_product_page_does_not_claim_the_illustration_is_benchmark_data() -> None:
    html = PAGE.read_text(encoding="utf-8").lower()
    pos = html.find("bionuclei-microscopy-illustration.svg")
    assert pos >= 0
    context = html[pos : pos + 1400]
    assert "not benchmark data" in context
    assert "not used as evidence" in context


def test_active_upload_experience_runs_and_displays_verified_specialist_output() -> None:
    html = APP.read_text(encoding="utf-8")
    for script in ['src="assets/bionuclei-config.js"', 'src="assets/bionuclei-specialist-verification.js"',
                   'src="assets/bionuclei-analyzer.js"']:
        assert script in html
    for text in ['accept=".tif,.tiff,.nd2"', 'id="analyzeButton"', 'id="agentDetails"', 'id="resultPanel"',
                 "Upload microscopy image", "Analyzed overlay", "Segmentation mask", "Expert analysis layer",
                 "Download complete report", "Delete analysis data now"]:
        assert text in html
    config = (DOCS / "assets" / "bionuclei-config.js").read_text(encoding="utf-8")
    assert "https://bionuclei-community-analyzer.onrender.com" in config


def test_main_homepage_links_to_product_and_labels_visual_as_illustrative() -> None:
    homepage = (DOCS / "index.html").read_text(encoding="utf-8")
    assert 'href="bionuclei.html"' in homepage
    assert "Illustrative fluorescence microscopy field used as a product visual" in homepage
    assert "Open Lab" in homepage


def test_progress_adapter_displays_failed_job_as_terminal_alert() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for the browser progress-adapter test")

    asset = DOCS / "assets" / "bionuclei-progress.js"
    script = r"""
const fs = require("fs");
const vm = require("vm");
const host = { hidden: true, innerHTML: "" };
const runMsg = { innerHTML: "" };
const input = { files: [], addEventListener() {} };
const analyzeButton = { disabled: false };
const guestButton = { addEventListener() {} };
const elements = {
  analysisProgress: host,
  runMsg,
  image: input,
  analyzeButton,
  guestButton
};
const response = payload => ({
  ok: true,
  status: 200,
  json: async () => payload,
  clone: () => ({ json: async () => payload })
});
const window = {
  __BIONUCLEI_PROGRESS_BOOTED: false,
  BIONUCLEI_CONFIG: { apiBase: "https://api.example" },
  fetch: async url => {
    if (String(url).endsWith("/analyze")) return response({ job_id: "job-1" });
    if (String(url).endsWith("/jobs/job-1/progress")) {
      return response({ phase: "failed", message: "Analysis worker failed safely." });
    }
    throw new Error("Unexpected request: " + url);
  }
};
const document = {
  readyState: "complete",
  getElementById: id => elements[id] || null,
  querySelector: () => null,
  createElement: () => ({ hidden: true, innerHTML: "", className: "", appendChild() {} }),
  addEventListener() {}
};
const context = { window, document, Headers, console, setTimeout, clearTimeout, Promise };
vm.runInNewContext(fs.readFileSync(process.argv[1], "utf8"), context);
(async () => {
  await window.fetch("https://api.example/analyze", { method: "POST" });
  await new Promise(resolve => setTimeout(resolve, 40));
  if (window.__BIONUCLEI_ANALYSIS_ACTIVE !== false) throw new Error("failed job remained active");
  if (!host.innerHTML.includes("role=\"alert\"")) throw new Error("failure alert not rendered");
  if (!host.innerHTML.includes("Analysis worker failed safely.")) throw new Error("failure reason not rendered");
  if (host.innerHTML.includes("role=\"progressbar\"")) throw new Error("failed job still displays active progress");
  if (!runMsg.innerHTML.includes("Analysis worker failed safely.")) throw new Error("run message omitted failure reason");
  process.stdout.write("terminal-failure-ui-ok\\n");
})().catch(error => { console.error(error.stack || error); process.exit(1); });
"""
    result = subprocess.run(
        [node, "-e", script, str(asset)],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "terminal-failure-ui-ok" in result.stdout

