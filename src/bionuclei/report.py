"""Concise BioNuclei report generation."""
from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Any


def _pdf_font() -> tuple[str, str]:
    """Prefer a configured Times New Roman font and otherwise use PDF Times."""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        candidates = [
            os.getenv("BIONUCLEI_TNR_FONT", ""),
            "/usr/share/fonts/truetype/msttcorefonts/times.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf",
        ]
        bold_candidates = [
            os.getenv("BIONUCLEI_TNR_BOLD_FONT", ""),
            "/usr/share/fonts/truetype/msttcorefonts/timesbd.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Bold.ttf",
        ]
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
    text = str(value)
    return text.replace("–", " ").replace("—", " ").replace("-", " ")


def _build_pdf(payload: dict[str, Any], output_dir: Path) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
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

    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=22 * mm, leftMargin=22 * mm, topMargin=20 * mm, bottomMargin=20 * mm)
    title = ParagraphStyle("title", fontName=bold, fontSize=19, leading=23, alignment=TA_CENTER, spaceAfter=8)
    heading = ParagraphStyle("heading", fontName=bold, fontSize=12, leading=15, spaceBefore=8, spaceAfter=5)
    body = ParagraphStyle("body", fontName=regular, fontSize=10.5, leading=14, spaceAfter=4)
    small = ParagraphStyle("small", fontName=regular, fontSize=8.5, leading=11)

    story = [Paragraph("BioNuclei Analysis Report", title), Paragraph(status, ParagraphStyle("status", parent=body, alignment=TA_CENTER)), Spacer(1, 4)]
    data = [
        ["Nuclei detected", str(count)],
        ["Image shape", _clean(profile.get("shape", "Not available"))],
        ["Mean nucleus area", str(morphology.get("mean_area", "Not available"))],
        ["Mean nuclear intensity", str(intensity.get("mean_nuclear_intensity", "Not available"))],
    ]
    table = Table(data, colWidths=[70 * mm, 75 * mm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), regular),
        ("FONTNAME", (0, 0), (0, -1), bold),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story += [
        Paragraph("CNN pattern check", heading),
        Paragraph(
            f"{_clean(cnn.get('status', 'NOT RUN'))}. Foreground fraction {cnn.get('foreground_fraction', 'Not available')}. "
            f"Mean class confidence {cnn.get('mean_class_confidence', 'Not available')}. "
            f"Connected components {cnn.get('connected_components', 'Not available')}.",
            body,
        ),
        Paragraph("Model", heading),
        Paragraph(
            f"{_clean(model.get('architecture', 'Boundary U Net'))}. Training reference {html.escape(_clean(model.get('training_reference', 'BBBC039v1')))}.",
            body,
        ),
    ]
    warnings = plan.get("warnings", [])
    if warnings:
        story += [Paragraph("Quality notes", heading), Paragraph(" ".join(_clean(x) for x in warnings), body)]
    story += [Spacer(1, 8), Paragraph("This report records the executed image analysis. It is not a clinical diagnosis.", small)]
    doc.build(story)
    return path


def build_report(payload: dict[str, Any], output_dir: Path) -> Path:
    """Write concise HTML and PDF reports plus machine readable JSON."""
    plan = payload.get("adaptive_plan", {})
    profile = plan.get("profile", {})
    cnn = plan.get("cnn_pattern_check") or {}
    reports = payload.get("reports", {})
    model = payload.get("model", {})
    status = plan.get("status", "UNKNOWN")
    morphology = reports.get("morphology", {})
    intensity = reports.get("intensity", {})
    nuclei_count = reports.get("nuclei_count", payload.get("n_instances", "Not available"))
    report_json = output_dir / "analysis_report.json"
    report_html = output_dir / "analysis_report.html"
    report = {"report_version": "1.2", "analysis_status": status, "adaptive_plan": plan, "model": model, "results": payload}
    report_json.write_text(json.dumps(report, indent=2) + "\n")
    esc = lambda v: html.escape(_clean(v))
    html_doc = f"""<!doctype html><html><head><meta charset='utf 8'><title>BioNuclei Analysis Report</title><style>body{{font-family:'Times New Roman',Times,serif;max-width:760px;margin:40px auto;padding:0 24px;color:#111;line-height:1.45}}h1,h2{{font-family:'Times New Roman',Times,serif}}table{{border-collapse:collapse;width:100%}}td{{border:1px solid #bbb;padding:8px}}td:first-child{{font-weight:bold;width:45%}}.small{{font-size:11px}}</style></head><body><h1>BioNuclei Analysis Report</h1><p>{esc(status)}</p><table><tr><td>Nuclei detected</td><td>{esc(nuclei_count)}</td></tr><tr><td>Image shape</td><td>{esc(profile.get('shape','Not available'))}</td></tr><tr><td>Mean nucleus area</td><td>{esc(morphology.get('mean_area','Not available'))}</td></tr><tr><td>Mean nuclear intensity</td><td>{esc(intensity.get('mean_nuclear_intensity','Not available'))}</td></tr></table><h2>CNN pattern check</h2><p>{esc(cnn.get('status','NOT RUN'))}. Foreground fraction {esc(cnn.get('foreground_fraction','Not available'))}. Mean class confidence {esc(cnn.get('mean_class_confidence','Not available'))}.</p><h2>Model</h2><p>{esc(model.get('architecture','Boundary U Net'))}. Training reference {esc(model.get('training_reference','BBBC039v1'))}.</p><p class='small'>This report records the executed image analysis. It is not a clinical diagnosis.</p></body></html>"""
    report_html.write_text(html_doc)
    _build_pdf(payload, output_dir)
    return report_html
