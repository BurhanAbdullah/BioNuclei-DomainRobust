"""Professional evidence based BioNuclei report generation."""
from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Any


def _pdf_font() -> tuple[str, str]:
    """Prefer configured Times New Roman files and use a Times compatible fallback."""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        candidates = [os.getenv("BIONUCLEI_TNR_FONT", ""), "/usr/share/fonts/truetype/msttcorefonts/times.ttf", "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf"]
        bold_candidates = [os.getenv("BIONUCLEI_TNR_BOLD_FONT", ""), "/usr/share/fonts/truetype/msttcorefonts/timesbd.ttf", "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Bold.ttf"]
        regular = next((p for p in candidates if p and Path(p).is_file()), None)
        bold = next((p for p in bold_candidates if p and Path(p).is_file()), regular)
        if regular:
            pdfmetrics.registerFont(TTFont("BioNucleiTimes", regular))
            pdfmetrics.registerFont(TTFont("BioNucleiTimesBold", bold or regular))
            return "BioNucleiTimes", "BioNucleiTimesBold"
    except Exception:
        pass
    return "Times Roman", "Times Bold"


def _clean(value: object) -> str:
    """Make report prose safe and remove dash punctuation as requested."""
    return str(value).replace("–", " ").replace("—", " ").replace("-", " ")


def _fmt(value: object, digits: int = 4) -> str:
    if value is None:
        return "Not available"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return _clean(value)


def _expert_interpretation(payload: dict[str, Any]) -> list[str]:
    reports = payload.get("reports", {})
    morphology = reports.get("morphology", {})
    intensity = reports.get("intensity", {})
    plan = payload.get("adaptive_plan", {})
    profile = plan.get("profile", {})
    cnn = plan.get("cnn_pattern_check") or {}
    count = reports.get("nuclei_count", payload.get("n_instances"))
    paragraphs = [
        "The analysis was performed as an evidence based quantitative bioimaging workflow. Image quality characteristics were assessed before the released Boundary U Net model was used for nuclear segmentation. The CNN pattern assessment was treated as an analysisability gate rather than as a calibrated diagnostic classifier."
    ]
    if count is not None:
        paragraphs.append(f"The segmentation stage identified {_clean(count)} nuclear objects in the analysed field. This count describes objects detected by the computational pipeline and should not be interpreted as a biological ground truth without experimental validation.")
    if morphology:
        paragraphs.append("Morphological measurements provide a population level description of nuclear geometry. Mean area, perimeter, eccentricity, solidity and circularity should be interpreted together because each quantity captures a different aspect of nuclear shape. Increased dispersion can indicate biological heterogeneity, acquisition variation, segmentation uncertainty, or a combination of these factors.")
    if intensity:
        paragraphs.append("Nuclear intensity measurements describe the measured fluorescence signal within segmented nuclear regions. Intensity differences can reflect biological signal variation, staining efficiency, exposure, background, photobleaching, detector response, or segmentation boundaries. Quantitative comparisons between samples therefore require consistent acquisition and normalization procedures.")
    paragraphs.append(f"The image profile reports a median intensity of {_fmt(profile.get('median'))}, a standard deviation of {_fmt(profile.get('std'))}, and a saturation fraction of {_fmt(profile.get('saturation_fraction'))}. The CNN reported {_clean(cnn.get('status', 'NOT RUN'))} for the analysisability assessment. These measurements provide context for interpreting the downstream results.")
    paragraphs.append("The final interpretation is intentionally conservative. The computational evidence supports quantitative characterization of detected nuclear objects, but morphology and intensity measurements alone do not establish a specific biological mechanism, disease state, treatment response, or clinical diagnosis.")
    return paragraphs


def _agent_lines(payload: dict[str, Any]) -> list[str]:
    expert = payload.get("expert_agents") or {}
    lines = []
    for item in expert.get("agents", []):
        name = _clean(item.get("agent", "specialist agent"))
        observations = "; ".join(_clean(x) for x in item.get("observations", []))
        limitations = "; ".join(_clean(x) for x in item.get("limitations", []))
        text = f"{name}: {observations or 'No additional observation.'}"
        if limitations:
            text += f" Limitation: {limitations}"
        lines.append(text)
    return lines


