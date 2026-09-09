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


def test_lab_has_simple_real_user_flow():
    html = read("bionuclei-lab.html").lower()
    for text in [
        "upload an image. get the analysis.",
        "what do you want to know?",
        "find & count nuclei",
        "measure morphology",
        "measure fluorescence",
        "drop an nd2 or tiff here",
        "analyze image",
        "uploading",
        "analysis complete",
        "analyzed overlay",
        "segmentation mask",
        "download full report",
    ]:
        assert text in html
    assert "compute instance metrics" not in html
    assert "read provenance" not in html


def test_analysis_library_separates_available_and_validation_gated_features():
    html = read("bionuclei-analysis.html")
    assert "Find & count nuclei" in html
    assert "Measure morphology" in html
    assert "Measure fluorescence" in html
    assert "Colocalization" in html
    assert "Track objects" in html
    assert "Classify objects" in html
    assert "Validation required" in html


def test_formats_page_documents_nd2_explicit_plane_selection():
    html = read("bionuclei-formats.html")
    assert "Nikon ND2" in html
    for text in ["Channel", "Time", "Z / Field", "selected indices", "SHA-256"]:
        assert text in html


def test_community_page_has_explicit_research_consent():
    html = read("bionuclei-community.html")
    assert "Optional research contribution" in html
    assert "explicitly agree" in html
    assert "Research retention is opt-in" in html


def test_bionuclei_overview_is_concise_and_user_facing():
    html = read("bionuclei.html").lower()
    for text in [
        "see the nuclei.",
        "what it does",
        "one focused workflow.",
        "the model",
        "ai predicts. scientific code measures.",
        "training reference",
        "adaptive analysis",
        "agents help the workflow adapt.",
        "your result",
        "not just a mask.",
        "open the bionuclei lab",
    ]:
        assert text in html
    assert "which ai is actually being used?" not in html
    assert "api base url" not in html
    assert "inspect an image" not in html
    assert "evaluate against ground truth" not in html


def test_bionuclei_viewer_surface_exposes_original_overlay_and_segmentation():
    js = read("assets/bionuclei-minimal.js").lower()
    css = read("assets/bionuclei-viewer.css").lower()
    for text in [
        "original",
        "overlay.tif",
        "segmentation_mask.tif",
        "analysis result",
        "per-nucleus measurements",
        "download result bundle",
        "zoom",
        "/predict",
        "input_preview.png",
    ]:
        assert text in js
    for text in ["bn-viewer", "bn-tab", "bn-canvas-wrap", "bn-result-grid", "bn-table-wrap"]:
        assert text in css


def test_web_api_returns_original_browser_preview_with_analysis_artifacts():
    app = (ROOT / "webapp" / "app.py").read_text(encoding="utf-8").lower()
    assert "input_preview.png" in app
    assert "_artifact_payload(output_dir, original=image_path)" in app
    assert "segmentation_mask.tif" in app
    assert "overlay.tif" in app
