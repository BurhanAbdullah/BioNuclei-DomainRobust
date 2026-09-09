"""Detailed, deterministic BioNuclei report generation."""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def build_report(payload: dict[str, Any], output_dir: Path) -> Path:
    """Write a self-contained HTML report plus machine-readable JSON summary."""
    plan = payload.get("adaptive_plan", {})
    profile = plan.get("profile", {})
    reports = payload.get("reports", {})
    warnings = plan.get("warnings", [])
    status = plan.get("status", "UNKNOWN")
    model = payload.get("model", {})
    files = sorted(p.name for p in output_dir.iterdir() if p.is_file())
    report_files = sorted(set(files) | {"analysis_report.json", "analysis_report.html"})

    def esc(value: Any) -> str:
        return html.escape(str(value))

    warning_html = "".join(f"<li>{esc(w)}</li>" for w in warnings) or "<li>No input-quality warnings were triggered by the configured checks.</li>"
    file_html = "".join(f"<li><code>{esc(name)}</code></li>" for name in report_files)
    report_json = output_dir / "analysis_report.json"
    report_html = output_dir / "analysis_report.html"

    report = {
        "report_version": "1.0",
        "analysis_status": status,
        "adaptive_plan": plan,
        "model": model,
        "results": payload,
        "generated_files": report_files,
        "scientific_interpretation": {
            "model_training": "The uploaded image is used for inference; this analysis does not update model weights.",
            "accuracy_metrics": "Dice/IoU/Boundary-F1/AJI are only valid when an appropriate ground-truth evaluation protocol is supplied.",
            "domain_warning": "Input-quality warnings are diagnostic signals, not calibrated probabilities of correctness.",
        },
    }
    report_json.write_text(json.dumps(report, indent=2) + "\n")

    morphology = reports.get("morphology", {})
    intensity = reports.get("intensity", {})
    nuclei_count = reports.get("nuclei_count", payload.get("n_instances", "—"))
    html_doc = f"""<!doctype html>
<html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>BioNuclei Analysis Report</title>
<style>body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;max-width:980px;margin:40px auto;padding:0 20px;color:#17212b;line-height:1.55}}h1,h2{{line-height:1.1}}.hero{{padding:28px;border-radius:18px;background:#0d171e;color:white}}.status{{display:inline-block;padding:6px 10px;border-radius:999px;background:#24353f;color:#fff;font-weight:700;font-size:12px}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.card{{padding:16px;border:1px solid #d8e0e5;border-radius:12px}}.muted{{color:#62717f}}.warn{{background:#fff7e6;border-left:4px solid #b77908;padding:14px 16px;border-radius:8px}}code{{background:#eef2f4;padding:2px 5px;border-radius:4px}}@media(max-width:700px){{.grid{{grid-template-columns:1fr}}}}</style>
</head><body>
<section class='hero'><div>BioNuclei · Detailed analysis</div><h1>What BioNuclei found in this image</h1><span class='status'>{esc(status)}</span><p>Adaptive workflow planning and deterministic scientific analysis. The image is analyzed with the configured checkpoint; model weights are not updated by this run.</p></section>
<h2>Input profile</h2><div class='grid'>
<div class='card'><b>Shape</b><div>{esc(profile.get('shape','—'))}</div></div>
<div class='card'><b>Type</b><div>{esc(profile.get('dtype','—'))}</div></div>
<div class='card'><b>Intensity</b><div>{esc(profile.get('min','—'))} → {esc(profile.get('p995','—'))}</div></div>
</div>
<h2>Analysis result</h2><div class='grid'>
<div class='card'><b>Nuclei detected</b><div>{esc(nuclei_count)}</div></div>
<div class='card'><b>Mean nucleus area</b><div>{esc(morphology.get('mean_area','—'))}</div></div>
<div class='card'><b>Mean nuclear intensity</b><div>{esc(intensity.get('mean_nuclear_intensity','—'))}</div></div>
</div>
<h2>Adaptive checks</h2><div class='warn'><ul>{warning_html}</ul></div>
<h2>Model</h2><div class='card'><b>{esc(model.get('architecture','Boundary U-Net'))}</b><p>{esc(model.get('training_reference','Training reference: BBBC039v1'))}</p><p>{esc(model.get('target','3-class background/interior/boundary prediction'))}</p></div>
<h2>Generated files</h2><ul>{file_html}</ul>
<h2>Scientific interpretation</h2><p class='muted'>This report describes the executed analysis and observed image properties. It does not turn input warnings into calibrated accuracy estimates, and it does not claim clinical or biological diagnosis.</p>
</body></html>"""
    report_html.write_text(html_doc)
    return report_html
