"""Self-contained HTML discovery report generated from a scan.yaml artifact."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import yaml

from db2ilens.scan import validate_scan_document

_SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}
_SEVERITY_LABELS = ("critical", "warning", "info")

_RULE_BUSINESS_LINES: dict[str, str] = {
    "R01": (
        "Dates stored as plain numbers (YYYYMMDD); "
        "convert before any calendar use."
    ),
    "R02": (
        "Dates locked in IBM century numeric format (CYYMMDD); "
        "convert before any calendar use."
    ),
    "R03": (
        "Character data stored in binary encoding; "
        "must be translated before any export."
    ),
    "R04": (
        "Packed decimals hide an implied scale; "
        "values look like integers until divided."
    ),
    "R05": (
        "Blank strings are used instead of NULL; "
        "clean before joins and exports."
    ),
    "R06": "Short cryptic column name; rename for clarity in analytics models.",
    "R07": "Multiple values packed into one cell; split before relational use.",
    "R08": "Y/N (or 1/0) flag stored as text; cast to boolean in the warehouse.",
    "R09": "Zero used as a missing-value sentinel; treat as NULL in analytics.",
}

# Tokens aligned with .cursor/DESIGN.md (Db2iLens / iSphere).
_CSS = """
:root {
  --color-snow: #F8FAFC;
  --color-white: #FFFFFF;
  --color-ink: #171923;
  --color-slate: #64748B;
  --color-hairline: #E2E8F0;
  --color-border: #CBD5E1;
  --color-system-blue: #2563EB;
  --color-db2-soft: #DBEAFE;
  --color-charcoal: #0B0F1A;
  --color-code-fg: #E2E8F0;
  --color-critical: #DC2626;
  --color-critical-soft: #FEE2E2;
  --color-critical-text: #991B1B;
  --color-warning: #D97706;
  --color-warning-soft: #FEF3C7;
  --color-warning-text: #92400E;
  --color-info: #0284C7;
  --color-info-soft: #E0F2FE;
  --color-info-text: #075985;
  --font-sans: Inter, system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --radius-card: 12px;
  --radius-badge: 6px;
  --radius-code: 12px;
}
*, *::before, *::after { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: var(--font-sans);
  color: var(--color-ink);
  background: var(--color-snow);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}
.wrap {
  max-width: 1080px;
  margin: 0 auto;
  padding: 2.5rem 1.5rem 3.5rem;
}
code, pre, .mono {
  font-family: var(--font-mono);
  font-size: 0.875em;
}
a { color: var(--color-system-blue); text-decoration: none; }
a:hover { text-decoration: underline; text-underline-offset: 2px; }

/* Header */
.brand-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.brand-pill {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  background: var(--color-db2-soft);
  color: var(--color-system-blue);
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.brand-meta {
  color: var(--color-slate);
  font-size: 0.75rem;
  font-weight: 500;
}
header h1 {
  margin: 0 0 0.5rem;
  font-size: 2rem;
  font-weight: 600;
  letter-spacing: -0.035em;
  color: var(--color-ink);
  line-height: 1.15;
}
.meta {
  margin: 0 0 0.75rem;
  color: var(--color-slate);
  font-size: 0.8125rem;
  line-height: 1.6;
}
.meta dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.15rem 0.75rem;
  margin: 0;
}
.meta dt {
  color: var(--color-slate);
  font-weight: 500;
}
.meta dd {
  margin: 0;
  color: var(--color-slate);
}
.meta code { font-size: 0.95em; color: var(--color-ink); }
.summary-line {
  margin: 0 0 1.5rem;
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--color-ink);
}

/* Severity cards */
.cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
  margin: 0 0 2rem;
  align-items: stretch;
}
.card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  background: var(--color-white);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-card);
  padding: 1.1rem 1.15rem;
  min-height: 7rem;
}
.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.card-bar {
  width: 1.5rem;
  height: 3px;
  border-radius: 2px;
  flex-shrink: 0;
}
.card.critical .card-bar { background: var(--color-critical); }
.card.warning .card-bar { background: var(--color-warning); }
.card.info .card-bar { background: var(--color-info); }
.card .value {
  font-size: 2rem;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: var(--color-ink);
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}
.card .hint {
  margin: 0;
  font-size: 0.75rem;
  color: var(--color-slate);
  font-weight: 400;
}

