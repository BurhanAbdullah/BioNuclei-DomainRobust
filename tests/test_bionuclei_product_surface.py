from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def read(name: str) -> str:
    return (DOCS / name).read_text(encoding="utf-8")


def test_main_landing_page_stays_minimal():
    html = read("index.html")
    assert "Try / inspect / reproduce" not in html
    assert "Results are separated from the demo." not in html
    assert "From image to result in four steps." not in html


def test_lab_routes_local_preview_into_the_real_analyzer():
    lab = read("bionuclei-lab.html").lower()
    for text in ["choose how you want to work.", "open image", "supported inputs: nikon nd2 and tiff/tif",
                 "manual mode", "automated mode", "continue to analysis", "bionuclei-app.html"]:
        assert text in lab
    app = read("bionuclei-app.html").lower()
    for text in ["upload microscopy image", "analyze image", "expert analysis layer", "download complete report",
                 "delete analysis data now", "bionuclei-config.js", "bionuclei-specialist-verification.js",
                 "bionuclei-analyzer.js", 'id="image"', 'id="analyzebutton"', 'id="agentdetails"']:
        assert text in app


def test_analysis_library_separates_available_and_validation_gated_features():
    html = unescape(read("bionuclei-analysis.html"))
    for text in ["Find & count nuclei", "Measure morphology", "Measure fluorescence", "Colocalization",
                 "Track objects", "Classify objects", "Validation required"]:
        assert text in html


def test_formats_page_documents_nd2_explicit_plane_selection():
    html = read("bionuclei-formats.html")
    for text in ["Nikon ND2", "Channel", "Time", "Z / Field", "selected indices", "SHA-256"]:
        assert text in html


def test_community_page_has_explicit_research_consent():
    html = read("bionuclei-community.html")
    assert "Optional research contribution" in html
    assert "explicitly agree" in html
    assert "Without the research checkbox" in html
    assert "does not retain a research copy" in html
    assert "optional and separate from running the analysis" in html


def test_bionuclei_overview_is_concise_and_user_facing():
    html = read("bionuclei.html").lower()
    for text in ["see the nuclei.", "what it does", "one focused workflow, now inspectable.", "the model",
                 "ai predicts. scientific code measures.", "no online training", "adaptive analysis",
                 "deterministic specialist reviewers", "your result", "do not stop at the mask.",
                 "open the bionuclei analyzer", "not benchmark data", "not used as evidence"]:
        assert text in html
    for stale in ["which ai is actually being used?", "api base url", "inspect an image", "evaluate against ground truth"]:
        assert stale not in html


def test_bionuclei_viewer_surface_exposes_original_overlay_and_segmentation():
    js = read("assets/bionuclei-minimal.js").lower()
    css = read("assets/bionuclei-viewer.css").lower()
    for text in ["original", "overlay.tif", "segmentation_mask.tif", "analysis result", "per-nucleus measurements",
                 "download result bundle", "zoom", "/predict", "input_preview.png"]:
        assert text in js
    for text in ["bn-viewer", "bn-tab", "bn-canvas-wrap", "bn-result-grid", "bn-table-wrap"]:
        assert text in css


def test_web_api_returns_original_browser_preview_with_analysis_artifacts():
    app = (ROOT / "webapp" / "app.py").read_text(encoding="utf-8").lower()
    for text in ["input_preview.png", "_artifact_payload(output_dir, original=image_path)", "segmentation_mask.tif", "overlay.tif"]:
        assert text in app
