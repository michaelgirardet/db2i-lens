"""Column sampling and statistics for offline / JDBC profiles."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from db2ilens.connector.offline import TableData


@dataclass(frozen=True)
class ColumnProfile:
    """Per-column sample statistics."""

    table: str
    column: str
    data_type: str
    nullable: bool
    ccsid: int | None
    length: int | None
    scale: int | None
    implied_scale: int | None
    row_count: int
    null_count: int
    blank_count: int
    distinct_count: int
    min_value: Any
    max_value: Any
    top_values: list[tuple[Any, int]]
    sample_values: list[Any]


def profile_table(table: TableData, sample_rows: int | None = None) -> list[ColumnProfile]:
    """Profile every column of a table."""
    return [profile_column(table, column.name, sample_rows=sample_rows) for column in table.columns]


def profile_column(
    table: TableData,
    column_name: str,
    sample_rows: int | None = None,
) -> ColumnProfile:
    """Compute distinct / null / blank / min / max / top-values for one column."""
    meta = table.column_map().get(column_name)
    if meta is None:
        raise KeyError(f"column {column_name!r} not found in table {table.name!r}")

    sampled = _sample_rows(table.rows, sample_rows)
    values = [row.get(column_name) for row in sampled]

    null_count = sum(1 for value in values if value is None)
    blank_count = sum(1 for value in values if _is_blank(value))
    non_null = [value for value in values if value is not None]
    distinct_count = len(set(_hashable(value) for value in non_null))

    comparable = [value for value in non_null if not _is_blank(value)]
    min_value: Any = None
    max_value: Any = None
    if comparable:
        try:
            min_value = min(comparable)
            max_value = max(comparable)
        except TypeError:
            as_text = [str(value) for value in comparable]
            min_value = min(as_text)
            max_value = max(as_text)

    counts = Counter(_hashable(value) for value in non_null)
    top_values = [
        (_restore_value(value_key), count)
        for value_key, count in counts.most_common()
    ]

    return ColumnProfile(
        table=table.name,
        column=column_name,
        data_type=meta.data_type,
        nullable=meta.nullable,
        ccsid=meta.ccsid,
        length=meta.length,
        scale=meta.scale,
        implied_scale=meta.implied_scale,
        row_count=len(sampled),
        null_count=null_count,
        blank_count=blank_count,
        distinct_count=distinct_count,
        min_value=min_value,
        max_value=max_value,
        top_values=top_values,
        sample_values=list(non_null),
    )


def _sample_rows(
    rows: list[dict[str, Any]],
    sample_rows: int | None,
) -> list[dict[str, Any]]:
    if sample_rows is None or sample_rows < 0:
        return list(rows)
    return list(rows[:sample_rows])


def _is_blank(value: object) -> bool:
    return isinstance(value, str) and value.strip() == ""


def _hashable(value: object) -> object:
    if isinstance(value, (list, dict, set)):
        return repr(value)
    return value


def _restore_value(value_key: object) -> object:
    return value_key
