from pathlib import Path

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
            "training_reference": "BBBC039v1",
            "target": "3-class background/interior/boundary prediction",
        },
        "n_instances": 7,
        "reports": {
            "nuclei_count": 7,
            "morphology": {"mean_area": 41.0},
            "intensity": {"mean_nuclear_intensity": 512.0},
        },
    }
    build_report(payload, tmp_path)
    html = (tmp_path / "analysis_report.html").read_text()
    data = (tmp_path / "analysis_report.json").read_text()
    assert "model weights are not updated" in html
    assert "BBBC039v1" in html
    assert "analysis_report.json" in data
