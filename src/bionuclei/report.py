"""Evidence based BioNuclei report generation."""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def _clean(value: object) -> str:
    return str(value).replace("–", " ").replace("—", " ")


def _fmt(value: object, digits: int = 4) -> str:
    if value is None:
        return "Not available"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return _clean(value)


def _training_status(payload: dict[str, Any]) -> dict[str, Any]:
    status = (payload.get("expert_agents") or {}).get("training_status") or {}
    return {
        "verified": bool(status.get("verified", False)),
        "validated_images": int(status.get("validated_images", 0) or 0),
        "training_reference": status.get("training_reference", "Not established"),
        "claim_allowed": bool(status.get("claim_allowed", False)),
    }


def _interpretation(payload: dict[str, Any]) -> list[str]:
    reports = payload.get("reports", {})
    morphology = reports.get("morphology", {})
    intensity = reports.get("intensity", {})
    plan = payload.get("adaptive_plan", {})
    profile = plan.get("profile", {})
    cnn = plan.get("cnn_pattern_check") or {}
    count = reports.get("nuclei_count", payload.get("n_instances"))
    out = [
        "The analysis was performed as an evidence based quantitative bioimaging workflow. Image quality characteristics were assessed before the released Boundary U Net model was used for nuclear segmentation. The CNN pattern assessment was treated as an analysisability gate rather than a calibrated diagnostic classifier.",
    ]
    if count is not None:
        out.append(f"The segmentation stage identified {_clean(count)} nuclear objects in the analysed field. This count describes objects detected by the computational pipeline and should not be interpreted as biological ground truth without experimental validation.")
    if morphology:
        out.append("Morphological measurements provide a population level description of nuclear geometry. Area, perimeter, eccentricity, solidity and circularity should be interpreted together because each quantity captures a different aspect of nuclear shape.")
    if intensity:
        out.append("Nuclear intensity measurements describe measured fluorescence signal within segmented nuclear regions. Differences can reflect biological signal, staining, exposure, background, photobleaching, detector response, or segmentation boundaries.")
    out.append(f"The image profile reports a median intensity of {_fmt(profile.get('median'))}, standard deviation {_fmt(profile.get('std'))}, and saturation fraction {_fmt(profile.get('saturation_fraction'))}. The CNN reported {_clean(cnn.get('status', 'NOT RUN'))} for the analysisability assessment.")
    out.append("The final interpretation is intentionally conservative. Computational evidence supports quantitative characterization of detected nuclear objects, but morphology and intensity measurements alone do not establish a biological mechanism, disease state, treatment response, or clinical diagnosis.")
    return out


def _agent_lines(payload: dict[str, Any]) -> list[str]:
    expert = payload.get("expert_agents") or {}
    lines: list[str] = []
    for item in expert.get("agents", []):
        name = _clean(item.get("agent", "specialist agent"))
        observations = "; ".join(_clean(x) for x in item.get("observations", []))
        limitations = "; ".join(_clean(x) for x in item.get("limitations", []))
        text = f"{name}: {observations or 'No additional observation.'}"
        if limitations:
            text += f" Limitation: {limitations}"
        lines.append(text)
    return lines


