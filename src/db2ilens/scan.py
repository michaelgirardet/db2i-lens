"""Scan pipeline and explicit scan.yaml contract (central project artifact)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from db2ilens.connector.offline import ColumnMeta, OfflineExport, TableData, load_export
from db2ilens.profiler.sampling import ColumnProfile, profile_table
from db2ilens.rules import RULES
from db2ilens.rules.base import Finding

SCAN_FORMAT_VERSION = "1.0"


@dataclass(frozen=True)
class ScanColumnMetadata:
    """Column metadata serialized into scan.yaml."""

    name: str
    data_type: str
    length: int | None
    scale: int | None
    nullable: bool
    ccsid: int | None
    comment: str | None


@dataclass(frozen=True)
class ScanColumnStats:
    """Sample statistics for one column."""

    row_count: int
    null_count: int
    blank_count: int
    distinct_count: int
    min_value: Any
    max_value: Any
    top_values: list[dict[str, Any]]


@dataclass(frozen=True)
class ScanFinding:
    """One rule finding attached to a column."""

    rule_id: str
    severity: str
    message: str
    evidence: dict[str, Any]
    suggested_fix: str | None


@dataclass(frozen=True)
class ScanColumnResult:
    """Per-column scan payload: metadata + stats + findings."""

    name: str
    metadata: ScanColumnMetadata
    stats: ScanColumnStats
    findings: list[ScanFinding] = field(default_factory=list)


@dataclass(frozen=True)
class ScanTableResult:
    """Per-table scan payload."""

    name: str
    columns: list[ScanColumnResult]


@dataclass(frozen=True)
class ScanSummary:
    """Aggregate counters for the first line of a discovery report."""

    table_count: int
    column_count: int
    finding_count: int
    findings_by_severity: dict[str, int]


@dataclass(frozen=True)
class ScanResult:
    """
    Explicit contract for scan.yaml.

    Consumed later by report / dbtgen / SaaS. Prefer this schema over ad-hoc dicts.
    """

    version: str
    generated_at: str
    mode: str
    source: str
    schema_name: str
    sample_rows: int
    summary: ScanSummary
    tables: list[ScanTableResult]


def scan_offline(path: Path, sample_rows: int = 5000) -> ScanResult:
    """Profile an offline export and run the registered detection rules."""
    export = load_export(path)
    return build_scan_result(
        export=export,
        mode="offline",
        source=str(path.resolve()),
        sample_rows=sample_rows,
    )


def build_scan_result(
    export: OfflineExport,
    mode: str,
    source: str,
    sample_rows: int,
) -> ScanResult:
    """Build a ScanResult from an already loaded export."""
    tables: list[ScanTableResult] = []
    findings_by_severity = {"critical": 0, "warning": 0, "info": 0}
    finding_count = 0
    column_count = 0

    for table_name in sorted(export.tables):
        table = export.tables[table_name]
        column_results = _scan_table(table, sample_rows=sample_rows)
        for column in column_results:
            column_count += 1
            for finding in column.findings:
                finding_count += 1
                findings_by_severity[finding.severity] = (
                    findings_by_severity.get(finding.severity, 0) + 1
                )
        tables.append(ScanTableResult(name=table.name, columns=column_results))

    return ScanResult(
        version=SCAN_FORMAT_VERSION,
        generated_at=datetime.now(UTC).isoformat(),
        mode=mode,
        source=source,
        schema_name=export.schema_name,
        sample_rows=sample_rows,
        summary=ScanSummary(
            table_count=len(tables),
            column_count=column_count,
            finding_count=finding_count,
            findings_by_severity=findings_by_severity,
        ),
        tables=tables,
    )


def write_scan_yaml(result: ScanResult, out_path: Path) -> None:
    """Serialize a ScanResult to YAML."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(result)
    out_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _scan_table(table: TableData, sample_rows: int) -> list[ScanColumnResult]:
    profiles = {profile.column: profile for profile in profile_table(table, sample_rows)}
    results: list[ScanColumnResult] = []
    for column_meta in table.columns:
        profile = profiles[column_meta.name]
        findings = _run_rules(profile)
        results.append(
            ScanColumnResult(
                name=column_meta.name,
                metadata=_to_column_metadata(column_meta),
                stats=_to_column_stats(profile),
                findings=findings,
            )
        )
    return results


def _run_rules(profile: ColumnProfile) -> list[ScanFinding]:
    findings: list[ScanFinding] = []
    for rule in RULES:
        for finding in rule.detect(profile):
            findings.append(_to_scan_finding(finding, rule.fix(finding)))
    return findings


def _to_scan_finding(finding: Finding, suggested_fix: str | None) -> ScanFinding:
    return ScanFinding(
        rule_id=finding.rule_id,
        severity=finding.severity.value,
        message=finding.message,
        evidence=dict(finding.evidence),
        suggested_fix=suggested_fix or finding.suggested_fix,
    )


def _to_column_metadata(meta: ColumnMeta) -> ScanColumnMetadata:
    return ScanColumnMetadata(
        name=meta.name,
        data_type=meta.data_type,
        length=meta.length,
        scale=meta.scale,
        nullable=meta.nullable,
        ccsid=meta.ccsid,
        comment=meta.comment,
    )


def _to_column_stats(profile: ColumnProfile) -> ScanColumnStats:
    return ScanColumnStats(
        row_count=profile.row_count,
        null_count=profile.null_count,
        blank_count=profile.blank_count,
        distinct_count=profile.distinct_count,
        min_value=_yaml_safe(profile.min_value),
        max_value=_yaml_safe(profile.max_value),
        top_values=[
            {"value": _yaml_safe(value), "count": count}
            for value, count in profile.top_values
        ],
    )


def _yaml_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
