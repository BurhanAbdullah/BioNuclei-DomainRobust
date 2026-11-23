"""Evidence based BioNuclei report generation."""
from __future__ import annotations

import base64
import csv
import html
import io
import json
import math
import re
from pathlib import Path
from typing import Any


def _clean(value: object) -> str:
    return str(value).replace("–", " ").replace("—", " ")


def _training_status(payload: dict[str, Any]) -> dict[str, Any]:
    status = (payload.get("expert_agents") or {}).get("training_status") or {}
    verified = bool(status.get("verified", False) and status.get("claim_allowed", False))
    validated_images = status.get("validated_images")
    if isinstance(validated_images, bool) or not isinstance(validated_images, int) or validated_images < 0:
        validated_images = None
    if not verified:
        validated_images = None
    return {
        "verified": verified,
        "validated_images": validated_images,
        "training_reference": status.get("training_reference", "Not established") if verified else "Not established",
        "claim_allowed": verified,
    }


def _agent_lines(payload: dict[str, Any]) -> list[str]:
    """Render specialist execution status truthfully in detailed reports."""
    expert = payload.get("expert_agents") or {}
    lines: list[str] = []
    for item in expert.get("agents", []):
        name = _clean(item.get("agent", "specialist agent"))
        status = str(item.get("status", "unknown")).lower()
        observations = "; ".join(_clean(x).rstrip(". ") for x in item.get("observations", []))
        limitations = "; ".join(_clean(x).rstrip(". ") for x in item.get("limitations", []))
        observations = observations + "." if observations else observations
        limitations = limitations + "." if limitations else limitations
        if status == "not_applicable":
            text = f"{name}: NOT APPLICABLE — {observations or 'Required analysis module was not selected.'}"
        elif status != "completed":
            text = f"{name}: INCOMPLETE — {observations or 'Specialist execution did not complete.'}"
        else:
            text = f"{name}: COMPLETED — {observations or 'No additional observation.'}"
        if limitations:
            text += f" Limitation: {limitations}"
        lines.append(text)
    return lines


def _input_lines(payload: dict[str, Any]) -> list[str]:
    """Describe how the uploaded file was recognized and which plane was analyzed."""
    meta = payload.get("input_metadata") or {}
    if not meta:
        return []
    lines = []
    fmt = meta.get("input_format")
    if meta.get("recognized_as"):
        lines.append(f"Recognized as: {meta['recognized_as']} ({fmt}).")
    elif fmt:
        lines.append(f"Input format: {fmt}.")
    axes = meta.get("source_axes")
    shape = meta.get("source_shape")
    if axes and shape:
        lines.append(f"Source axes {axes} with shape {shape}.")
    selected = meta.get("selected_indices") or {}
    if selected:
        lines.append("Analyzed plane: " + ", ".join(f"{k} {v}" for k, v in selected.items()) + ".")
    plane = meta.get("selected_plane_shape")
    if plane:
        lines.append(f"Analyzed plane size: {plane[0]} x {plane[1]} px, {meta.get('selected_plane_dtype', meta.get('dtype', ''))}.")
    size = meta.get("pixel_size")
    if isinstance(size, dict) and size.get("x"):
        lines.append(f"Pixel size from {size.get('source', 'metadata')}: {size['x']:.4g} {size.get('unit', '')}. Measurements remain in pixels.")
    else:
        lines.append("No pixel size was found in the file metadata. All measurements are in pixels.")
    for note in meta.get("notes") or []:
        lines.append(str(note))
    return lines



# ---------------------------------------------------------------------------
# Presentation helpers
# ---------------------------------------------------------------------------
_LONG_DECIMAL = re.compile(r"(?<![\w.])(-?\d+\.\d{4,})(?![\d])")


def _num(value: object) -> str:
    """Readable number: thousands separators, sensible precision. Display only."""
    if value is None:
        return "Not available"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return "Not available"
        a = abs(value)
        if a >= 1000:
            return f"{value:,.0f}"
        if a >= 10:
            return f"{value:,.1f}"
        if a == 0:
            return "0"
        return f"{value:.3g}" if a < 0.001 else f"{value:.3f}".rstrip("0").rstrip(".")
    return _clean(value)