def _build_pdf(payload: dict[str, Any], output_dir: Path) -> Path:
    """Generate a PDF using built in Helvetica fonts available in ReportLab."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    path = output_dir / "analysis_report.pdf"
    reports = payload.get("reports", {})
    plan = payload.get("adaptive_plan", {})
    profile = plan.get("profile", {})
    model = payload.get("model", {})
    training = _training_status(payload)
    regular = "Helvetica"
    bold = "Helvetica-Bold"
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm, title="BioNuclei Quantitative Bioimaging Analysis Report", author="BioNuclei")
    title = ParagraphStyle("bn_title", fontName=bold, fontSize=18, leading=22, alignment=TA_CENTER, spaceAfter=8)
    heading = ParagraphStyle("bn_heading", fontName=bold, fontSize=12, leading=15, spaceBefore=8, spaceAfter=5)
    body = ParagraphStyle("bn_body", fontName=regular, fontSize=9.5, leading=13, spaceAfter=6)
    story = [Paragraph("BioNuclei Quantitative Bioimaging Analysis Report", title), Paragraph("Evidence based nuclear image analysis and scientific interpretation", body)]
    summary = [["Status", _clean(plan.get("status", "UNKNOWN"))], ["Nuclei detected", _clean(reports.get("nuclei_count", payload.get("n_instances", "Not available")))], ["Image shape", _clean(profile.get("shape", "Not available"))], ["Data type", _clean(profile.get("dtype", "Not available"))], ["Model", _clean(model.get("architecture", "Boundary U Net"))], ["Training reference", _clean(model.get("training_reference", "BBBC039v1"))], ["Specialist agents", str(len((payload.get("expert_agents") or {}).get("agents", [])))]]
    table = Table(summary, colWidths=[55 * mm, 110 * mm])
    table.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), regular), ("FONTNAME", (0, 0), (0, -1), bold), ("GRID", (0, 0), (-1, -1), .35, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 9), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story += [table, Paragraph("1. Executive Summary", heading)]
    for text in _interpretation(payload)[:2]:
        story.append(Paragraph(html.escape(_clean(text)), body))
    story.append(Paragraph("2. Image Quality and Analysisability", heading))
    for text in _interpretation(payload)[2:]:
        story.append(Paragraph(html.escape(_clean(text)), body))
    story.append(Paragraph("3. Nuclear Measurements", heading))
    morph = reports.get("morphology", {})
    intensity = reports.get("intensity", {})
    measurements = [["Mean area", _fmt(morph.get("mean_area"))], ["Mean perimeter", _fmt(morph.get("mean_perimeter"))], ["Mean eccentricity", _fmt(morph.get("mean_eccentricity"))], ["Mean solidity", _fmt(morph.get("mean_solidity"))], ["Mean circularity", _fmt(morph.get("mean_circularity"))], ["Mean nuclear intensity", _fmt(intensity.get("mean_nuclear_intensity"))]]
    mt = Table(measurements, colWidths=[55 * mm, 110 * mm])
    mt.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), regular), ("FONTNAME", (0, 0), (0, -1), bold), ("GRID", (0, 0), (-1, -1), .35, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story.append(mt)
    story.append(Paragraph("4. Specialist Evidence Chain", heading))
    for line in _agent_lines(payload) or ["No specialist agent findings were recorded for this run."]:
        story.append(Paragraph(html.escape(line), body))
    story.append(Paragraph(f"Verified training corpus status: {training['validated_images']} validated images. Model weights are not updated during user analysis. A claim of training on 1000 or more datasets requires a verified training manifest establishing that count.", body))
    story.append(Paragraph("5. Limitations", heading))
    for item in ["The CNN analysisability gate is not a calibrated diagnostic classifier.", "Object counts and morphology depend on segmentation quality and acquisition conditions.", "Fluorescence intensity depends on acquisition and staining conditions.", "Quantitative morphology does not establish a specific biological mechanism without appropriate controls.", "This software is not a clinical diagnostic system."]:
        story.append(Paragraph(html.escape(item), body))
    doc.build(story)
    return path


def build_report(payload: dict[str, Any], output_dir: Path) -> Path:
    """Write detailed HTML, PDF, and machine readable scientific reports."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    reports = payload.get("reports", {})
    model = payload.get("model", {})
    plan = payload.get("adaptive_plan", {})
    training = _training_status(payload)
    sections = []
    for text in _interpretation(payload):
        sections.append(f"<p>{html.escape(_clean(text))}</p>")
    agents = "".join(f"<li>{html.escape(line)}</li>" for line in _agent_lines(payload)) or "<li>No specialist agent findings were recorded for this run.</li>"
    page = f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><title>BioNuclei Analysis Report</title><style>body{{font-family:Arial,sans-serif;max-width:900px;margin:40px auto;padding:0 24px;line-height:1.55}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #bbb;padding:8px;text-align:left}}h1,h2{{margin-top:1.5em}}</style></head><body><h1>BioNuclei Quantitative Bioimaging Analysis Report</h1><p><strong>Status:</strong> {html.escape(_clean(plan.get('status','UNKNOWN')))}</p><table><tr><th>Nuclei detected</th><td>{html.escape(_clean(reports.get('nuclei_count',payload.get('n_instances','Not available'))))}</td></tr><tr><th>Model</th><td>{html.escape(_clean(model.get('architecture','Boundary U Net')))}</td></tr><tr><th>Training reference</th><td>{html.escape(_clean(model.get('training_reference','BBBC039v1')))}</td></tr></table><h2>Evidence summary</h2>{''.join(sections)}<h2>Specialist evidence chain</h2><ul>{agents}</ul><p><strong>model weights are not updated during user analysis.</strong> Verified specialist training corpus: {training['validated_images']} validated images. Claims about larger training counts require a verified manifest.</p><h2>Limitations</h2><p>This software reports computational measurements and evidence. It is not a clinical diagnostic system.</p></body></html>"""
    html_path = output_dir / "analysis_report.html"
    html_path.write_text(page, encoding="utf-8")
    (output_dir / "analysis_report.json").write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    return _build_pdf(payload, output_dir)
