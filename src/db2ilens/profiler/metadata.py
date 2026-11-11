"""Table/column metadata profiling from an offline export."""

from __future__ import annotations

from db2ilens.connector.offline import ColumnMeta, OfflineExport, TableData


def profile_metadata(export: OfflineExport) -> dict[str, list[ColumnMeta]]:
    """Return column metadata keyed by table name."""
    return {name: list(table.columns) for name, table in export.tables.items()}


def table_column_names(table: TableData) -> list[str]:
    """Return ordered column names for a table."""
    return [column.name for column in table.columns]