def _fmt(value: object, digits: int = 4) -> str:  # kept for backward compatibility
    return _num(value)


def _tidy(text: str) -> str:
    """Round long machine decimals inside specialist text for reading; JSON keeps full precision."""
    return _LONG_DECIMAL.sub(lambda m: _num(float(m.group(1))), _clean(text))


def _plural(n: int, one: str, many: str) -> str:
    return one if n == 1 else many


def _areas(output_dir: Path) -> list[float]:
    path = Path(output_dir) / "nuclei_analysis.csv"
    if not path.is_file():
        return []
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            return [float(row["area"]) for row in csv.DictReader(handle) if row.get("area") not in (None, "")]
    except (OSError, ValueError, KeyError):
        return []


def _review_flags(payload: dict[str, Any], areas: list[float]) -> list[str]:
    """Evidence-based reasons a reader must review the result before using it."""
    flags: list[str] = []
    plan = payload.get("adaptive_plan", {}) or {}
    status = str(plan.get("status", "UNKNOWN")).upper()
    if status not in {"READY", "UNKNOWN"}:
        flags.append(f"The input-quality gate returned {status}.")
    for warning in plan.get("warnings", []) or []:
        text = _clean(warning)
        if text not in flags:
            flags.append(text)
    reports = payload.get("reports", {}) or {}
    count = reports.get("nuclei_count", payload.get("n_instances"))
    shape = (plan.get("profile") or {}).get("shape") or payload.get("image_shape")
    image_area = float(shape[0]) * float(shape[1]) if isinstance(shape, (list, tuple)) and len(shape) == 2 else None
    if count == 0:
        flags.append("No nuclei were detected. Check that the analyzed channel contains a nuclear stain.")
    if image_area and areas:
        largest = max(areas)
        if largest > 0.25 * image_area:
            flags.append(f"One object covers {largest / image_area:.0%} of the image. A single nucleus this large is implausible; the segmentation is very likely invalid for this image.")
        if len(areas) > image_area / 40:
            flags.append(f"{len(areas):,} objects in {image_area:,.0f} px suggests over-segmentation (fewer than 40 px per object).")
    for meta_note in (payload.get("input_metadata") or {}).get("notes", []) or []:
        if str(meta_note).startswith("Warning:"):
            flags.append(_clean(meta_note).removeprefix("Warning: "))
    return flags


def _sections(payload: dict[str, Any]) -> dict[str, list[str]]:
    reports = payload.get("reports", {}) or {}
    plan = payload.get("adaptive_plan", {}) or {}
    profile = plan.get("profile", {}) or {}
    cnn = plan.get("cnn_pattern_check") or {}
    count = reports.get("nuclei_count", payload.get("n_instances"))
    summary = [
        "This report was produced by an evidence-based quantitative bioimaging workflow. Image quality was assessed before the released Boundary U-Net model segmented nuclei. The network-based analysability check is a gate, not a calibrated diagnostic classifier.",
    ]
    if count is not None:
        n = int(count)
        summary.append(f"The pipeline detected {n:,} {_plural(n, 'nuclear object', 'nuclear objects')} in the analyzed plane. This is a computational count, not biological ground truth, and it should be read together with the review notes above.")
    quality = []
    if profile:
        quality.append(f"Intensity profile of the analyzed plane: median {_num(profile.get('median'))}, standard deviation {_num(profile.get('std'))}, saturated pixels {_num(100 * float(profile.get('saturation_fraction') or 0))}%.")
    if cnn:
        quality.append(f"Network analysability check: {_clean(cnn.get('status', 'NOT RUN'))}. Foreground fraction {_num(cnn.get('foreground_fraction'))}, mean class confidence {_num(cnn.get('mean_class_confidence'))}, connected components {_num(cnn.get('connected_components'))}.")
    measures = []
    if reports.get("morphology"):
        measures.append("Morphology describes nuclear geometry. Area, perimeter, eccentricity, solidity and circularity capture different aspects of shape and should be read together. Values are in pixels unless a calibrated pixel size is reported.")
    if reports.get("intensity"):
        measures.append("Intensity values are raw detector units within each segmented nucleus. Differences can reflect biology, staining, exposure, background, photobleaching, detector response or segmentation boundaries.")
    closing = "The interpretation is intentionally conservative. Morphology and intensity alone do not establish a biological mechanism, disease state, treatment response or clinical diagnosis."
    return {"summary": summary, "quality": quality, "measures": measures, "closing": [closing]}


