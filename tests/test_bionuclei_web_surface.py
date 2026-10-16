from pathlib import Path

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
