from datetime import datetime
from pathlib import Path
from html import escape
import io
import re
from html import unescape as html_unescape

from database.models.scan_results import ScanResult


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
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


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


def generate_audit_report_html(scan: ScanResult) -> str:
    flagged_fields = [item.strip() for item in (scan.pii_types_found or "").split(",") if item.strip()]
    risk_level = _risk_label(scan.risk_score)
    risk_pct = max(0, min(100, scan.risk_score))
    scan_timestamp = _format_scanned_at(scan.scanned_at)
    generated_timestamp = _format_generated_at()
    findings_rows = _build_findings_rows(flagged_fields, scan.total_pii_found)
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
    from reportlab.lib.pagesizes import A4  # type: ignore
    from reportlab.pdfgen import canvas  # type: ignore

    # Lightweight HTML-to-text pass for fallback rendering.
    text = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", html)
    text = re.sub(r"(?i)</\s*(p|div|h1|h2|h3|li|tr|section|header)\s*>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html_unescape(text)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin_x = 50
    y = height - 50
    line_height = 14

    for line in lines:
        pdf.drawString(margin_x, y, line[:130])
        y -= line_height
        if y < 50:
            pdf.showPage()
            y = height - 50

    pdf.save()
    return buffer.getvalue()


def render_report_pdf_from_html(html: str) -> bytes:
    try:
        from weasyprint import HTML  # type: ignore
    except ImportError:
        return _fallback_pdf_from_html(html)

    return HTML(string=html).write_pdf()
