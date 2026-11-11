"""Build structured Jinja context from a validated scan document (no SQL here)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FindingView:
    rule_id: str
    severity: str
    message: str
    suggested_fix: str | None


@dataclass
class ColumnView:
    name: str
    data_type: str
    length: int | None
    nullable: bool
    output_name: str
    findings: list[FindingView] = field(default_factory=list)
    cleaning_rules: list[str] = field(default_factory=list)
    implied_scale: int | None = None
    accepted_values: list[str] = field(default_factory=list)
    is_key: bool = False
    relationship_targets: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class RelationshipView:
    column: str
    output_name: str
    from_table: str
    from_model: str
    to_table: str
    to_model: str


@dataclass
class TableView:
    name: str
    model_name: str
    staging_name: str
    columns: list[ColumnView]
    findings: list[FindingView]


@dataclass
class ProjectContext:
    target: str
    schema_name: str
    source_name: str
    project_name: str
    profile_name: str
    tables: list[TableView]
    relationships: list[RelationshipView]


def build_project_context(scan: dict[str, Any], target: str) -> ProjectContext:
    schema_name = str(scan.get("schema_name", "source"))
    source_name = _slug(schema_name)
    tables_raw = scan.get("tables", [])
    assert isinstance(tables_raw, list)

    tables = [_table_view(table) for table in tables_raw]
    relationships = _detect_relationships(tables)
    table_by_name = {table.name: table for table in tables}
    for rel in relationships:
        child = table_by_name[rel.from_table]
        parent = table_by_name[rel.to_table]
        child_col = _column_by_name(child, rel.column)
        parent_col = _column_by_name(parent, rel.column)
        # Align renamed FK/PK names so relationship tests resolve.
        child_col.output_name = parent_col.output_name
        child_col.is_key = True
        parent_col.is_key = True
        child_col.relationship_targets.append(
            (parent.model_name, parent_col.output_name)
        )

    for table in tables:
        for column in table.columns:
            if column.name.endswith("ID") and not column.nullable:
                column.is_key = True

    return ProjectContext(
        target=target.lower(),
        schema_name=schema_name,
        source_name=source_name,
        project_name="db2ilens_generated",
        profile_name="db2ilens",
        tables=tables,
        relationships=relationships,
    )


def _table_view(table: dict[str, Any]) -> TableView:
    name = str(table["name"])
    model_name = _slug(name)
    columns: list[ColumnView] = []
    findings: list[FindingView] = []
    for column in table.get("columns", []):
        view = _column_view(column)
        columns.append(view)
        findings.extend(view.findings)
    return TableView(
        name=name,
        model_name=model_name,
        staging_name=f"stg_{model_name}",
        columns=columns,
        findings=findings,
    )


def _column_view(column: dict[str, Any]) -> ColumnView:
    name = str(column["name"])
    meta = column.get("metadata") or {}
    stats = column.get("stats") or {}
    finding_views = [
        FindingView(
            rule_id=str(item.get("rule_id", "")),
            severity=str(item.get("severity", "info")),
            message=str(item.get("message", "")),
            suggested_fix=(
                str(item["suggested_fix"])
                if item.get("suggested_fix") is not None
                else None
            ),
        )
        for item in column.get("findings", [])
    ]
    rule_ids = [item.rule_id for item in finding_views]
    output_name = name.lower()
    for item in column.get("findings", []):
        if item.get("rule_id") != "R06":
            continue
        evidence = item.get("evidence") or {}
        suggested = evidence.get("suggested_name") or item.get("suggested_fix")
        if isinstance(suggested, str) and suggested.strip():
            output_name = _slug(suggested)
            break

    cleaning: list[str] = [
        rule_id
        for rule_id in ("R03", "R05", "R08", "R01", "R02", "R04")
        if rule_id in rule_ids
    ]
    accepted = _accepted_values(name, stats, rule_ids)
    implied = meta.get("implied_scale")
    if implied is None and "R04" in rule_ids:
        for item in column.get("findings", []):
            if item.get("rule_id") == "R04":
                evidence = item.get("evidence") or {}
                implied = evidence.get("implied_scale")
    return ColumnView(
        name=name,
        data_type=str(meta.get("data_type", "VARCHAR")),
        length=meta.get("length") if isinstance(meta.get("length"), int) else None,
        nullable=bool(meta.get("nullable", True)),
        output_name=output_name,
        findings=finding_views,
        cleaning_rules=cleaning,
        implied_scale=int(implied) if isinstance(implied, int) else None,
        accepted_values=accepted,
    )


def _accepted_values(
    column_name: str,
    stats: dict[str, Any],
    rule_ids: list[str],
) -> list[str]:
    top_values = stats.get("top_values") or []
    values: list[str] = []
    for entry in top_values:
        if not isinstance(entry, dict):
            continue
        value = entry.get("value")
        if value is None:
            continue
        text = str(value).strip()
        if text:
            values.append(text)
    # Explicit ORDSTS / short status codes from the mini-ERP contract.
    if column_name.upper() == "ORDSTS" or (
        values and all(len(value) == 1 for value in values) and len(values) <= 10
    ):
        return sorted(set(values))
    _ = rule_ids
    return []


def _detect_relationships(tables: list[TableView]) -> list[RelationshipView]:
    by_column: dict[str, list[TableView]] = {}
    for table in tables:
        for column in table.columns:
            by_column.setdefault(column.name, []).append(table)

    relationships: list[RelationshipView] = []
    for column_name, owners in by_column.items():
        if len(owners) < 2:
            continue
        parent = min(
            owners,
            key=lambda table: (
                _column_index(table, column_name),
                len(table.columns),
                table.name,
            ),
        )
        parent_col = _column_by_name(parent, column_name)
        for child in owners:
            if child.name == parent.name:
                continue
            child_col = _column_by_name(child, column_name)
            relationships.append(
                RelationshipView(
                    column=column_name,
                    output_name=child_col.output_name,
                    from_table=child.name,
                    from_model=child.model_name,
                    to_table=parent.name,
                    to_model=parent.model_name,
                )
            )
            # Prefer parent rename if child somehow differs.
            if parent_col.output_name != child_col.output_name:
                relationships[-1] = RelationshipView(
                    column=column_name,
                    output_name=parent_col.output_name,
                    from_table=child.name,
                    from_model=child.model_name,
                    to_table=parent.name,
                    to_model=parent.model_name,
                )
    return relationships


def _column_index(table: TableView, column_name: str) -> int:
    for index, column in enumerate(table.columns):
        if column.name == column_name:
            return index
    return 999


def _column_by_name(table: TableView, column_name: str) -> ColumnView:
    for column in table.columns:
        if column.name == column_name:
            return column
    raise KeyError(column_name)


def _slug(value: str) -> str:
    text = value.strip().lower().replace("-", "_").replace(" ", "_")
    return "".join(char if char.isalnum() or char == "_" else "_" for char in text)