def _training_status(payload: dict[str, Any]) -> dict[str, Any]:
    status = (payload.get("expert_agents") or {}).get("training_status") or {}
    return {
        "verified": bool(status.get("verified", False)),
        "validated_images": int(status.get("validated_images", 0) or 0),
        "training_reference": status.get("training_reference", "Not established"),
        "claim_allowed": bool(status.get("claim_allowed", False)),
    }


def _build_pdf(payload: dict[str, Any], output_dir: Path) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors

    regular, bold = _pdf_font()
    path = output_dir / "analysis_report.pdf"
    reports = payload.get("reports", {})
    morphology = reports.get("morphology", {})
    intensity = reports.get("intensity", {})
    plan = payload.get("adaptive_plan", {})
    profile = plan.get("profile", {})
    cnn = plan.get("cnn_pattern_check") or {}
    model = payload.get("model", {})
    status = _clean(plan.get("status", "UNKNOWN"))
    count = reports.get("nuclei_count", payload.get("n_instances", "Not available"))
    modules = ", ".join(_clean(x) for x in reports.get("modules", [])) or "Not specified"
    training = _training_status(payload)

    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm, title="BioNuclei Quantitative Bioimaging Analysis Report", author="BioNuclei")
    title = ParagraphStyle("title", fontName=bold, fontSize=19, leading=23, alignment=TA_CENTER, spaceAfter=8)
    subtitle = ParagraphStyle("subtitle", fontName=regular, fontSize=9.5, leading=13, alignment=TA_CENTER, spaceAfter=10)
    heading = ParagraphStyle("heading", fontName=bold, fontSize=12, leading=15, spaceBefore=9, spaceAfter=5)
    body = ParagraphStyle("body", fontName=regular, fontSize=10, leading=14, spaceAfter=6)
    small = ParagraphStyle("small", fontName=regular, fontSize=8, leading=10)
    story = [Paragraph("BioNuclei Quantitative Bioimaging Analysis Report", title), Paragraph("Evidence based nuclear image analysis and scientific interpretation", subtitle)]

    summary_data = [["Analysis status", status], ["Nuclei detected", _clean(count)], ["Image dimensions", _clean(profile.get("shape", "Not available"))], ["Image data type", _clean(profile.get("dtype", "Not available"))], ["Analysis modules", modules], ["CNN analysisability", _clean(cnn.get("status", "NOT RUN"))], ["Specialist agents", str(len((payload.get("expert_agents") or {}).get("agents", [])))]]
    table = Table(summary_data, colWidths=[62 * mm, 103 * mm])
    table.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), regular), ("FONTNAME", (0, 0), (0, -1), bold), ("FONTSIZE", (0, 0), (-1, -1), 9.5), ("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [table, Paragraph("1. Executive Summary", heading)]
    for text in _expert_interpretation(payload)[:2]: story.append(Paragraph(html.escape(_clean(text)), body))

    story.append(Paragraph("2. Sample and Image Information", heading))
    image_rows = [["Source filename", _clean(payload.get("source_filename", "Not available"))], ["Image shape", _clean(profile.get("shape", "Not available"))], ["Data type", _clean(profile.get("dtype", "Not available"))], ["Minimum intensity", _fmt(profile.get("min"))], ["Median intensity", _fmt(profile.get("median"))], ["Maximum intensity", _fmt(profile.get("max"))], ["Mean intensity", _fmt(profile.get("mean"))], ["Intensity standard deviation", _fmt(profile.get("std"))], ["Zero fraction", _fmt(profile.get("zero_fraction"))], ["Saturation fraction", _fmt(profile.get("saturation_fraction"))]]
    info = Table(image_rows, colWidths=[62 * mm, 103 * mm])
    info.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), regular), ("FONTNAME", (0, 0), (0, -1), bold), ("FONTSIZE", (0, 0), (-1, -1), 9), ("GRID", (0, 0), (-1, -1), 0.35, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(info)

    story.append(Paragraph("3. Image Quality Assessment", heading))
    quality_text = f"The input quality assessment found finite values equal to {_clean(profile.get('finite', 'Not available'))}, zero fraction {_fmt(profile.get('zero_fraction'))}, and saturation fraction {_fmt(profile.get('saturation_fraction'))}. These measurements are reported as acquisition context and are not themselves evidence of biological abnormality."
    story.append(Paragraph(html.escape(_clean(quality_text)), body))

    story.append(Paragraph("4. CNN Analysisability Assessment", heading))
    cnn_text = f"The released {_clean(cnn.get('architecture', model.get('architecture', 'Boundary U Net')))} was evaluated before full segmentation. The gate status was {_clean(cnn.get('status', 'NOT RUN'))}. Foreground fraction was {_fmt(cnn.get('foreground_fraction'))}, mean class confidence was {_fmt(cnn.get('mean_class_confidence'))}, mean entropy was {_fmt(cnn.get('mean_entropy'))}, and connected foreground components were {_clean(cnn.get('connected_components', 'Not available'))}. This gate is an analysisability check and is not a calibrated probability of correctness."
    story.append(Paragraph(html.escape(_clean(cnn_text)), body))
    if cnn.get("reasons"): story.append(Paragraph("CNN quality notes: " + html.escape(_clean(" ".join(cnn["reasons"]))), body))

    story.append(Paragraph("5. Nuclear Segmentation", heading))
    story.append(Paragraph(html.escape(_clean(f"The scientific runner used the {_clean(model.get('architecture', 'Boundary U Net'))} model in evaluation mode. The measured nuclear object count was {_clean(count)}. The segmentation result should be inspected visually, particularly for touching objects, fragmented objects, weak boundaries, and objects near the image border.")), body))

    story.append(Paragraph("6. Nuclear Morphology", heading))
    morph_rows = [["Mean area", _fmt(morphology.get("mean_area"))], ["Median area", _fmt(morphology.get("median_area"))], ["Mean perimeter", _fmt(morphology.get("mean_perimeter"))], ["Mean eccentricity", _fmt(morphology.get("mean_eccentricity"))], ["Mean solidity", _fmt(morphology.get("mean_solidity"))], ["Mean circularity", _fmt(morphology.get("mean_circularity"))]]
    mt = Table(morph_rows, colWidths=[62 * mm, 103 * mm])
    mt.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), regular), ("FONTNAME", (0, 0), (0, -1), bold), ("FONTSIZE", (0, 0), (-1, -1), 9), ("GRID", (0, 0), (-1, -1), 0.35, colors.grey), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(mt)
    for text in _expert_interpretation(payload)[2:3]: story.append(Paragraph(html.escape(_clean(text)), body))

    story.append(Paragraph("7. Nuclear Intensity", heading))
    int_rows = [["Mean nuclear intensity", _fmt(intensity.get("mean_nuclear_intensity"))], ["Median nuclear intensity", _fmt(intensity.get("median_nuclear_intensity"))], ["Mean maximum intensity", _fmt(intensity.get("mean_max_intensity"))]]
    it = Table(int_rows, colWidths=[62 * mm, 103 * mm])
    it.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), regular), ("FONTNAME", (0, 0), (0, -1), bold), ("FONTSIZE", (0, 0), (-1, -1), 9), ("GRID", (0, 0), (-1, -1), 0.35, colors.grey), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(it)
    for text in _expert_interpretation(payload)[3:4]: story.append(Paragraph(html.escape(_clean(text)), body))

    story.append(PageBreak())
    story.append(Paragraph("8. Integrated Bioimaging Interpretation", heading))
    for text in _expert_interpretation(payload): story.append(Paragraph(html.escape(_clean(text)), body))

    story.append(Paragraph("9. Quality Control and Limitations", heading))
    for item in ["The CNN analysisability gate is not a calibrated diagnostic classifier.", "Object counts and morphology depend on segmentation quality and image acquisition conditions.", "Fluorescence intensity is affected by acquisition and staining conditions and should be compared only under controlled protocols.", "Quantitative morphology does not establish a specific biological mechanism without appropriate experimental controls.", "This software does not provide clinical diagnosis."]: story.append(Paragraph(html.escape(_clean(item)), body))

    story.append(Paragraph("10. AI Specialist Evidence Chain", heading))
    agent_lines = _agent_lines(payload)
    if agent_lines:
        for line in agent_lines: story.append(Paragraph(html.escape(line), body))
    else: story.append(Paragraph("No specialist agent findings were recorded for this run.", body))
    story.append(Paragraph(f"Verified training corpus for these specialist agents: {training['validated_images']} validated images. A claim of training on 1000 or more datasets is permitted only when a verified training manifest establishes that count.", body))

    story.append(Paragraph("11. Reproducibility and Provenance", heading))
    provenance = [["Model architecture", _clean(model.get("architecture", "Boundary U Net"))], ["Training reference", _clean(model.get("training_reference", "BBBC039v1"))], ["Input SHA256", _clean(payload.get("input_sha256", "Not available"))], ["Analysis profile", _clean(payload.get("analysis_profile", "Not available"))]]
    pt = Table(provenance, colWidths=[62 * mm, 103 * mm])
    pt.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), regular), ("FONTNAME", (0, 0), (0, -1), bold), ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("GRID", (0, 0), (-1, -1), 0.35, colors.grey), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(pt)

    story.append(Paragraph("12. Conclusion", heading))
    story.append(Paragraph(html.escape(_clean("The report provides a quantitative description of the analysed microscopy field using the BioNuclei computational pipeline. The conclusions are limited to the measured image evidence and should be interpreted together with acquisition metadata, experimental controls, and visual inspection of the segmentation output.")), body))
    story.append(Spacer(1, 8))
    story.append(Paragraph("BioNuclei scientific image analysis software. Not a clinical diagnosis.", small))
    doc.build(story)
    return path


