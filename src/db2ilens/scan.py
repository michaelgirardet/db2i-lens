"""Scan pipeline and explicit scan.yaml contract (central project artifact)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from db2ilens.connector.ibmi_jdbc import load_jdbc_export
from db2ilens.connector.offline import ColumnMeta, OfflineExport, TableData, load_export
from db2ilens.profiler.sampling import ColumnProfile, profile_table
from db2ilens.rules import RULES
from db2ilens.rules.base import Finding, Severity

SCAN_FORMAT_VERSION = "1.0"

_KNOWN_SEVERITIES: frozenset[str] = frozenset(item.value for item in Severity)
_KNOWN_RULE_IDS: frozenset[str] = frozenset(rule.id for rule in RULES)

_ROOT_REQUIRED_FIELDS: tuple[str, ...] = (
    "version",
    "generated_at",
    "mode",
    "source",
    "schema_name",
    "sample_rows",
    "summary",
    "tables",
)
_SUMMARY_REQUIRED_FIELDS: tuple[str, ...] = (
    "table_count",
    "column_count",
    "finding_count",
    "findings_by_severity",
)
_COLUMN_REQUIRED_FIELDS: tuple[str, ...] = ("name", "metadata", "stats", "findings")
_METADATA_REQUIRED_FIELDS: tuple[str, ...] = (
    "name",
    "data_type",
    "length",
    "scale",
    "implied_scale",
    "nullable",
    "ccsid",
    "comment",
)
_STATS_REQUIRED_FIELDS: tuple[str, ...] = (
    "row_count",
    "null_count",
    "blank_count",
    "distinct_count",
    "min_value",
    "max_value",
    "top_values",
)
_FINDING_REQUIRED_FIELDS: tuple[str, ...] = (
    "rule_id",
    "severity",
    "message",
    "evidence",
    "suggested_fix",
)


@dataclass(frozen=True)
class ScanColumnMetadata:
    """Column metadata serialized into scan.yaml."""

    name: str
    data_type: str
    length: int | None
    scale: int | None
    implied_scale: int | None
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


def scan_jdbc(
    *,
    host: str,
    user: str,
    password: str,
    schema: str,
    sample_rows: int = 5000,
    jar_path: Path | None = None,
    tables: str | None = None,
) -> ScanResult:
    """Profile an IBM i schema over JDBC and run the registered detection rules."""
    export = load_jdbc_export(
        host=host,
        user=user,
        password=password,
        schema=schema,
        sample_rows=sample_rows,
        jar_path=jar_path,
        tables=tables,
    )
    return build_scan_result(
        export=export,
        mode="jdbc",
        source=f"jdbc:as400://{host}/{schema.strip().upper()}",
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
    payload = _yaml_safe(asdict(result))
    out_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def validate_scan_document(document: Any) -> None:
    """
    Validate a loaded scan.yaml mapping against the published contract.

    Raises ValueError on the first structural invariant violation. Consumers
    (report, dbtgen, SaaS) should call this before trusting an external artifact.
    """
    if not isinstance(document, dict):
        raise ValueError("scan.yaml must contain a mapping")

    _require_fields(document, _ROOT_REQUIRED_FIELDS, path="scan")

    version = document["version"]
    if not isinstance(version, str):
        raise ValueError("scan.version must be a string")
    if version != SCAN_FORMAT_VERSION:
        raise ValueError(
            f"scan.version {version!r} is unsupported; "
            f"expected {SCAN_FORMAT_VERSION!r}"
        )

    if not isinstance(document["generated_at"], str):
        raise ValueError("scan.generated_at must be a string")
    if not isinstance(document["mode"], str):
        raise ValueError("scan.mode must be a string")
    if not isinstance(document["source"], str):
        raise ValueError("scan.source must be a string")
    if not isinstance(document["schema_name"], str):
        raise ValueError("scan.schema_name must be a string")
    if not isinstance(document["sample_rows"], int):
        raise ValueError("scan.sample_rows must be an integer")

    summary = document["summary"]
    if not isinstance(summary, dict):
        raise ValueError("scan.summary must be a mapping")
    _require_fields(summary, _SUMMARY_REQUIRED_FIELDS, path="scan.summary")
    for key in ("table_count", "column_count", "finding_count"):
        if not isinstance(summary[key], int):
            raise ValueError(f"scan.summary.{key} must be an integer")

    by_severity = summary["findings_by_severity"]
    if not isinstance(by_severity, dict):
        raise ValueError("scan.summary.findings_by_severity must be a mapping")
    for severity, count in by_severity.items():
        if severity not in _KNOWN_SEVERITIES:
            raise ValueError(
                f"unknown severity {severity!r} in scan.summary.findings_by_severity"
            )
        if not isinstance(count, int):
            raise ValueError(
                f"scan.summary.findings_by_severity[{severity!r}] must be an integer"
            )

    tables = document["tables"]
    if not isinstance(tables, list):
        raise ValueError("scan.tables must be a list")
    for table_index, table in enumerate(tables):
        _validate_table(table, path=f"scan.tables[{table_index}]")


def _require_fields(
    mapping: dict[str, Any],
    required: tuple[str, ...],
    *,
    path: str,
) -> None:
    missing = [field for field in required if field not in mapping]
    if missing:
        raise ValueError(f"{path} missing required field(s): {', '.join(missing)}")


def _validate_table(table: Any, *, path: str) -> None:
    if not isinstance(table, dict):
        raise ValueError(f"{path} must be a mapping")
    _require_fields(table, ("name", "columns"), path=path)
    if not isinstance(table["name"], str):
        raise ValueError(f"{path}.name must be a string")
    columns = table["columns"]
    if not isinstance(columns, list):
        raise ValueError(f"{path}.columns must be a list")
    for column_index, column in enumerate(columns):
        _validate_column(column, path=f"{path}.columns[{column_index}]")


def _validate_column(column: Any, *, path: str) -> None:
    if not isinstance(column, dict):
        raise ValueError(f"{path} must be a mapping")
    _require_fields(column, _COLUMN_REQUIRED_FIELDS, path=path)
    if not isinstance(column["name"], str):
        raise ValueError(f"{path}.name must be a string")

    metadata = column["metadata"]
    if not isinstance(metadata, dict):
        raise ValueError(f"{path}.metadata must be a mapping")
    _require_fields(metadata, _METADATA_REQUIRED_FIELDS, path=f"{path}.metadata")
    if not isinstance(metadata["nullable"], bool):
        raise ValueError(f"{path}.metadata.nullable must be a boolean")

    stats = column["stats"]
    if not isinstance(stats, dict):
        raise ValueError(f"{path}.stats must be a mapping")
    _require_fields(stats, _STATS_REQUIRED_FIELDS, path=f"{path}.stats")
    if not isinstance(stats["top_values"], list):
        raise ValueError(f"{path}.stats.top_values must be a list")

    findings = column["findings"]
    if not isinstance(findings, list):
        raise ValueError(f"{path}.findings must be a list")
    for finding_index, finding in enumerate(findings):
        _validate_finding(finding, path=f"{path}.findings[{finding_index}]")


def _validate_finding(finding: Any, *, path: str) -> None:
    if not isinstance(finding, dict):
        raise ValueError(f"{path} must be a mapping")
    _require_fields(finding, _FINDING_REQUIRED_FIELDS, path=path)

    rule_id = finding["rule_id"]
    if not isinstance(rule_id, str):
        raise ValueError(f"{path}.rule_id must be a string")
    if rule_id not in _KNOWN_RULE_IDS:
        raise ValueError(
            f"{path}.rule_id {rule_id!r} is not registered in RULES "
            f"(known: {sorted(_KNOWN_RULE_IDS)})"
        )

    severity = finding["severity"]
    if not isinstance(severity, str):
        raise ValueError(f"{path}.severity must be a string")
    if severity not in _KNOWN_SEVERITIES:
        raise ValueError(
            f"{path}.severity {severity!r} is unknown "
            f"(allowed: {sorted(_KNOWN_SEVERITIES)})"
        )

    if not isinstance(finding["message"], str):
        raise ValueError(f"{path}.message must be a string")
    if not isinstance(finding["evidence"], dict):
        raise ValueError(f"{path}.evidence must be a mapping")
    suggested_fix = finding["suggested_fix"]
    if suggested_fix is not None and not isinstance(suggested_fix, str):
        raise ValueError(f"{path}.suggested_fix must be a string or null")


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
    evidence = _yaml_safe(dict(finding.evidence))
    if not isinstance(evidence, dict):
        evidence = {}
    return ScanFinding(
        rule_id=finding.rule_id,
        severity=finding.severity.value,
        message=finding.message,
        evidence=evidence,
        suggested_fix=suggested_fix or finding.suggested_fix,
    )


def _to_column_metadata(meta: ColumnMeta) -> ScanColumnMetadata:
    return ScanColumnMetadata(
        name=meta.name,
        data_type=meta.data_type,
        length=meta.length,
        scale=meta.scale,
        implied_scale=meta.implied_scale,
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
    """
    Coerce values to YAML-safe Python builtins.

    JT400/JPype boxed numbers often pass ``isinstance(..., int)`` but are not
    plain ``int`` instances, and ``yaml.safe_dump`` rejects them.
    """
    if value is None:
        return None
    value_type = type(value)
    if value_type is bool or value_type is str:
        return value
    if value_type is int or value_type is float:
        return value
    if isinstance(value, dict):
        return {str(key): _yaml_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_yaml_safe(item) for item in value]
    text = str(value).strip()
    if text == "":
        return text
    try:
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            return int(text)
        return float(text)
    except ValueError:
        return str(value)
