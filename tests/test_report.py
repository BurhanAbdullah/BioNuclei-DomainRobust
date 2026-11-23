import json
from pathlib import Path

from pypdf import PdfReader

from bionuclei.report import build_report


def test_detailed_report_contains_non_training_boundary(tmp_path: Path) -> None:
    payload = {
        "adaptive_plan": {
            "status": "READY",
            "warnings": [],
            "profile": {"shape": [64, 64], "dtype": "uint16", "min": 0, "p995": 1200},
        },
        "model": {
            "architecture": "Boundary U-Net",
            "training_reference": "Not established",
            "target": "3-class background/interior/boundary prediction",
        },
        "n_instances": 7,
        "reports": {
            "nuclei_count": 7,
            "morphology": {"mean_area": 41.0},
            "intensity": {"mean_nuclear_intensity": 512.0},
        },
    }
    pdf_path = build_report(payload, tmp_path)
    html = (tmp_path / "analysis_report.html").read_text()
    json_path = tmp_path / "analysis_report.json"
    assert "model weights are not updated" in html.lower()
    assert "Not established" in html
    assert "BBBC039v1" not in html
    assert json_path.is_file()
    data = json.loads(json_path.read_text())
    assert data["n_instances"] == 7

    assert pdf_path.is_file()
    assert pdf_path.stat().st_size > 1000
    reader = PdfReader(str(pdf_path), strict=True)
    assert len(reader.pages) >= 1
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "BioNuclei Quantitative Bioimaging Analysis Report" in pdf_text
    assert "Training provenance is not established" in pdf_text


def test_detailed_report_labels_not_applicable_specialists_truthfully(tmp_path: Path) -> None:
    payload = {
        "adaptive_plan": {
            "status": "READY",
            "profile": {"shape": [64, 64], "dtype": "uint16", "min": 0, "p995": 1200},
        },
        "model": {
            "architecture": "Boundary U-Net",
            "training_reference": "Not established",
            "weights_updated_during_analysis": False,
        },
        "analysis_modules": ["nuclei"],
        "reports": {"nuclei_count": 3},
        "expert_agents": {
            "training_status": {"verified": False, "claim_allowed": False},
            "agents": [
                {
                    "agent": "nuclei_qc_agent",
                    "status": "completed",
                    "observations": ["Computed nuclei QC passed."],
                    "limitations": [],
                },
                {
                    "agent": "morphology_agent",
                    "status": "not_applicable",
                    "observations": ["Not applicable: required analysis module(s) not selected: morphology."],
                    "limitations": ["This reviewer did not execute because its required modules were not selected; no findings or quantitative claims are asserted."],
                },
                {
                    "agent": "intensity_agent",
                    "status": "not_applicable",
                    "observations": ["Not applicable: required analysis module(s) not selected: intensity."],
                    "limitations": ["This reviewer did not execute because its required modules were not selected; no findings or quantitative claims are asserted."],
                },
            ],
        },
    }
    build_report(payload, tmp_path)
    html = (tmp_path / "analysis_report.html").read_text(encoding="utf-8")
    assert "nuclei_qc_agent: COMPLETED" in html
    assert "morphology_agent: NOT APPLICABLE" in html
    assert "intensity_agent: NOT APPLICABLE" in html
    assert "not applicable" in html.lower()
    assert "Training provenance is not established" in html


def test_report_flags_implausible_segmentation_and_formats_numbers(tmp_path: Path) -> None:
    import tifffile
    import numpy as np
    (tmp_path / "nuclei_analysis.csv").write_text("label,area\n1,147456\n", encoding="utf-8")
    tifffile.imwrite(tmp_path / "overlay.tif", np.zeros((64, 64, 3), dtype=np.uint8))
    payload = {
        "adaptive_plan": {"status": "CAUTION", "warnings": ["CNN class confidence is low."], "profile": {"shape": [384, 384], "dtype": "uint16", "median": 312.0, "std": 498.50859267840536, "saturation_fraction": 0.0}},
        "model": {"architecture": "Boundary U-Net", "training_reference": "Not established"},
        "n_instances": 1,
        "reports": {"nuclei_count": 1, "morphology": {"mean_area": 147456.0}, "intensity": {"mean_nuclear_intensity": 463.78721788194446}},
        "expert_agents": {"agents": [{"agent": "intensity_agent", "status": "completed", "observations": ["Raw image p995: 3149.725000000006.", "Mean: 463.78721788194446."]}]},
    }
    build_report(payload, tmp_path)
    page = (tmp_path / "analysis_report.html").read_text(encoding="utf-8")
    assert "Review required before use" in page
    assert "One object covers 100% of the image" in page
    assert "CNN class confidence is low." in page
    assert "1 nuclear object in" in page and "1 nuclear objects" not in page
    assert "3149.725000000006" not in page and "3,150" in page and "463.8" in page
    assert "analysisability" not in page.lower()
    assert ".;" not in page
    assert "data:image/png;base64," in page and "Histogram of nuclear area" in page
    review = json.loads((tmp_path / "analysis_report.json").read_text())["review"]
    assert review["verdict"] == "Review required before use" and len(review["flags"]) >= 3
    text = "".join(p.extract_text() for p in PdfReader(str(tmp_path / "analysis_report.pdf")).pages)
    assert "Review before using these numbers" in text and "Figure 2" in text


def test_clean_result_has_no_review_flags(tmp_path: Path) -> None:
    (tmp_path / "nuclei_analysis.csv").write_text("label,area\n" + "".join(f"{i},{100 + i}\n" for i in range(1, 30)), encoding="utf-8")
    payload = {"adaptive_plan": {"status": "READY", "warnings": [], "profile": {"shape": [512, 512], "dtype": "uint16"}},
               "model": {"architecture": "Boundary U-Net"}, "reports": {"nuclei_count": 29}}
    build_report(payload, tmp_path)
    page = (tmp_path / "analysis_report.html").read_text(encoding="utf-8")
    assert "No automatic quality flags" in page and "Review before using" not in page
    assert "29 nuclear objects" in page


def test_review_flags_fragments_that_inflate_the_count():
    from bionuclei.report import _review_flags
    areas = [1200.0] * 40 + [5.0] * 60
    flags = _review_flags({"n_instances": 100, "image_shape": [512, 512]}, areas)
    assert any("likely fragments" in f for f in flags)
    clean = _review_flags({"n_instances": 40, "image_shape": [512, 512]}, [1200.0] * 40)
    assert not any("fragments" in f for f in clean)


def test_calibrated_area_rows_use_micron_pixel_size():
    from bionuclei.report import _measure_rows
    payload = {"input_metadata": {"pixel_size": {"x": 0.5, "y": 0.5, "unit": "µm", "source": "ImageJ"}},
               "reports": {"morphology": {"mean_area": 400.0, "median_area": 100.0, "mean_perimeter": 80.0}}}
    rows = dict(_measure_rows(payload))
    num = lambda k: float(rows[k].replace(",", ""))
    assert num("Mean area (µm²)") == 100 and num("Median area (µm²)") == 25 and num("Mean perimeter (µm)") == 40
    plain = dict(_measure_rows({"reports": {"morphology": {"mean_area": 400.0}}}))
    assert not any("µm" in k for k in plain)
