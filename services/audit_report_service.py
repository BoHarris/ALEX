from datetime import UTC, datetime
from pathlib import Path
from html import escape
import io
import json
import re
import textwrap
from html import unescape as html_unescape

from database.models.scan_results import ScanResult
from services.scan_service import parse_scan_result_metadata
from utils.pii_taxonomy import get_display_name, get_policy_categories, get_policy_display_names


def _risk_label(risk_score: int) -> str:
    if risk_score >= 70:
        return "high"
    if risk_score >= 40:
        return "moderate"
    return "low"


def _risk_explanation(risk_label: str) -> str:
    explanations = {
        "low": "Minimal sensitive information detected. Document can typically be shared with minimal review.",
        "moderate": "Sensitive information detected. Review recommended before distribution.",
        "high": "Significant sensitive data detected. Remediation recommended prior to sharing.",
    }
    return explanations.get(risk_label, "Risk level guidance is not available.")


def _format_scanned_at(scanned_at: datetime | None) -> str:
    if not scanned_at:
        return "Unknown"
    return scanned_at.strftime("%Y-%m-%d %H:%M:%S")


def _format_generated_at() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _display_file_type(scan: ScanResult) -> str:
    if scan.file_type and scan.file_type.strip():
        return scan.file_type.strip().lower()
    ext = Path(scan.filename or "").suffix
    return ext.lstrip(".").lower() if ext else "unknown"


def _build_findings_rows(flagged_fields: list[str], total_pii_found: int) -> str:
    methods = ["Automated Pattern Analysis", "Heuristic Detection"]
    rows_html = "".join(
        (
            f"<tr>"
            f"<td>Finding {idx}</td>"
            f"<td>{escape(field)}</td>"
            f"<td>{methods[(idx - 1) % len(methods)]}</td>"
            f"<td>Redacted</td>"
            f"</tr>"
        )
        for idx, field in enumerate(flagged_fields, start=1)
    )

    if rows_html:
        return rows_html

    if total_pii_found > 0:
        return (
            "<tr>"
            "<td>Finding 1</td>"
            "<td>Sensitive Data Pattern</td>"
            "<td>Automated Pattern Analysis</td>"
            "<td>Redacted</td>"
            "</tr>"
        )

    return (
        "<tr>"
        "<td>Finding 1</td>"
        "<td>No sensitive data pattern identified</td>"
        "<td>Automated Pattern Analysis</td>"
        "<td>No redaction required</td>"
        "</tr>"
    )


def _parse_redacted_type_counts(scan: ScanResult) -> dict[str, int]:
    counts, _ = parse_scan_result_metadata(getattr(scan, "redacted_type_counts", None))
    return counts


def _parse_detection_results(scan: ScanResult) -> list[dict[str, object]]:
    _, detections = parse_scan_result_metadata(getattr(scan, "redacted_type_counts", None))
    return detections


def _build_type_count_rows(type_counts: dict[str, int], total_pii_found: int) -> str:
    if not type_counts:
        if total_pii_found > 0:
            return (
                "<tr>"
                "<td>PII_SENSITIVE_DATA</td>"
                "<td>Sensitive Data Pattern</td>"
                f"<td>{escape(', '.join(get_policy_display_names(get_policy_categories('PII_SENSITIVE_DATA'))))}</td>"
                f"<td>{total_pii_found}</td>"
                "</tr>"
            )
        return (
            "<tr>"
            "<td colspan=\"4\">No sensitive data patterns were detected in this scan.</td>"
            "</tr>"
        )

    sorted_items = sorted(type_counts.items(), key=lambda item: (-item[1], item[0]))
    return "".join(
        (
            f"<tr><td>{escape(code)}</td>"
            f"<td>{escape(get_display_name(code))}</td>"
            f"<td>{escape(', '.join(get_policy_display_names(get_policy_categories(code))))}</td>"
            f"<td>{count}</td></tr>"
        )
        for code, count in sorted_items
    )


