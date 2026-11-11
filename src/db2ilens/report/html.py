"""Self-contained HTML discovery report generated from a scan.yaml artifact."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import yaml

from db2ilens.scan import validate_scan_document

_SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}

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

_CSS = """
:root {
  --bg: #f7f5f1;
  --ink: #1c1b19;
  --muted: #5c574f;
  --card: #ffffff;
  --line: #ddd6c8;
  --critical: #b42318;
  --critical-bg: #fef3f2;
  --warning: #b54708;
  --warning-bg: #fffaeb;
  --info: #175cd3;
  --info-bg: #eff8ff;
  --sql-bg: #ece8e1;
  --accent: #0f3d3e;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  color: var(--ink);
  background:
    radial-gradient(circle at top left, #efe8dc 0%, transparent 45%),
    linear-gradient(180deg, #fbf9f5 0%, var(--bg) 100%);
  line-height: 1.5;
}
.wrap { max-width: 960px; margin: 0 auto; padding: 1.5rem 1rem 3rem; }
header h1 { margin: 0 0 0.35rem; font-size: 1.85rem; color: var(--accent); }
.meta { color: var(--muted); font-size: 0.95rem; margin: 0 0 1.25rem; }
.meta code { font-size: 0.9em; }
.cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
  margin: 1rem 0 1.5rem;
}
.card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.9rem 1rem;
}
.card .label { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.04em; }
.card .value { font-size: 1.8rem; font-weight: 700; margin-top: 0.2rem; }
.card.critical { border-color: #f3b0a8; background: var(--critical-bg); }
.card.critical .label, .card.critical .value { color: var(--critical); }
.card.warning { border-color: #f7c948; background: var(--warning-bg); }
.card.warning .label, .card.warning .value { color: var(--warning); }
.card.info { border-color: #b2ddff; background: var(--info-bg); }
.card.info .label, .card.info .value { color: var(--info); }
.summary-line { margin: 0 0 1rem; color: var(--muted); }
nav.toc {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.9rem 1rem;
  margin-bottom: 1.5rem;
}
nav.toc h2 { margin: 0 0 0.5rem; font-size: 1.05rem; }
nav.toc ul { margin: 0; padding-left: 1.1rem; }
nav.toc a { color: var(--accent); text-decoration: none; }
nav.toc a:hover { text-decoration: underline; }
section.table-block {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 1rem;
  margin: 0 0 1.25rem;
}
section.table-block h2 { margin: 0 0 0.75rem; font-size: 1.25rem; }
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.95rem;
}
th, td {
  border-bottom: 1px solid var(--line);
  text-align: left;
  padding: 0.45rem 0.4rem;
  vertical-align: top;
}
th { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.03em; color: var(--muted); }
.badge {
  display: inline-block;
  border-radius: 999px;
  padding: 0.1rem 0.55rem;
  font-size: 0.78rem;
  font-weight: 600;
}
.badge.critical { background: var(--critical-bg); color: var(--critical); }
.badge.warning { background: var(--warning-bg); color: var(--warning); }
.badge.info { background: var(--info-bg); color: var(--info); }
.finding { margin: 0.9rem 0; padding-top: 0.4rem; border-top: 1px dashed var(--line); }
.finding h4 { margin: 0 0 0.35rem; font-size: 1rem; }
.business { margin: 0.35rem 0; color: var(--ink); }
.message { margin: 0.25rem 0; color: var(--muted); font-size: 0.92rem; }
pre.sql {
  margin: 0.5rem 0 0;
  background: var(--sql-bg);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 0.7rem 0.8rem;
  overflow-x: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.85rem;
  white-space: pre-wrap;
}
.priorities, .decoded {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 1rem;
  margin: 0 0 1.25rem;
}
.priorities h2, .decoded h2 { margin: 0 0 0.35rem; }
.hint { color: var(--muted); margin: 0 0 0.8rem; font-size: 0.92rem; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
@media (max-width: 720px) {
  .cards { grid-template-columns: 1fr; }
  .wrap { padding: 1rem 0.75rem 2rem; }
  table, thead, tbody, th, td, tr { display: block; }
  thead { display: none; }
  tr {
    border: 1px solid var(--line);
    border-radius: 8px;
    margin-bottom: 0.6rem;
    padding: 0.4rem 0.5rem;
  }
  td {
    border: 0;
    padding: 0.2rem 0;
  }
  td::before {
    content: attr(data-label);
    display: block;
    font-size: 0.72rem;
    text-transform: uppercase;
    color: var(--muted);
  }
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
        "<h1>Db2iLens discovery report</h1>",
        '<p class="meta">',
        f"Source: <code>{_esc(scan.get('source', ''))}</code><br>",
        f"Generated at: {_esc(scan.get('generated_at', ''))}<br>",
        f"Mode: {_esc(scan.get('mode', ''))} · Schema: "
        f"<code>{_esc(scan.get('schema_name', ''))}</code>",
        "</p>",
        "</header>",
        '<p class="summary-line">',
        f"Tables scanned: <strong>{_esc(summary.get('table_count', 0))}</strong> · ",
        f"Columns: <strong>{_esc(summary.get('column_count', 0))}</strong> · ",
        f"Issues: <strong>{_esc(summary.get('finding_count', 0))}</strong>",
        "</p>",
        '<div class="cards" role="group" aria-label="Findings by severity">',
        _severity_card("critical", by_severity.get("critical", 0)),
        _severity_card("warning", by_severity.get("warning", 0)),
        _severity_card("info", by_severity.get("info", 0)),
        "</div>",
        _toc(tables),
    ]

    for table in tables:
        parts.append(_table_section(table))

    parts.append(_migration_priorities_section(tables))
    parts.append(_decoded_names_section(tables))
    parts.extend(["</div>", "</body>", "</html>", ""])
    return "\n".join(parts)


def _severity_card(severity: str, count: Any) -> str:
    return (
        f'<div class="card {severity}">'
        f'<div class="label">{severity}</div>'
        f'<div class="value">{_esc(count)}</div>'
        "</div>"
    )


def _toc(tables: list[dict[str, Any]]) -> str:
    items = []
    for table in tables:
        name = str(table.get("name", ""))
        anchor = f"table-{name.lower()}"
        items.append(f'<li><a href="#{anchor}"><code>{_esc(name)}</code></a></li>')
    return (
        '<nav class="toc" aria-label="Tables">'
        "<h2>Tables</h2>"
        f"<ul>{''.join(items)}</ul>"
        "</nav>"
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
            f'<td data-label="Type">{_esc(type_label)}</td>'
            f'<td data-label="Suggested name">{suggested or "—"}</td>'
            "</tr>"
        )

    findings_html = _column_finding_details(table)
    if not findings_html:
        findings_html = "<p><em>No issues detected in this table.</em></p>"

    return (
        f'<section class="table-block" id="{anchor}">'
        f"<h2>Table <code>{_esc(name)}</code></h2>"
        "<table>"
        "<thead><tr><th>Column</th><th>Type</th><th>Suggested name</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "<h3>Issues in this table</h3>"
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
        chunks.append(f"<h3><code>{_esc(table_name)}.{_esc(column_name)}</code></h3>")
        for finding in findings:
            severity = str(finding.get("severity", "info"))
            rule_id = str(finding.get("rule_id", ""))
            message = str(finding.get("message", ""))
            business = _RULE_BUSINESS_LINES.get(rule_id)
            body = [
                '<div class="finding">',
                f"<h4>{_esc(rule_id)} — {_badge(severity)}</h4>",
            ]
            if business:
                body.append(f'<p class="business">{_esc(business)}</p>')
            body.append(f'<p class="message">{_esc(message)}</p>')
            suggested_fix = finding.get("suggested_fix")
            if suggested_fix:
                if rule_id == "R06" or not _looks_like_sql(str(suggested_fix)):
                    body.append(
                        "<p>Suggested clearer name: "
                        f"<code>{_esc(suggested_fix)}</code></p>"
                    )
                else:
                    body.append("<p>Suggested cleanup SQL:</p>")
                    body.append(f'<pre class="sql">{_esc(suggested_fix)}</pre>')
            body.append("</div>")
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
        body = "<p><em>No migration priorities identified.</em></p>"
    else:
        rows: list[str] = []
        for index, (_order, table_name, column_name, rule_id, severity, fix) in enumerate(
            items, start=1
        ):
            business = _RULE_BUSINESS_LINES.get(rule_id, "")
            fix_cell = (
                f'<pre class="sql">{_esc(fix)}</pre>'
                if fix != "—" and _looks_like_sql(fix)
                else f"<code>{_esc(fix)}</code>"
                if fix != "—"
                else "—"
            )
            rows.append(
                "<tr>"
                f'<td data-label="#">{index}</td>'
                f'<td data-label="Table"><code>{_esc(table_name)}</code></td>'
                f'<td data-label="Column"><code>{_esc(column_name)}</code></td>'
                f'<td data-label="Rule">{_esc(rule_id)}</td>'
                f'<td data-label="Severity">{_badge(severity)}</td>'
                f'<td data-label="Business impact">{_esc(business)}</td>'
                f'<td data-label="Fix">{fix_cell}</td>'
                "</tr>"
            )
        body = (
            "<table>"
            "<thead><tr>"
            "<th>#</th><th>Table</th><th>Column</th><th>Rule</th>"
            "<th>Severity</th><th>Business impact</th><th>Fix</th>"
            "</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody>"
            "</table>"
        )

    return (
        '<section class="priorities">'
        "<h2>Migration priorities</h2>"
        '<p class="hint">'
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
        '<p class="hint">'
        "Short IBM i names mapped to clearer names when the abbreviation "
        "dictionary could decode them."
        "</p>"
        "<table>"
        "<thead><tr><th>Table</th><th>Short name</th>"
        "<th>Suggested long name</th></tr></thead>"
        f"<tbody>{body_rows}</tbody>"
        "</table>"
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


def _looks_like_sql(text: str) -> bool:
    upper = text.upper()
    return any(
        token in upper
        for token in ("SELECT", "CAST", "TO_DATE", "NULLIF", "CASE", "TRIM", "||")
    )


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)
