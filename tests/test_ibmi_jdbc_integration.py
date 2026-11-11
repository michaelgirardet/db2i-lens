"""Live PUB400 JDBC checks — skipped unless PUB400_USER/PUB400_PASSWORD are set."""

from __future__ import annotations

import os

import pytest

from db2ilens.connector.ibmi_jdbc import JdbcConfigError, load_jdbc_export

_HAS_PUB400 = bool(
    (os.environ.get("PUB400_USER") or os.environ.get("DB2ILENS_USER"))
    and (os.environ.get("PUB400_PASSWORD") or os.environ.get("DB2ILENS_PASSWORD"))
)


@pytest.mark.integration
@pytest.mark.skipif(not _HAS_PUB400, reason="PUB400_USER/PUB400_PASSWORD not configured")
def test_jdbc_load_export_returns_offline_compatible_structure() -> None:
    user = os.environ.get("PUB400_USER") or os.environ["DB2ILENS_USER"]
    password = os.environ.get("PUB400_PASSWORD") or os.environ["DB2ILENS_PASSWORD"]
    schema = os.environ.get("PUB400_SCHEMA") or os.environ.get("DB2ILENS_SCHEMA") or user
    host = os.environ.get("PUB400_HOST", "pub400.com")

    try:
        export = load_jdbc_export(
            host=host,
            user=user,
            password=password,
            schema=schema,
            sample_rows=100,
        )
    except JdbcConfigError as exc:
        pytest.skip(f"JT400 / JDBC not usable in this environment: {exc}")

    assert export.schema_name == schema.upper() or export.schema_name == schema
    assert export.tables, "expected at least one table in PUB400 library"
    sample_table = next(iter(export.tables.values()))
    assert sample_table.columns
    first = sample_table.columns[0]
    assert first.name
    assert first.data_type
    # Structure parity with offline ColumnMeta fields.
    assert hasattr(first, "ccsid")
    assert hasattr(first, "comment")
    assert hasattr(first, "implied_scale")