def _measure_rows(payload: dict[str, Any]) -> list[tuple[str, str]]:
    reports = payload.get("reports", {}) or {}
    m, i = reports.get("morphology", {}) or {}, reports.get("intensity", {}) or {}
    rows = [("Mean area (px²)", m.get("mean_area")), ("Median area (px²)", m.get("median_area")), ("Mean perimeter (px)", m.get("mean_perimeter")),
            ("Mean eccentricity", m.get("mean_eccentricity")), ("Mean solidity", m.get("mean_solidity")), ("Mean circularity", m.get("mean_circularity")),
            ("Mean nuclear intensity", i.get("mean_nuclear_intensity")), ("Median nuclear intensity", i.get("median_nuclear_intensity"))]
    return [(k, _num(v)) for k, v in rows if v is not None] or [("Measurements", "Not available")]


def _overlay_png(output_dir: Path, max_side: int = 900) -> bytes | None:
    path = Path(output_dir) / "overlay.tif"
    if not path.is_file():
        return None
    try:
        import numpy as np
        import tifffile
        from PIL import Image
        arr = np.asarray(tifffile.imread(path))
        if arr.dtype != np.uint8:
            hi = float(np.percentile(arr, 99.5)) or 1.0
            arr = np.clip(arr.astype(np.float32) * (255.0 / hi), 0, 255).astype(np.uint8)
        image = Image.fromarray(arr)
        image.thumbnail((max_side, max_side))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()
    except Exception:
        return None


def _histogram(areas: list[float], bins: int = 12) -> tuple[list[int], list[float]]:
    if not areas:
        return [], []
    lo, hi = min(areas), max(areas)
    if hi <= lo:
        return [len(areas)], [lo, hi]
    width = (hi - lo) / bins
    counts = [0] * bins
    for a in areas:
        counts[min(bins - 1, int((a - lo) / width))] += 1
    return counts, [lo + k * width for k in range(bins + 1)]


def _repro_rows(payload: dict[str, Any]) -> list[tuple[str, str]]:
    rows = [("Job", payload.get("job_id")), ("Source file", payload.get("source_filename")), ("Input SHA-256", payload.get("input_sha256")),
            ("Analysis modules", ", ".join(payload.get("analysis_modules", []) or []) or None), ("Model", (payload.get("model") or {}).get("architecture")),
            ("Weights updated during analysis", "No")]
    return [(k, _clean(v)) for k, v in rows if v not in (None, "")]


