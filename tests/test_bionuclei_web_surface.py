from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "bionuclei.html"
ASSET = ROOT / "docs" / "assets" / "bionuclei-microscopy-illustration.svg"
UPLOAD_JS = ROOT / "docs" / "assets" / "bionuclei-upload.js"
SITE_JS = ROOT / "docs" / "assets" / "site.js"


def test_bionuclei_product_page_has_local_visual_and_core_sections() -> None:
    html = PAGE.read_text(encoding="utf-8")
    assert ASSET.is_file(), "BioNuclei microscopy illustration asset is missing"
    assert 'src="assets/bionuclei-microscopy-illustration.svg"' in html
    assert 'id="what"' in html
    assert 'id="model"' in html
    assert 'id="analyze"' in html
    assert 'id="outputs"' in html
    assert "Boundary U-Net" in html
    assert "2-D fluorescence" in html
    assert "measurements + provenance" in html.lower()
    assert "synthetic illustration" in html.lower()
    assert "No biological diagnosis" in html


def test_bionuclei_product_page_does_not_claim_the_illustration_is_benchmark_data() -> None:
    html = PAGE.read_text(encoding="utf-8").lower()
    marker = "bionuclei-microscopy-illustration.svg"
    pos = html.find(marker)
    assert pos >= 0
    context = html[pos : pos + 1400]
    assert "not benchmark data" in context
    assert "not used as evidence" in context


def test_bionuclei_upload_experience_has_visible_state_and_nd2_support() -> None:
    html = PAGE.read_text(encoding="utf-8")
    js = UPLOAD_JS.read_text(encoding="utf-8")
    site_js = SITE_JS.read_text(encoding="utf-8")
    assert UPLOAD_JS.is_file(), "BioNuclei upload UX helper is missing"
    assert "bionuclei-upload.js" in site_js
    assert ".nd2,.tif,.tiff" in js
    assert "Uploading " in js
    assert "Analysis complete" in js
    assert "no live BioNuclei API is configured" in js.lower()
    assert "document.readyState" in js


def test_main_ecosystem_homepage_is_not_edited_by_bionuclei_visual_change() -> None:
    # The product visual belongs only to the dedicated BioNuclei page.
    homepage = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    assert "bionuclei-microscopy-illustration.svg" not in homepage
