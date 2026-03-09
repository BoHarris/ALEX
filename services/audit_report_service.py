from datetime import datetime
from html import escape

from database.models.scan_results import ScanResult


def _risk_label(risk_score: int) -> str:
    if risk_score >= 70:
        return "high"
    if risk_score >= 40:
        return "moderate"
    return "low"


def _risk_explanation(risk_label: str) -> str:
    explanations = {
        "low": "Limited sensitive content detected. Routine handling is typically sufficient.",
        "moderate": "Sensitive content detected. A documented review is recommended before sharing.",
        "high": "Significant sensitive content detected. Additional handling controls are recommended.",
    }
    return explanations.get(risk_label, "Risk level guidance is not available.")


def _format_scanned_at(scanned_at: datetime | None) -> str:
    if not scanned_at:
        return "Unknown"
    return scanned_at.strftime("%Y-%m-%d %H:%M:%S")


def _format_generated_at() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def generate_audit_report_html(scan: ScanResult) -> str:
    flagged_fields = [item.strip() for item in (scan.pii_types_found or "").split(",") if item.strip()]
    risk_level = _risk_label(scan.risk_score)
    risk_explanation = _risk_explanation(risk_level)
    risk_pct = scan.risk_score

    if scan.total_pii_found > 0:
        finding_summary = (
            "This scan identified potentially sensitive information in the uploaded document. "
            f"Redactions were applied to {scan.total_pii_found} value(s) in the exported file."
        )
    else:
        finding_summary = (
            "This scan did not identify values that required redaction under the current detection settings."
        )

    detected_section_title = "Flagged Fields"
    if flagged_fields:
        detected_section_title = "Detected PII Categories / Flagged Fields"

    rows_html = "".join(
        f"<tr><td>{idx}</td><td>{escape(field)}</td><td>Detected during scan and marked for redaction</td></tr>"
        for idx, field in enumerate(flagged_fields, start=1)
    )
    if not rows_html:
        rows_html = "<tr><td colspan='3'>No PII categories or flagged fields were recorded for this scan.</td></tr>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ALEX Compliance Audit Report</title>
  <style>
    :root {{ color-scheme: light; }}
    body {{
      font-family: "Segoe UI", Arial, sans-serif;
      color: #1f2937;
      margin: 0;
      background: #f3f4f6;
      line-height: 1.5;
    }}
    .page {{
      max-width: 960px;
      margin: 24px auto;
      padding: 0 18px 24px;
    }}
    .header {{
      background: #111827;
      color: #f9fafb;
      border-radius: 10px;
      padding: 20px;
      margin-bottom: 16px;
    }}
    .title {{ margin: 0; font-size: 1.55rem; letter-spacing: 0.2px; }}
    .subtitle {{ margin: 6px 0 0; font-size: 1rem; color: #d1d5db; }}
    .generated {{ margin-top: 8px; font-size: 0.88rem; color: #9ca3af; }}
    .section {{
      background: #ffffff;
      border: 1px solid #e5e7eb;
      border-radius: 10px;
      padding: 16px;
      margin-bottom: 12px;
    }}
    h2 {{
      margin: 0 0 10px;
      font-size: 1.03rem;
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
    .meta-label {{ font-weight: 600; color: #374151; }}
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
    .muted {{ color: #6b7280; font-size: 0.9rem; }}
    .footer-note {{ margin-top: 8px; }}
    @media print {{
      body {{ background: #fff; color: #000; }}
      .page {{ max-width: none; margin: 0; padding: 0; }}
      .section, .header {{
        border-radius: 0;
        box-shadow: none;
        break-inside: avoid;
      }}
      a {{ color: inherit; text-decoration: none; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <header class="header">
      <h1 class="title">ALEX Privacy Scan Report</h1>
      <p class="subtitle">Plain-English Audit Report</p>
      <p class="generated">Report generated: {_format_generated_at()}</p>
    </header>

    <section class="section">
      <h2>File Summary</h2>
      <div class="grid">
        <p class="meta-item"><span class="meta-label">Original Filename:</span> {escape(scan.filename or "Unknown")}</p>
        <p class="meta-item"><span class="meta-label">Scan Date/Time:</span> {_format_scanned_at(scan.scanned_at)}</p>
        <p class="meta-item"><span class="meta-label">Redacted Output Reference:</span> {escape(scan.redacted_file_path or "Not available")}</p>
        <p class="meta-item"><span class="meta-label">Values Redacted:</span> {scan.total_pii_found}</p>
      </div>
    </section>

    <section class="section">
      <h2>Executive Summary</h2>
      <p>{finding_summary}</p>
      <p>
        This report is intended to support review, documentation, and compliance-oriented workflows.
      </p>
    </section>

    <section class="section">
      <h2>Risk Assessment</h2>
      <p>
        <span class="meta-label">Risk Score:</span> {risk_pct}% &nbsp;
        <span class="risk-pill">{risk_level.capitalize()} Risk</span>
      </p>
      <p>
        The assigned risk score indicates the likelihood that the file contains Personally Identifiable Information (PII).
      </p>
      <p class="muted">{escape(risk_explanation)}</p>
    </section>

    <section class="section">
      <h2>{escape(detected_section_title)}</h2>
      <table>
        <thead>
          <tr><th>#</th><th>Detected Item</th><th>Assessment</th></tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </section>

    <section class="section">
      <h2>Redaction Confirmation</h2>
      <p>
        Total values redacted: <strong>{scan.total_pii_found}</strong>.
        The exported redacted file reflects the redactions identified by this scan.
      </p>
    </section>

    <section class="section">
      <h2>Report Note</h2>
      <p class="footer-note">
        This report is generated from stored scan metadata in ALEX and is suitable for internal review,
        audit documentation, and compliance-oriented recordkeeping.
      </p>
      <p class="muted">
        This HTML format is designed to print cleanly and can be used as the source for future PDF export.
      </p>
    </section>
  </div>
</body>
</html>
"""


def render_report_pdf_from_html(html: str) -> bytes:
    try:
        from weasyprint import HTML  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "PDF export requires the 'weasyprint' package. Install with: pip install weasyprint"
        ) from exc

    return HTML(string=html).write_pdf()