LIMITATIONS = [
    "The network analysability gate is not a calibrated diagnostic classifier.",
    "Object counts and morphology depend on segmentation quality and acquisition conditions.",
    "Fluorescence intensity depends on acquisition and staining conditions.",
    "Quantitative morphology does not establish a biological mechanism without appropriate controls.",
    "This software is not a clinical diagnostic system.",
]


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
def _build_pdf(payload: dict[str, Any], output_dir: Path, areas: list[float], flags: list[str], overlay: bytes | None) -> Path:
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.shapes import Drawing, String
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    wine, ink, grey, pale = colors.HexColor("#7B1638"), colors.HexColor("#111111"), colors.HexColor("#64646D"), colors.HexColor("#F5E8ED")
    path = output_dir / "analysis_report.pdf"
    reports = payload.get("reports", {}) or {}
    plan = payload.get("adaptive_plan", {}) or {}
    profile = plan.get("profile", {}) or {}
    model = payload.get("model", {}) or {}
    training = _training_status(payload)
    sec = _sections(payload)
    regular, bold = "Helvetica", "Helvetica-Bold"
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title="BioNuclei Quantitative Bioimaging Analysis Report", author="BioNuclei")
    title = ParagraphStyle("t", fontName=bold, fontSize=17, leading=21, textColor=ink, spaceAfter=2, alignment=TA_LEFT)
    sub = ParagraphStyle("s", fontName=regular, fontSize=9.5, leading=13, textColor=grey, spaceAfter=10)
    heading = ParagraphStyle("h", fontName=bold, fontSize=11.5, leading=15, textColor=wine, spaceBefore=10, spaceAfter=5)
    body = ParagraphStyle("b", fontName=regular, fontSize=9.5, leading=13.5, textColor=ink, spaceAfter=5)
    small = ParagraphStyle("sm", parent=body, fontSize=8.5, leading=12, textColor=grey)
    flag_style = ParagraphStyle("f", parent=body, leftIndent=8, bulletIndent=0)
    # Built-in PDF fonts have no superscript-two glyph: use ReportLab markup instead.
    esc = lambda t: html.escape(_tidy(str(t))).replace("²", "<super>2</super>")

    def table(rows, widths=(60 * mm, 114 * mm)):
        t = Table([[Paragraph(f"<b>{esc(k)}</b>", small), Paragraph(esc(v), body)] for k, v in rows], colWidths=list(widths))
        t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), .3, colors.HexColor("#E4E4E8")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
        return t

    count = reports.get("nuclei_count", payload.get("n_instances"))
    verdict = "Review required before use" if flags else "No automatic quality flags"
    story = [Paragraph("BioNuclei Quantitative Bioimaging Analysis Report", title),
             Paragraph("Evidence-based nuclear image analysis. Measurements in pixels unless stated otherwise.", sub),
             table([("Result", verdict), ("Quality gate", plan.get("status", "UNKNOWN")), ("Nuclei detected", _num(count)),
                    ("Analyzed plane", f"{profile.get('shape', ['?', '?'])[0]} × {profile.get('shape', ['?', '?'])[1]} px, {profile.get('dtype', 'unknown type')}" if profile.get("shape") else "Not available"),
                    ("Model", model.get("architecture", "Boundary U-Net")), ("Training reference", model.get("training_reference", "Not established")),
                    ("Specialist reviewers", str(len((payload.get("expert_agents") or {}).get("agents", []))))])]
    if flags:
        box = Table([[Paragraph("<b>Review before using these numbers</b>", ParagraphStyle("bx", parent=body, textColor=wine))]] +
                    [[Paragraph(esc(f), flag_style, bulletText="•")] for f in flags], colWidths=[174 * mm])
        box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), pale), ("LINEBEFORE", (0, 0), (0, -1), 3, wine),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        story += [Spacer(1, 8), box]
    input_lines = _input_lines(payload)
    if input_lines:
        story.append(Paragraph("Input recognition", heading))
        story += [Paragraph(esc(line), body) for line in input_lines]
    story.append(Paragraph("1. Executive Summary", heading))
    story += [Paragraph(esc(t), body) for t in sec["summary"]]
    story.append(Paragraph("2. Image Quality and Analysability", heading))
    story += [Paragraph(esc(t), body) for t in sec["quality"] or ["No image-quality profile was recorded."]]
    story.append(Paragraph("3. Nuclear Measurements", heading))
    story += [table(_measure_rows(payload))] + [Paragraph(esc(t), body) for t in sec["measures"]]

    figures = []
    if overlay:
        img = Image(io.BytesIO(overlay))
        scale = min(84 * mm / img.drawWidth, 84 * mm / img.drawHeight)
        img.drawWidth, img.drawHeight = img.drawWidth * scale, img.drawHeight * scale
        figures.append([img, Paragraph("Figure 1. Analyzed plane with detected nuclear boundaries.", small)])
    counts, edges = _histogram(areas)
    if counts:
        d = Drawing(84 * mm, 62 * mm)
        chart = VerticalBarChart()
        chart.x, chart.y, chart.width, chart.height = 22, 20, 84 * mm - 30, 62 * mm - 36
        chart.data = [counts]
        chart.bars[0].fillColor = wine
        chart.bars[0].strokeColor = None
        chart.valueAxis.valueMin = 0
        chart.valueAxis.labels.fontSize = 6.5
        chart.categoryAxis.categoryNames = [f"{edges[k]:,.0f}" if k % 3 == 0 else "" for k in range(len(counts))]
        chart.categoryAxis.labels.fontSize = 6.5
        d.add(chart)
        d.add(String(84 * mm / 2, 4, "Nuclear area (square pixels)", fontSize=7, textAnchor="middle", fillColor=grey))
        figures.append([d, Paragraph(f"Figure 2. Distribution of nuclear area, {len(areas):,} {_plural(len(areas), 'object', 'objects')}.", small)])
    if figures:
        story.append(Paragraph("Figures", heading))
        cells = [[f[0] for f in figures], [f[1] for f in figures]]
        ft = Table(cells, colWidths=[87 * mm] * len(figures))
        ft.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        story.append(KeepTogether(ft))

    story.append(Paragraph("4. Specialist Execution and Evidence Status", heading))
    for line in _agent_lines(payload) or ["No specialist agent findings were recorded for this run."]:
        story.append(Paragraph(esc(line), small))
    training_text = (f"Verified specialist training corpus: {training['validated_images']} validated images."
                     if training["verified"] and training["claim_allowed"] and training["validated_images"] is not None
                     else "Training provenance is not established; no training-image count is claimed.")
    story.append(Paragraph(esc(training_text + " Model weights are not updated during user analysis."), body))
    story.append(Paragraph("5. Limitations", heading))
    story += [Paragraph(esc(item), body, bulletText="•") for item in LIMITATIONS + sec["closing"]]
    repro = _repro_rows(payload)
    if repro:
        story.append(Paragraph("6. Reproducibility", heading))
        story.append(table(repro))
    doc.build(story)
    return path