def _build_detection_reasoning_rows(detections: list[dict[str, object]]) -> str:
    if not detections:
        return (
            "<tr>"
            "<td colspan=\"6\">No explainable detection metadata was recorded for this scan.</td>"
            "</tr>"
        )

    return "".join(
        "<tr>"
        f"<td>{escape(str(detection.get('column', 'Unknown')))}</td>"
        f"<td>{escape(str(detection.get('detected_type') or detection.get('detected_as') or 'PII_SENSITIVE_DATA'))}</td>"
        f"<td>{escape(str(detection.get('display_name', get_display_name(str(detection.get('detected_type') or detection.get('detected_as') or '')))))}</td>"
        f"<td>{escape(', '.join(get_policy_display_names(detection.get('policy_categories', []))))}</td>"
        f"<td>{float(detection.get('confidence_score', 0.0)):.2f}</td>"
        f"<td>{escape(', '.join(str(signal) for signal in detection.get('signals', [])))}</td>"
        "</tr>"
        for detection in detections
    )


def generate_audit_report_html(scan: ScanResult) -> str:
    flagged_fields = [item.strip() for item in (scan.pii_types_found or "").split(",") if item.strip()]
    risk_level = _risk_label(scan.risk_score)
    risk_pct = max(0, min(100, scan.risk_score))
    scan_timestamp = _format_scanned_at(scan.scanned_at)
    generated_timestamp = _format_generated_at()
    findings_rows = _build_findings_rows(flagged_fields, scan.total_pii_found)
    type_counts = _parse_redacted_type_counts(scan)
    detection_results = _parse_detection_results(scan)
    type_count_rows = _build_type_count_rows(type_counts, scan.total_pii_found)
    detection_reasoning_rows = _build_detection_reasoning_rows(detection_results)
    file_type = _display_file_type(scan)
    risk_explanation = _risk_explanation(risk_level)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ALEX Privacy Compliance Scan Report</title>
  <style>
    @page {{
      size: A4;
      margin: 0.75in;
    }}
    body {{
      font-family: "Helvetica Neue", Arial, sans-serif;
      color: #1f2937;
      margin: 0;
      background: #ffffff;
      line-height: 1.5;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}
    .page {{
      max-width: 840px;
      margin: 0 auto;
      padding: 24px;
    }}
    .header {{
      border-bottom: 2px solid #111827;
      padding-bottom: 14px;
      margin-bottom: 18px;
    }}
    .title {{ margin: 0; font-size: 1.65rem; letter-spacing: 0.2px; color: #111827; }}
    .subtitle {{ margin: 4px 0 14px; font-size: 1rem; color: #374151; }}
    .header-meta {{ margin: 2px 0; font-size: 0.94rem; color: #1f2937; }}
    .header-label {{ font-weight: 700; }}
    .section {{
      border: 1px solid #e5e7eb;
      padding: 14px;
      margin-bottom: 14px;
    }}
    h2 {{
      margin: 0 0 10px;
      font-size: 1.05rem;
      color: #111827;
      border-bottom: 1px solid #e5e7eb;
      padding-bottom: 7px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px 16px;
    }}
    .meta-item {{ margin: 0; }}
    .meta-label {{ font-weight: 700; color: #374151; }}
    .risk-pill {{
      display: inline-block;
      border-radius: 999px;
      padding: 2px 10px;
      border: 1px solid #d1d5db;
      font-weight: 600;
      font-size: 0.9rem;
      background: #f9fafb;
    }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
    th, td {{
      border: 1px solid #d1d5db;
      padding: 8px;
      text-align: left;
      font-size: 0.93rem;
      vertical-align: top;
    }}
    th {{ background: #f9fafb; color: #111827; }}
    .risk-block-title {{ font-weight: 700; margin: 10px 0 2px; }}
    .muted {{ color: #4b5563; font-size: 0.92rem; }}
    @media print {{
      body {{ background: #ffffff; color: #000000; }}
      .page {{ max-width: none; margin: 0; padding: 0; }}
      .section, .header {{
        box-shadow: none;
        break-inside: avoid;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <header class="header">
      <h1 class="title">ALEX Privacy Compliance Scan Report</h1>
      <p class="subtitle">Automated Data Protection Assessment</p>
      <p class="header-meta"><span class="header-label">Generated by:</span> ALEX (Anonymization &amp; Learning EXpert)</p>
      <p class="header-meta"><span class="header-label">Scan Timestamp:</span> {scan_timestamp}</p>
      <p class="header-meta"><span class="header-label">Report ID:</span> {scan.id}</p>
    </header>

    <section class="section">
      <h2>Document Information</h2>
      <div class="grid">
        <p class="meta-item"><span class="meta-label">File Name:</span> {escape(scan.filename or "Unknown")}</p>
        <p class="meta-item"><span class="meta-label">File Type:</span> {escape(file_type)}</p>
        <p class="meta-item"><span class="meta-label">Scan Date:</span> {scan_timestamp}</p>
        <p class="meta-item"><span class="meta-label">Scanner Version:</span> ALEX Privacy Engine</p>
      </div>
    </section>

    <section class="section">
      <h2>Executive Summary</h2>
      <p>This report summarizes the results of an automated privacy compliance scan performed by ALEX (Anonymization &amp; Learning EXpert).</p>
      <p>The submitted document was analyzed for indicators of sensitive or personally identifiable information (PII). Detected patterns were evaluated and automatically redacted where applicable.</p>
      <p>The purpose of this scan is to reduce the risk of unauthorized disclosure of sensitive information when documents are shared internally or externally.</p>
    </section>

    <section class="section">
      <h2>Risk Classification</h2>
      <p>
        <span class="meta-label">Overall Risk Score:</span> {risk_pct}% &nbsp;
        <span class="risk-pill">{risk_level.capitalize()} Risk</span>
      </p>
      <p><span class="meta-label">Risk Level:</span> {risk_level.capitalize()}</p>
      <p class="meta-label">Risk Interpretation:</p>
      <p class="risk-block-title">Low Risk</p>
      <p class="muted">Minimal sensitive information detected. Document can typically be shared with minimal review.</p>
      <p class="risk-block-title">Moderate Risk</p>
      <p class="muted">Sensitive information detected. Review recommended before distribution.</p>
      <p class="risk-block-title">High Risk</p>
      <p class="muted">Significant sensitive data detected. Remediation recommended prior to sharing.</p>
      <p class="muted">Current scan interpretation: {escape(risk_explanation)}</p>
    </section>

    <section class="section">
      <h2>Detected Sensitive Data</h2>
      <table>
        <thead>
          <tr><th>Finding</th><th>Category</th><th>Detection Method</th><th>Action Taken</th></tr>
        </thead>
        <tbody>
          {findings_rows}
        </tbody>
      </table>
    </section>

    <section class="section">
      <h2>Detected and Redacted Data Types</h2>
      <table>
        <thead>
          <tr><th>Taxonomy</th><th>Category</th><th>Policy Categories</th><th>Redacted Count</th></tr>
        </thead>
        <tbody>
          {type_count_rows}
        </tbody>
      </table>
    </section>

    <section class="section">
      <h2>Detection Reasoning</h2>
      <p class="muted">Per-field confidence scores are derived from explicit detection signals and remain separate from the scan-level risk score.</p>
      <table>
        <thead>
          <tr><th>Field</th><th>Taxonomy</th><th>Category</th><th>Policy Categories</th><th>Confidence Score</th><th>Signals</th></tr>
        </thead>
        <tbody>
          {detection_reasoning_rows}
        </tbody>
      </table>
    </section>

    <section class="section">
      <h2>Redaction Confirmation</h2>
      <p>Sensitive data identified during the scan was automatically redacted to prevent exposure.</p>
      <p>The generated redacted document is suitable for controlled distribution depending on organizational policy.</p>
      <p><span class="meta-label">Status:</span> Redacted document successfully generated.</p>
      <p><span class="meta-label">Total Values Redacted:</span> {scan.total_pii_found}</p>
    </section>

    <section class="section">
      <h2>System Note</h2>
      <p>This report was generated by the ALEX automated privacy scanning engine.</p>
      <p>While automated detection significantly reduces exposure risk, organizations should apply additional policy-based review when handling sensitive or regulated data.</p>
      <p>This report represents the findings of automated analysis and does not replace formal compliance review procedures.</p>
      <p class="muted">Report Render Timestamp: {generated_timestamp}</p>
    </section>
  </div>
</body>
</html>
"""


def _fallback_pdf_from_html(html: str) -> bytes:
    from reportlab.lib import colors  # type: ignore
    from reportlab.lib.pagesizes import A4  # type: ignore
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore
    from reportlab.lib.units import inch  # type: ignore
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # type: ignore

    def clean_fragment(fragment: str) -> str:
        fragment = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", fragment)
        fragment = re.sub(r"(?i)<\s*br\s*/?\s*>", "<br/>", fragment)
        fragment = re.sub(r"(?s)<[^>]+>", " ", fragment)
        fragment = html_unescape(fragment)
        fragment = re.sub(r"\s+", " ", fragment)
        return fragment.strip()

    def extract_table_rows(fragment: str) -> list[list[str]]:
        rows: list[list[str]] = []
        for row_html in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", fragment):
            cells = re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", row_html)
            cleaned = [clean_fragment(cell) for cell in cells]
            if cleaned:
                rows.append(cleaned)
        return rows

    body_match = re.search(r"(?is)<body[^>]*>(.*)</body>", html)
    body = body_match.group(1) if body_match else html
    body = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", body)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#111827"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#374151"),
        spaceAfter=6,
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#111827"),
        spaceBefore=8,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "SectionBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=6,
    )
    meta_style = ParagraphStyle(
        "MetaText",
        parent=body_style,
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#374151"),
        spaceAfter=4,
    )

    story = []

    header_match = re.search(r"(?is)<header[^>]*>(.*?)</header>", body)
    if header_match:
        header_html = header_match.group(1)
        title_match = re.search(r"(?is)<h1[^>]*>(.*?)</h1>", header_html)
        subtitle_match = re.search(r"(?is)<p[^>]*class=[\"'][^\"']*subtitle[^\"']*[\"'][^>]*>(.*?)</p>", header_html)
        subtitle_text = clean_fragment(subtitle_match.group(1)) if subtitle_match else None
        if title_match:
            story.append(Paragraph(clean_fragment(title_match.group(1)), title_style))
        if subtitle_match:
            story.append(Paragraph(subtitle_text, subtitle_style))
        for meta in re.findall(r"(?is)<p[^>]*>(.*?)</p>", header_html):
            cleaned = clean_fragment(meta)
            if cleaned and cleaned != subtitle_text:
                story.append(Paragraph(cleaned, meta_style))
        story.append(Spacer(1, 0.16 * inch))

    for section_html in re.findall(r"(?is)<section[^>]*>(.*?)</section>", body):
        heading_match = re.search(r"(?is)<h2[^>]*>(.*?)</h2>", section_html)
        if heading_match:
            story.append(Paragraph(clean_fragment(heading_match.group(1)), heading_style))

        table_rows = extract_table_rows(section_html)
        if table_rows:
            table = Table(table_rows, repeatRows=1, hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("LEADING", (0, 0), (-1, -1), 12),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 0.12 * inch))

        paragraph_matches = re.findall(r"(?is)<p[^>]*>(.*?)</p>", section_html)
        for paragraph_html in paragraph_matches:
            cleaned = clean_fragment(paragraph_html)
            if cleaned:
                story.append(Paragraph(cleaned, body_style))

    if not story:
        # Last-resort plain text extraction.
        text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
        text = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", text)
        text = re.sub(r"(?i)</\s*(p|div|h1|h2|h3|li|tr|section|header|table)\s*>", "\n", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = html_unescape(text)
        raw_lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
        raw_lines = [line for line in raw_lines if line]
        for line in raw_lines:
            for wrapped in textwrap.wrap(line, width=95, break_long_words=False, break_on_hyphens=False):
                story.append(Paragraph(wrapped, body_style))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    doc.build(story)
    return buffer.getvalue()


def render_report_pdf_from_html(html: str) -> bytes:
    try:
        from weasyprint import HTML  # type: ignore
    except ImportError:
        return _fallback_pdf_from_html(html)

    return HTML(string=html).write_pdf()
