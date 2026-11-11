"""Offline connector for CSV exports described by schema.yaml."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class OfflineExportError(ValueError):
    """Raised when an offline export directory cannot be loaded."""


@dataclass(frozen=True)
class ColumnMeta:
    """Column metadata from schema.yaml (SYSCOLUMNS2-like)."""

    name: str
    data_type: str
    length: int | None = None
    scale: int | None = None
    implied_scale: int | None = None
    nullable: bool = True
    ccsid: int | None = None
    comment: str | None = None


@dataclass
class TableData:
    """One table: metadata + in-memory rows."""

    name: str
    columns: list[ColumnMeta]
    rows: list[dict[str, Any]] = field(default_factory=list)

    def column_map(self) -> dict[str, ColumnMeta]:
        return {column.name: column for column in self.columns}


@dataclass
class OfflineExport:
    """Offline export loaded from a directory of CSV + schema.yaml."""

    schema_name: str
    tables: dict[str, TableData]
    source_path: Path


def load_export(path: Path) -> OfflineExport:
    """Load tables from an offline export directory (CSV + schema.yaml)."""
    root = Path(path)
    schema_path = root / "schema.yaml"
    if not schema_path.is_file():
        raise OfflineExportError(f"schema.yaml not found under {root}")

    raw = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise OfflineExportError("schema.yaml must be a mapping")

    schema_name = str(raw.get("schema", ""))
    tables_raw = raw.get("tables")
    if not isinstance(tables_raw, dict) or not tables_raw:
        raise OfflineExportError("schema.yaml must define a non-empty tables mapping")

    tables: dict[str, TableData] = {}
    for table_name, table_def in tables_raw.items():
        if not isinstance(table_def, dict):
            raise OfflineExportError(f"invalid table definition for {table_name}")
        columns = _parse_columns(table_name, table_def.get("columns"))
        csv_path = root / f"{table_name}.csv"
        if not csv_path.is_file():
            raise OfflineExportError(f"missing CSV for table {table_name}: {csv_path}")
        rows = _load_csv_rows(csv_path, columns)
        tables[str(table_name)] = TableData(name=str(table_name), columns=columns, rows=rows)

    return OfflineExport(schema_name=schema_name, tables=tables, source_path=root)


def _parse_columns(table_name: str, columns_raw: object) -> list[ColumnMeta]:
    if not isinstance(columns_raw, dict) or not columns_raw:
        raise OfflineExportError(f"table {table_name} must define columns")

    columns: list[ColumnMeta] = []
    for name, meta in columns_raw.items():
        if not isinstance(meta, dict):
            raise OfflineExportError(f"invalid column metadata for {table_name}.{name}")
        columns.append(
            ColumnMeta(
                name=str(name),
                data_type=str(meta.get("data_type", "VARCHAR")),
                length=_optional_int(meta.get("length")),
                scale=_optional_int(meta.get("scale")),
                implied_scale=_optional_int(meta.get("implied_scale")),
                nullable=bool(meta.get("nullable", True)),
                ccsid=_optional_int(meta.get("ccsid")),
                comment=_optional_str(meta.get("comment")),
            )
        )
    return columns


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    raise OfflineExportError(f"expected int-compatible value, got {type(value).__name__}")


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _load_csv_rows(csv_path: Path, columns: list[ColumnMeta]) -> list[dict[str, Any]]:
    column_by_name = {column.name: column for column in columns}
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise OfflineExportError(f"CSV has no header: {csv_path}")
        rows: list[dict[str, Any]] = []
        for raw_row in reader:
            typed: dict[str, Any] = {}
            for field_name, raw_value in raw_row.items():
                if field_name is None:
                    continue
                meta = column_by_name.get(field_name)
                typed[field_name] = _coerce_value(raw_value, meta)
            rows.append(typed)
        return rows


def _coerce_value(raw_value: str | None, meta: ColumnMeta | None) -> Any:
    if raw_value is None:
        return None
    if meta is None:
        return raw_value
    data_type = meta.data_type.upper()
    if data_type in {"DECIMAL", "NUMERIC", "INTEGER", "SMALLINT", "BIGINT"}:
        text = raw_value.strip()
        if text == "":
            return None
        if meta.scale and meta.scale > 0:
            return float(text)
        return int(text)
    return raw_value