/* Badges */
.badge {
  display: inline-flex;
  align-items: center;
  border-radius: var(--radius-badge);
  padding: 0.15rem 0.5rem;
  font-size: 0.6875rem;
  font-weight: 600;
  line-height: 1.3;
  white-space: nowrap;
}
.badge.critical {
  background: var(--color-critical-soft);
  color: var(--color-critical-text);
}
.badge.warning {
  background: var(--color-warning-soft);
  color: var(--color-warning-text);
}
.badge.info {
  background: var(--color-info-soft);
  color: var(--color-info-text);
}
.badge-print {
  display: none;
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  font-weight: 600;
  color: #334155;
  border: 1px solid #64748B;
  background: #F1F5F9;
  border-radius: var(--radius-badge);
  padding: 0.15rem 0.45rem;
}

/* TOC */
nav.toc {
  background: var(--color-white);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-card);
  padding: 1.25rem 1.35rem;
  margin-bottom: 2.5rem;
}
nav.toc h2 {
  margin: 0 0 0.85rem;
  font-size: 1.125rem;
  font-weight: 600;
  letter-spacing: -0.02em;
}
.toc-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.toc-list a {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.65rem 0.75rem;
  border-radius: 8px;
  border: 1px solid var(--color-hairline);
  background: var(--color-snow);
  text-decoration: none;
  color: inherit;
  transition: background 0.12s ease, border-color 0.12s ease;
}
.toc-list a:hover {
  background: var(--color-db2-soft);
  border-color: #BFDBFE;
  text-decoration: none;
}
.toc-list a:hover .toc-name { color: var(--color-system-blue); }
.toc-name {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-ink);
}
.toc-counts {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  justify-content: flex-end;
}
.toc-summary {
  display: none;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9375rem;
  list-style: none;
}
.toc-summary::-webkit-details-marker { display: none; }

/* Table sections */
section.table-block {
  margin: 0 0 2.5rem;
  padding-top: 0.25rem;
  break-inside: avoid;
}
section.table-block > h2 {
  margin: 0 0 1rem;
  font-size: 1.35rem;
  font-weight: 600;
  letter-spacing: -0.025em;
}
section.table-block > h2 code {
  font-size: 0.95em;
  color: var(--color-system-blue);
}
.panel {
  background: var(--color-white);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-card);
  overflow: hidden;
  margin-bottom: 1.25rem;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}
.data-table th,
.data-table td {
  text-align: left;
  padding: 0.7rem 0.9rem;
  vertical-align: middle;
  border-bottom: 1px solid var(--color-hairline);
  height: 2.75rem;
}
.data-table th {
  background: var(--color-snow);
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-slate);
}
.data-table tbody tr:last-child td { border-bottom: 0; }
.data-table td code {
  font-size: 0.8125rem;
  color: var(--color-ink);
}
.data-table .col-type {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--color-slate);
}

h3.issues-heading {
  margin: 0 0 0.85rem;
  font-size: 1.05rem;
  font-weight: 600;
}

/* Finding cards */
.finding {
  background: var(--color-white);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-card);
  padding: 1.1rem 1.2rem;
  margin: 0 0 0.75rem;
  break-inside: avoid;
  page-break-inside: avoid;
}
.finding-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.75rem;
  margin-bottom: 0.65rem;
}
.finding-target {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-ink);
}
.finding-rule {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-system-blue);
}
.business {
  margin: 0 0 0.35rem;
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--color-ink);
}
.message {
  margin: 0 0 0.65rem;
  font-size: 0.8125rem;
  color: var(--color-slate);
}
.fix-label {
  margin: 0 0 0.35rem;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-slate);
}
pre.sql {
  margin: 0;
  background: var(--color-charcoal);
  color: var(--color-code-fg);
  border-radius: var(--radius-code);
  padding: 0.9rem 1rem;
  overflow-x: auto;
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  line-height: 1.55;
  white-space: pre;
  border: 0;
}
.fix-inline code {
  font-size: 0.8125rem;
}