# ---------------------------------------------------------------------------
# HTML + JSON + PDF
# ---------------------------------------------------------------------------
def build_report(payload: dict[str, Any], output_dir: Path) -> Path:
    """Write detailed HTML, PDF, and machine readable scientific reports."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    reports = payload.get("reports", {}) or {}
    model = payload.get("model", {}) or {}
    plan = payload.get("adaptive_plan", {}) or {}
    profile = plan.get("profile", {}) or {}
    training = _training_status(payload)
    areas = _areas(output_dir)
    flags = _review_flags(payload, areas)
    overlay = _overlay_png(output_dir)
    sec = _sections(payload)
    esc = lambda t: html.escape(_tidy(str(t)))
    count = reports.get("nuclei_count", payload.get("n_instances"))
    verdict = "Review required before use" if flags else "No automatic quality flags"
    rows = lambda pairs: "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in pairs)
    summary_rows = rows([("Result", verdict), ("Quality gate", plan.get("status", "UNKNOWN")), ("Nuclei detected", _num(count)),
                         ("Analyzed plane", f"{profile['shape'][0]} × {profile['shape'][1]} px, {profile.get('dtype', '')}" if profile.get("shape") else "Not available"),
                         ("Model", model.get("architecture", "Boundary U-Net")), ("Training reference", model.get("training_reference", "Not established"))])
    flag_html = ("<aside class='review'><b>Review before using these numbers</b><ul>" + "".join(f"<li>{esc(f)}</li>" for f in flags) + "</ul></aside>") if flags else ""
    input_html = "".join(f"<li>{esc(line)}</li>" for line in _input_lines(payload))
    input_section = f"<h2>Input recognition</h2><ul>{input_html}</ul>" if input_html else ""
    figs = []
    if overlay:
        figs.append(f"<figure><img alt='Analyzed plane with detected nuclear boundaries' src='data:image/png;base64,{base64.b64encode(overlay).decode()}'><figcaption>Figure 1. Analyzed plane with detected nuclear boundaries.</figcaption></figure>")
    counts, edges = _histogram(areas)
    if counts:
        peak = max(counts) or 1
        bars = "".join(f"<rect x='{8 + k * 24}' y='{150 - 130 * c / peak:.1f}' width='20' height='{130 * c / peak:.1f}' fill='#7B1638'><title>{edges[k]:,.0f}–{edges[k + 1]:,.0f} px²: {c}</title></rect>" for k, c in enumerate(counts))
        figs.append(f"<figure><svg viewBox='0 0 300 175' role='img' aria-label='Histogram of nuclear area'>{bars}<line x1='4' y1='150' x2='296' y2='150' stroke='#999'/><text x='4' y='168' font-size='9' fill='#64646D'>{edges[0]:,.0f}</text><text x='296' y='168' font-size='9' fill='#64646D' text-anchor='end'>{edges[-1]:,.0f} px²</text></svg><figcaption>Figure 2. Distribution of nuclear area, {len(areas):,} {_plural(len(areas), 'object', 'objects')}.</figcaption></figure>")
    figure_html = f"<h2>Figures</h2><div class='figs'>{''.join(figs)}</div>" if figs else ""
    agents = "".join(f"<li>{esc(line)}</li>" for line in _agent_lines(payload)) or "<li>No specialist agent findings were recorded for this run.</li>"
    training_text = (f"Verified specialist training corpus: {training['validated_images']} validated images."
                     if training["verified"] and training["claim_allowed"] and training["validated_images"] is not None
                     else "Training provenance is not established; no training-image count is claimed.")
    para = lambda items: "".join(f"<p>{esc(t)}</p>" for t in items)
    style = ("body{font-family:Inter,Segoe UI,Arial,sans-serif;max-width:920px;margin:40px auto;padding:0 24px;line-height:1.55;color:#111}"
             "h1{font-family:Georgia,serif;font-size:1.9rem;margin:0 0 4px}h2{color:#7B1638;font-size:1.1rem;margin-top:1.8em}"
             ".sub{color:#64646D;margin:0 0 18px}table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid #e4e4e8;padding:7px 8px;text-align:left;vertical-align:top}"
             "th{width:34%;color:#64646D;font-weight:600}.review{background:#F5E8ED;border-left:4px solid #7B1638;padding:12px 16px;margin:18px 0;border-radius:8px}"
             ".review ul{margin:6px 0 0;padding-left:20px}.figs{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px}"
             "figure{margin:0}figure img,figure svg{width:100%;height:auto;border-radius:8px;background:#05070a}figure svg{background:#fafafa}figcaption{font-size:.85rem;color:#64646D;margin-top:6px}"
             ".agents li{font-size:.86rem;color:#333;margin-bottom:6px}")
    page = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>BioNuclei Analysis Report</title><style>{style}</style></head><body>"
            f"<h1>BioNuclei Quantitative Bioimaging Analysis Report</h1><p class='sub'>Evidence-based nuclear image analysis. Measurements in pixels unless stated otherwise.</p>"
            f"<table>{summary_rows}</table>{flag_html}{input_section}"
            f"<h2>1. Executive summary</h2>{para(sec['summary'])}<h2>2. Image quality and analysability</h2>{para(sec['quality'] or ['No image-quality profile was recorded.'])}"
            f"<h2>3. Nuclear measurements</h2><table>{rows(_measure_rows(payload))}</table>{para(sec['measures'])}{figure_html}"
            f"<h2>4. Specialist execution and evidence status</h2><ul class='agents'>{agents}</ul>"
            f"<p><strong>Model weights are not updated during user analysis.</strong> {esc(training_text)}</p>"
            f"<h2>5. Limitations</h2><ul>{''.join(f'<li>{esc(x)}</li>' for x in LIMITATIONS + sec['closing'])}</ul>"
            + (f"<h2>6. Reproducibility</h2><table>{rows(_repro_rows(payload))}</table>" if _repro_rows(payload) else "")
            + "</body></html>")
    (output_dir / "analysis_report.html").write_text(page, encoding="utf-8")
    report_json = dict(payload)
    report_json["review"] = {"verdict": verdict, "flags": flags}
    (output_dir / "analysis_report.json").write_text(json.dumps(report_json, indent=2, default=str) + "\n", encoding="utf-8")
    return _build_pdf(payload, output_dir, areas, flags, overlay)
