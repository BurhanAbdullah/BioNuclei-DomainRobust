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
    html = read("bionuclei-lab.html")
    lower = html.lower()
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
        assert text in lower
    assert "endpoint" in lower
    assert "compute instance metrics" not in lower
    assert "read provenance" not in lower


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


def test_bionuclei_product_page_is_user_facing_and_minimal():
    html = read("bionuclei.html")
    lower = html.lower()
    for text in [
        "From microscopy image to a report you can inspect.",
        "What BioNuclei analyzes",
        "Boundary U-Net",
        "What the current model was trained on.",
        "Agents help decide how to analyze the image.",
        "What you actually get back",
    ]:
        assert text.lower() in lower
    assert "API base URL" not in html
    assert "six tools" not in lower