/* Priorities + decoded */
.priorities, .decoded {
  background: var(--color-white);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-card);
  padding: 1.25rem 1.35rem;
  margin: 0 0 2rem;
}
.priorities { break-before: avoid; }
.priorities h2, .decoded h2 {
  margin: 0 0 0.35rem;
  font-size: 1.25rem;
  font-weight: 600;
  letter-spacing: -0.02em;
}
.section-hint {
  margin: 0 0 1rem;
  color: var(--color-slate);
  font-size: 0.8125rem;
}
.prio-num {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--color-ink);
}
.prio-fix {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--color-slate);
  max-width: 28rem;
  overflow-x: auto;
  white-space: nowrap;
}
.priorities .data-table td { height: auto; padding-top: 0.85rem; padding-bottom: 0.85rem; }
.priorities .data-table pre.sql {
  padding: 0.55rem 0.7rem;
  font-size: 0.75rem;
  max-width: 22rem;
}

.empty { color: var(--color-slate); font-style: italic; font-size: 0.875rem; }

/* Mobile */
@media (max-width: 720px) {
  .wrap { padding: 1.25rem 1rem 2.5rem; }
  header h1 { font-size: 1.5rem; }
  .meta dl {
    grid-template-columns: 1fr;
    gap: 0.1rem;
  }
  .meta dt { font-size: 0.6875rem; text-transform: uppercase; letter-spacing: 0.04em; }
  .cards {
    grid-template-columns: 1fr;
    gap: 0.5rem;
  }
  .card {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    min-height: 0;
    padding: 0.75rem 0.9rem;
    gap: 0.75rem;
  }
  .card-top { flex: 1; }
  .card .value {
    font-size: 1.5rem;
    margin: 0;
  }
  .card .hint { display: none; }
  .card-bar { display: none; }

  nav.toc { padding: 0.85rem 1rem; }
  nav.toc h2 { display: none; }
  .toc-summary { display: block; margin-bottom: 0.5rem; }
  .toc-summary::before { content: "▸ "; color: var(--color-system-blue); }
  nav.toc[open] .toc-summary::before { content: "▾ "; }
  .toc-list a {
    flex-direction: column;
    align-items: flex-start;
  }

  .panel { overflow: visible; }
  .data-table, .data-table thead, .data-table tbody,
  .data-table th, .data-table td, .data-table tr { display: block; }
  .data-table thead { display: none; }
  .data-table tr {
    border: 1px solid var(--color-hairline);
    border-radius: 8px;
    margin-bottom: 0.5rem;
    padding: 0.55rem 0.7rem;
    background: var(--color-white);
  }
  .data-table td {
    border: 0;
    height: auto;
    padding: 0.2rem 0;
  }
  .data-table td::before {
    content: attr(data-label);
    display: block;
    font-size: 0.625rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--color-slate);
    margin-bottom: 0.1rem;
  }
  .priorities, .decoded { padding: 1rem; }
  .prio-fix { max-width: 100%; }
  .priorities .data-table pre.sql { max-width: 100%; }
}

