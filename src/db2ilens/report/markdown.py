"""Markdown discovery report generated from a scan.yaml artifact."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_SEVERITY_BADGE = {
    "critical": "🔴 critical",
    "warning": "🟡 warning",
    "info": "🔵 info",
}
_SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def render_markdown(scan_path: Path, out_path: Path) -> None:
    """Render a Markdown discovery report from a scan artifact."""
    data = yaml.safe_load(scan_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("scan.yaml must contain a mapping")
    markdown = build_markdown_report(data)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")


def build_markdown_report(scan: dict[str, Any]) -> str:
    """Build the full Markdown report body from a loaded scan document."""
    summary = scan.get("summary", {})
    findings_by_severity = summary.get("findings_by_severity", {})
    tables = scan.get("tables", [])

    lines: list[str] = []
    lines.extend(_header_section(scan, summary, findings_by_severity))
    lines.append("")
    lines.extend(_table_of_contents(tables))
    lines.append("")

    for table in tables:
        lines.extend(_table_section(table))
        lines.append("")

    lines.extend(_migration_priorities_section(tables))
    lines.append("")
    lines.extend(_decoded_names_appendix(tables))
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _header_section(
    scan: dict[str, Any],
    summary: dict[str, Any],
    findings_by_severity: dict[str, Any],
) -> list[str]:
    return [
        "# Db2iLens discovery report",
        "",
        f"- **Source:** `{scan.get('source', '')}`",
        f"- **Generated at:** {scan.get('generated_at', '')}",
        f"- **Mode:** {scan.get('mode', '')}",
        f"- **Schema:** `{scan.get('schema_name', '')}`",
        "",
        "## Summary",
        "",
        f"- Tables scanned: **{summary.get('table_count', 0)}**",
        f"- Columns scanned: **{summary.get('column_count', 0)}**",
        f"- Issues found: **{summary.get('finding_count', 0)}**",
        (
            "- By severity: "
            f"{_SEVERITY_BADGE['critical']}={findings_by_severity.get('critical', 0)}, "
            f"{_SEVERITY_BADGE['warning']}={findings_by_severity.get('warning', 0)}, "
            f"{_SEVERITY_BADGE['info']}={findings_by_severity.get('info', 0)}"
        ),
    ]


def _table_of_contents(tables: list[dict[str, Any]]) -> list[str]:
    lines = ["## Table of contents", ""]
    for table in tables:
        name = str(table.get("name", ""))
        anchor = f"table-{name.lower()}"
        lines.append(f"- [`{name}`](#{anchor})")
    return lines


def _table_section(table: dict[str, Any]) -> list[str]:
    name = str(table.get("name", ""))
    anchor = f"table-{name.lower()}"
    lines = [
        f'<a id="{anchor}"></a>',
        f"## Table `{name}`",
        "",
        "| Column | Type | Suggested name |",
        "|---|---|---|",
    ]
    for column in table.get("columns", []):
        meta = column.get("metadata", {})
        suggested = _suggested_name_for_column(column)
        type_label = str(meta.get("data_type", ""))
        length = meta.get("length")
        if length is not None:
            type_label = f"{type_label}({length})"
        lines.append(
            f"| `{column.get('name', '')}` | {type_label} | {suggested or '—'} |"
        )

    lines.append("")
    lines.append("### Issues in this table")
    lines.append("")
    issue_lines = _column_finding_details(table)
    if issue_lines:
        lines.extend(issue_lines)
    else:
        lines.append("_No issues detected in this table._")
    return lines


def _column_finding_details(table: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    table_name = str(table.get("name", ""))
    for column in table.get("columns", []):
        findings = column.get("findings", [])
        if not findings:
            continue
        column_name = str(column.get("name", ""))
        lines.append(f"#### `{table_name}.{column_name}`")
        lines.append("")
        for finding in findings:
            severity = str(finding.get("severity", "info"))
            badge = _SEVERITY_BADGE.get(severity, severity)
            rule_id = finding.get("rule_id", "")
            message = finding.get("message", "")
            lines.append(f"- **{rule_id}** — {badge}")
            lines.append(f"  - {message}")
            suggested_fix = finding.get("suggested_fix")
            if suggested_fix:
                if rule_id == "R06" or not _looks_like_sql(str(suggested_fix)):
                    lines.append(f"  - Suggested clearer name: `{suggested_fix}`")
                else:
                    lines.append("  - Suggested cleanup SQL:")
                    lines.append("")
                    lines.append("```sql")
                    lines.append(str(suggested_fix))
                    lines.append("```")
                    lines.append("")
        lines.append("")
    return lines


def _looks_like_sql(text: str) -> bool:
    upper = text.upper()
    return any(
        token in upper
        for token in ("SELECT", "CAST", "TO_DATE", "NULLIF", "CASE", "TRIM", "||")
    )


def _migration_priorities_section(tables: list[dict[str, Any]]) -> list[str]:
    items: list[tuple[int, str, str, str, str]] = []
    for table in tables:
        table_name = str(table.get("name", ""))
        for column in table.get("columns", []):
            column_name = str(column.get("name", ""))
            for finding in column.get("findings", []):
                severity = str(finding.get("severity", "info"))
                items.append(
                    (
                        _SEVERITY_ORDER.get(severity, 99),
                        severity,
                        f"{table_name}.{column_name}",
                        str(finding.get("rule_id", "")),
                        str(finding.get("message", "")),
                    )
                )
    items.sort(key=lambda item: (item[0], item[2], item[3]))

    lines = [
        "## Migration priorities",
        "",
        "Start with the most serious issues. Fix encoding and data-quality "
        "problems before renaming columns.",
        "",
    ]
    if not items:
        lines.append("_No migration priorities identified._")
        return lines

    for _order, severity, ref, rule_id, message in items:
        badge = _SEVERITY_BADGE.get(severity, severity)
        lines.append(f"1. {badge} — `{ref}` ({rule_id}): {message}")
    return lines


def _decoded_names_appendix(tables: list[dict[str, Any]]) -> list[str]:
    rows: list[tuple[str, str, str]] = []
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
                    rows.append((table_name, column_name, suggested))

    lines = [
        "## Decoded column names",
        "",
        "Short IBM i names mapped to clearer names when the abbreviation "
        "dictionary could decode them.",
        "",
        "| Table | Short name | Suggested long name |",
        "|---|---|---|",
    ]
    if not rows:
        lines.append("| — | — | — |")
        return lines
    for table_name, short_name, long_name in sorted(rows):
        lines.append(f"| `{table_name}` | `{short_name}` | `{long_name}` |")
    return lines


def _suggested_name_for_column(column: dict[str, Any]) -> str | None:
    for finding in column.get("findings", []):
        if finding.get("rule_id") != "R06":
            continue
        evidence = finding.get("evidence") or {}
        suggested = evidence.get("suggested_name")
        if isinstance(suggested, str) and suggested:
            return f"`{suggested}`"
    return None