def build_report(payload: dict[str, Any], output_dir: Path) -> Path:
    """Write detailed HTML, PDF, and machine readable scientific reports."""
    plan = payload.get("adaptive_plan", {})
    profile = plan.get("profile", {})
    cnn = plan.get("cnn_pattern_check") or {}
    reports = payload.get("reports", {})
    model = payload.get("model", {})
    status = plan.get("status", "UNKNOWN")
    morphology = reports.get("morphology", {})
    intensity = reports.get("intensity", {})
    nuclei_count = reports.get("nuclei_count", payload.get("n_instances", "Not available"))
    training = _training_status(payload)
    report_json = output_dir / "analysis_report.json"
    report_html = output_dir / "analysis_report.html"
    report = {
        "report_version": "2.1",
        "analysis_status": status,
        "report_style": "professional quantitative bioimaging",
        "font_family": "Times New Roman preferred with Times compatible PDF fallback",
        "dash_punctuation_policy": "Removed from generated report prose",
        "adaptive_plan": plan,
        "model": model,
        "results": payload,
        "expert_interpretation": _expert_interpretation(payload),
        "expert_agents": payload.get("expert_agents", {}),
        "training_status": training,
    }
    report_json.write_text(json.dumps(report, indent=2) + "\n")

    esc = lambda v: html.escape(_clean(v))
    agent_html = "".join("<p><b>" + esc(item.get("agent", "specialist agent")) + ":</b> " + esc("; ".join(item.get("observations", []))) + "</p>" for item in (payload.get("expert_agents") or {}).get("agents", []))
    if not agent_html: agent_html = "<p>No specialist agent findings were recorded for this run.</p>"
    html_doc = f"""<!doctype html><html><head><meta charset='utf 8'><title>BioNuclei Quantitative Bioimaging Analysis Report</title><style>
body{{font-family:'Times New Roman',Times,serif;max-width:850px;margin:40px auto;padding:0 28px;color:#111;background:#fff;line-height:1.55;font-size:14px}}h1,h2,h3{{font-family:'Times New Roman',Times,serif;color:#111}}h1{{font-size:28px}}h2{{font-size:18px;margin-top:28px}}table{{border-collapse:collapse;width:100%;margin:12px 0 20px}}td{{border:1px solid #777;padding:8px;vertical-align:top}}td:first-child{{font-weight:bold;width:38%}}.small{{font-size:11px}}.note{{border:1px solid #777;padding:12px;background:#fff;color:#111}}</style></head><body>
<h1>BioNuclei Quantitative Bioimaging Analysis Report</h1><p><b>Analysis status:</b> {esc(status)}</p>
<h2>1. Executive Summary</h2><p>{esc(_expert_interpretation(payload)[0])}</p><p>{esc(_expert_interpretation(payload)[1])}</p>
<h2>2. Image Information</h2><table><tr><td>Source filename</td><td>{esc(payload.get('source_filename','Not available'))}</td></tr><tr><td>Image shape</td><td>{esc(profile.get('shape','Not available'))}</td></tr><tr><td>Data type</td><td>{esc(profile.get('dtype','Not available'))}</td></tr><tr><td>Nuclei detected</td><td>{esc(nuclei_count)}</td></tr><tr><td>CNN analysisability</td><td>{esc(cnn.get('status','NOT RUN'))}</td></tr></table>
<h2>3. CNN Analysisability Assessment</h2><p>Architecture: {esc(cnn.get('architecture',model.get('architecture','Boundary U Net')))}. Foreground fraction: {esc(_fmt(cnn.get('foreground_fraction')))}. Mean class confidence: {esc(_fmt(cnn.get('mean_class_confidence')))}. Mean entropy: {esc(_fmt(cnn.get('mean_entropy')))}. Connected components: {esc(cnn.get('connected_components','Not available'))}.</p>
<h2>4. Nuclear Morphology</h2><table><tr><td>Mean area</td><td>{esc(_fmt(morphology.get('mean_area')))}</td></tr><tr><td>Median area</td><td>{esc(_fmt(morphology.get('median_area')))}</td></tr><tr><td>Mean perimeter</td><td>{esc(_fmt(morphology.get('mean_perimeter')))}</td></tr><tr><td>Mean eccentricity</td><td>{esc(_fmt(morphology.get('mean_eccentricity')))}</td></tr><tr><td>Mean solidity</td><td>{esc(_fmt(morphology.get('mean_solidity')))}</td></tr><tr><td>Mean circularity</td><td>{esc(_fmt(morphology.get('mean_circularity')))}</td></tr></table>
<h2>5. Nuclear Intensity</h2><table><tr><td>Mean nuclear intensity</td><td>{esc(_fmt(intensity.get('mean_nuclear_intensity')))}</td></tr><tr><td>Median nuclear intensity</td><td>{esc(_fmt(intensity.get('median_nuclear_intensity')))}</td></tr><tr><td>Mean maximum intensity</td><td>{esc(_fmt(intensity.get('mean_max_intensity')))}</td></tr></table>
<h2>6. Integrated Bioimaging Interpretation</h2>{''.join('<p>'+esc(x)+'</p>' for x in _expert_interpretation(payload))}
<h2>7. Quality Control and Limitations</h2><p>The CNN gate is an analysisability check rather than a calibrated diagnostic classifier. Quantitative measurements depend on image acquisition and segmentation quality. Morphology and intensity measurements do not establish a specific biological mechanism without appropriate controls.</p>
<h2>8. AI Specialist Evidence Chain</h2>{agent_html}<p><b>Verified training corpus:</b> {training['validated_images']} validated images. The report does not claim 1000 or more datasets unless a verified training manifest supports that statement.</p>
<h2>9. Reproducibility and Provenance</h2><p>Model: {esc(model.get('architecture','Boundary U Net'))}. Training reference: {esc(model.get('training_reference','BBBC039v1'))}. Input SHA256: {esc(payload.get('input_sha256','Not available'))}.</p>
<p class='small'>BioNuclei scientific image analysis software. Not a clinical diagnosis.</p></body></html>"""
    report_html.write_text(html_doc)
    _build_pdf(payload, output_dir)
    return report_html