/* Print / PDF */
@media print {
  @page {
    size: A4;
    margin: 14mm 12mm 16mm;
  }
  body {
    background: #fff;
    color: #000;
    font-size: 10.5pt;
  }
  .wrap { max-width: none; padding: 0; }
  a { color: inherit; text-decoration: none; }
  .brand-pill { border: 1px solid #94A3B8; background: #fff; color: #000; }
  .cards {
    grid-template-columns: repeat(3, 1fr);
    break-inside: avoid;
    page-break-inside: avoid;
  }
  .card { box-shadow: none; min-height: 0; padding: 0.6rem 0.7rem; }
  .badge { display: none; }
  .badge-print { display: inline-flex; }
  .toc-list a {
    break-inside: avoid;
    background: #fff;
    border-color: #CBD5E1;
  }
  .toc-list a:hover { background: #fff; }
  nav.toc { break-after: avoid; }
  .priorities {
    break-before: avoid;
    page-break-before: avoid;
  }
  .finding, .panel, .priorities, .decoded, section.table-block {
    break-inside: avoid;
    page-break-inside: avoid;
  }
  pre.sql {
    background: #111827 !important;
    color: #F9FAFB !important;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
    white-space: pre-wrap;
    overflow: visible;
  }
  .print-footer {
    display: block;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    font-size: 8pt;
    color: #64748B;
    border-top: 1px solid #E2E8F0;
    padding-top: 4pt;
  }
}
@media screen {
  .print-footer { display: none; }
}
""".strip()


def render_html(scan_path: Path, out_path: Path) -> None:
    """Render a self-contained HTML discovery report from a scan artifact."""
    data = yaml.safe_load(scan_path.read_text(encoding="utf-8"))
    validate_scan_document(data)
    payload = build_html_report(data)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload, encoding="utf-8")


def build_html_report(scan: dict[str, Any]) -> str:
    """Build the full HTML document from a loaded scan mapping."""
    summary = scan.get("summary", {})
    by_severity = summary.get("findings_by_severity", {})
    tables = scan.get("tables", [])

    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Db2iLens discovery report</title>",
        f"<style>{_CSS}</style>",
        "</head>",
        "<body>",
        '<div class="wrap">',
        "<header>",
        '<div class="brand-row">',
        '<span class="brand-pill">Db2iLens</span>',
        '<span class="brand-meta">iSphere</span>',
        "</div>",
        "<h1>Discovery report</h1>",
        '<div class="meta">',
        "<dl>",
        f"<dt>Source</dt><dd><code>{_esc(scan.get('source', ''))}</code></dd>",
        f"<dt>Generated</dt><dd>{_esc(scan.get('generated_at', ''))}</dd>",
        f"<dt>Mode</dt><dd>{_esc(scan.get('mode', ''))}</dd>",
        f"<dt>Schema</dt><dd><code>{_esc(scan.get('schema_name', ''))}</code></dd>",
        "</dl>",
        "</div>",
        "</header>",
        '<p class="summary-line">',
        f"{_esc(summary.get('table_count', 0))} tables  ·  "
        f"{_esc(summary.get('column_count', 0))} columns  ·  "
        f"{_esc(summary.get('finding_count', 0))} issues",
        "</p>",
        '<div class="cards" role="group" aria-label="Findings by severity">',
        _severity_card(
            "critical",
            by_severity.get("critical", 0),
            "Blocking data issues",
        ),
        _severity_card(
            "warning",
            by_severity.get("warning", 0),
            "Review before migration",
        ),
        _severity_card(
            "info",
            by_severity.get("info", 0),
            "Naming and modelling hints",
        ),
        "</div>",
        _toc(tables),
        # Priorities sit after the summary/TOC so print page 1 surfaces them
        # for steering-committee reading (refinement over Markdown appendix order).
        _migration_priorities_section(tables),
    ]

    for table in tables:
        parts.append(_table_section(table))

    parts.append(_decoded_names_section(tables))
    parts.extend(
        [
            "</div>",
            '<div class="print-footer" aria-hidden="true">'
            "Db2iLens discovery report · read-only scan · iSphere"
            "</div>",
            "</body>",
            "</html>",
            "",
        ]
    )
    return "\n".join(parts)


def _severity_card(severity: str, count: Any, hint: str) -> str:
    return (
        f'<div class="card {severity}">'
        '<div class="card-top">'
        f"{_badge(severity)}"
        '<span class="card-bar" aria-hidden="true"></span>'
        "</div>"
        f'<div class="value">{_esc(count)}</div>'
        f'<p class="hint">{_esc(hint)}</p>'
        "</div>"
    )


def _table_severity_counts(table: dict[str, Any]) -> dict[str, int]:
    counts = {"critical": 0, "warning": 0, "info": 0}
    for column in table.get("columns", []):
        for finding in column.get("findings", []):
            severity = str(finding.get("severity", "info"))
            if severity in counts:
                counts[severity] += 1
    return counts


def _toc(tables: list[dict[str, Any]]) -> str:
    items: list[str] = []
    for table in tables:
        name = str(table.get("name", ""))
        anchor = f"table-{name.lower()}"
        counts = _table_severity_counts(table)
        chips = "".join(
            f'<span class="badge {sev}">{sev} {counts[sev]}</span>'
            f'<span class="badge-print" aria-hidden="true">'
            f"{_print_severity_mark(sev)} {sev} {counts[sev]}</span>"
            for sev in _SEVERITY_LABELS
            if counts[sev] > 0
        )
        items.append(
            "<li>"
            f'<a href="#{anchor}">'
            f'<span class="toc-name">{_esc(name)}</span>'
            f'<span class="toc-counts">{chips}</span>'
            "</a>"
            "</li>"
        )
    return (
        '<details class="toc-wrap" open>'
        '<summary class="toc-summary">Tables in this scan</summary>'
        '<nav class="toc" aria-label="Tables">'
        "<h2>Tables in this scan</h2>"
        f'<ul class="toc-list">{"".join(items)}</ul>'
        "</nav>"
        "</details>"
    )


def _table_section(table: dict[str, Any]) -> str:
    name = str(table.get("name", ""))
    anchor = f"table-{name.lower()}"
    rows: list[str] = []
    for column in table.get("columns", []):
        meta = column.get("metadata", {})
        suggested = _suggested_name_for_column(column)
        type_label = str(meta.get("data_type", ""))
        length = meta.get("length")
        if length is not None:
            type_label = f"{type_label}({length})"
        rows.append(
            "<tr>"
            f'<td data-label="Column"><code>{_esc(column.get("name", ""))}</code></td>'
            f'<td class="col-type" data-label="Type">{_esc(type_label)}</td>'
            f'<td data-label="Suggested name">{suggested or "—"}</td>'
            "</tr>"
        )

    findings_html = _column_finding_details(table)
    if not findings_html:
        findings_html = '<p class="empty">No issues detected in this table.</p>'

    return (
        f'<section class="table-block" id="{anchor}">'
        f"<h2>Table <code>{_esc(name)}</code></h2>"
        '<div class="panel">'
        '<table class="data-table">'
        "<thead><tr><th>Column</th><th>Type</th><th>Suggested name</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "</div>"
        '<h3 class="issues-heading">Issues in this table</h3>'
        f"{findings_html}"
        "</section>"
    )


def _column_finding_details(table: dict[str, Any]) -> str:
    chunks: list[str] = []
    table_name = str(table.get("name", ""))
    for column in table.get("columns", []):
        findings = column.get("findings", [])
        if not findings:
            continue
        column_name = str(column.get("name", ""))
        for finding in findings:
            severity = str(finding.get("severity", "info"))
            rule_id = str(finding.get("rule_id", ""))
            message = str(finding.get("message", ""))
            business = _RULE_BUSINESS_LINES.get(rule_id)
            body = [
                f'<article class="finding finding-{severity}">',
                '<div class="finding-head">',
                f'<span class="finding-target">'
                f"{_esc(table_name)}.{_esc(column_name)}</span>",
                f'<span class="finding-rule">{_esc(rule_id)}</span>',
                _badge(severity),
                _print_badge(severity),
                "</div>",
            ]
            if business:
                body.append(f'<p class="business">{_esc(business)}</p>')
            body.append(f'<p class="message">{_esc(message)}</p>')
            suggested_fix = finding.get("suggested_fix")
            if suggested_fix:
                if rule_id == "R06" or not _looks_like_sql(str(suggested_fix)):
                    body.append('<p class="fix-label">Suggested clearer name</p>')
                    body.append(
                        f'<p class="fix-inline">'
                        f"<code>{_esc(suggested_fix)}</code></p>"
                    )
                else:
                    body.append('<p class="fix-label">Suggested cleanup SQL</p>')
                    body.append(f'<pre class="sql">{_esc(suggested_fix)}</pre>')
            body.append("</article>")
            chunks.append("\n".join(body))
    return "\n".join(chunks)


def _migration_priorities_section(tables: list[dict[str, Any]]) -> str:
    items: list[tuple[int, str, str, str, str, str]] = []
    for table in tables:
        table_name = str(table.get("name", ""))
        for column in table.get("columns", []):
            column_name = str(column.get("name", ""))
            for finding in column.get("findings", []):
                severity = str(finding.get("severity", "info"))
                rule_id = str(finding.get("rule_id", ""))
                fix = finding.get("suggested_fix")
                fix_text = str(fix) if fix else "—"
                items.append(
                    (
                        _SEVERITY_ORDER.get(severity, 99),
                        table_name,
                        column_name,
                        rule_id,
                        severity,
                        fix_text,
                    )
                )
    items.sort(key=lambda item: (item[0], item[1], item[2], item[3]))

    if not items:
        body = '<p class="empty">No migration priorities identified.</p>'
    else:
        rows: list[str] = []
        for index, (_order, table_name, column_name, rule_id, severity, fix) in enumerate(
            items, start=1
        ):
            ref = f"{table_name}.{column_name}"
            if fix != "—" and _looks_like_sql(fix):
                fix_cell = f'<pre class="sql">{_esc(fix)}</pre>'
            elif fix != "—":
                fix_cell = f'<span class="prio-fix">{_esc(fix)}</span>'
            else:
                fix_cell = "—"
            rows.append(
                "<tr>"
                f'<td data-label="#"><span class="prio-num">{index}</span></td>'
                f'<td data-label="Table.Column"><code>{_esc(ref)}</code></td>'
                f'<td data-label="Rule"><code>{_esc(rule_id)}</code></td>'
                f'<td data-label="Severity">{_badge(severity)}{_print_badge(severity)}</td>'
                f'<td data-label="Fix">{fix_cell}</td>'
                "</tr>"
            )
        body = (
            '<div class="panel">'
            '<table class="data-table">'
            "<thead><tr>"
            "<th>#</th><th>Table.Column</th><th>Rule</th>"
            "<th>Severity</th><th>Fix</th>"
            "</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody>"
            "</table>"
            "</div>"
        )

    return (
        '<section class="priorities">'
        "<h2>Migration priorities</h2>"
        '<p class="section-hint">'
        "Start with the most serious issues. Fix encoding and data-quality "
        "problems before renaming columns."
        "</p>"
        f"{body}"
        "</section>"
    )


def _decoded_names_section(tables: list[dict[str, Any]]) -> str:
    rows_data: list[tuple[str, str, str]] = []
    for table in tables:
        table_name = str(table.get("name", ""))
        for column in table.get("columns", []):
            column_name = str(column.get("name", ""))
            for finding in column.get("findings", []):
                if finding.get("rule_id") != "R06":
                    continue
                evidence = finding.get("evidence") or {}
                suggested = evidence.get("suggested_name")
                if isinstance(suggested, str) and suggested:
                    rows_data.append((table_name, column_name, suggested))

    if not rows_data:
        body_rows = (
            '<tr><td data-label="Table">—</td>'
            '<td data-label="Short name">—</td>'
            '<td data-label="Suggested long name">—</td></tr>'
        )
    else:
        body_rows = "".join(
            "<tr>"
            f'<td data-label="Table"><code>{_esc(table_name)}</code></td>'
            f'<td data-label="Short name"><code>{_esc(short_name)}</code></td>'
            f'<td data-label="Suggested long name"><code>{_esc(long_name)}</code></td>'
            "</tr>"
            for table_name, short_name, long_name in sorted(rows_data)
        )

    return (
        '<section class="decoded">'
        "<h2>Decoded column names</h2>"
        '<p class="section-hint">'
        "Short IBM i names mapped to clearer names when the abbreviation "
        "dictionary could decode them."
        "</p>"
        '<div class="panel">'
        '<table class="data-table">'
        "<thead><tr><th>Table</th><th>Short name</th>"
        "<th>Suggested long name</th></tr></thead>"
        f"<tbody>{body_rows}</tbody>"
        "</table>"
        "</div>"
        "</section>"
    )


def _suggested_name_for_column(column: dict[str, Any]) -> str | None:
    for finding in column.get("findings", []):
        if finding.get("rule_id") != "R06":
            continue
        evidence = finding.get("evidence") or {}
        suggested = evidence.get("suggested_name")
        if isinstance(suggested, str) and suggested:
            return f"<code>{_esc(suggested)}</code>"
    return None


def _badge(severity: str) -> str:
    label = html.escape(severity)
    css = severity if severity in _SEVERITY_ORDER else "info"
    return f'<span class="badge {css}">{label}</span>'


def _print_severity_mark(severity: str) -> str:
    marks = {"critical": "■■", "warning": "▣▣", "info": "□□"}
    return marks.get(severity, "□□")


def _print_badge(severity: str) -> str:
    css = severity if severity in _SEVERITY_ORDER else "info"
    mark = _print_severity_mark(css)
    return (
        f'<span class="badge-print" aria-hidden="true">'
        f"{mark} {html.escape(css)}</span>"
    )


def _looks_like_sql(text: str) -> bool:
    upper = text.upper()
    return any(
        token in upper
        for token in ("SELECT", "CAST", "TO_DATE", "NULLIF", "CASE", "TRIM", "||")
    )


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)
