"""JDBC connector for Db2 for i via JayDeBeApi + JT400 (read-only)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from db2ilens.connector.offline import ColumnMeta, OfflineExport, TableData

# All SQL for IBM i lives in this module (AGENTS.md).
_SQL_LIST_TABLES = """
SELECT TABLE_NAME
FROM QSYS2.SYSTABLES
WHERE TABLE_SCHEMA = ?
  AND TABLE_TYPE = 'T'
ORDER BY TABLE_NAME
"""

_SQL_LIST_COLUMNS = """
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    LENGTH,
    NUMERIC_SCALE,
    IS_NULLABLE,
    CCSID,
    COLUMN_TEXT
FROM QSYS2.SYSCOLUMNS2
WHERE TABLE_SCHEMA = ?
  AND TABLE_NAME = ?
ORDER BY ORDINAL_POSITION
"""


class JdbcConfigError(ValueError):
    """Invalid JDBC / JT400 configuration."""


class JdbcQueryError(RuntimeError):
    """Failure while querying Db2 for i over JDBC."""


def resolve_password(*, password_stdin: bool) -> str:
    """
    Resolve the IBM i password.

    Prefer DB2ILENS_PASSWORD; otherwise read one line from stdin when
    ``password_stdin`` is true. Never accept CLI password arguments.
    """
    env_password = os.environ.get("DB2ILENS_PASSWORD")
    if env_password is not None and env_password != "":
        return env_password
    if password_stdin:
        line = sys.stdin.readline()
        if line == "":
            raise JdbcConfigError(
                "no password on stdin; set DB2ILENS_PASSWORD or pipe a password"
            )
        return line.rstrip("\n")
    raise JdbcConfigError(
        "password required: set DB2ILENS_PASSWORD or pass --password-stdin"
    )


def resolve_jt400_jar(explicit: Path | None = None) -> Path:
    """
    Locate the JT400 JDBC driver JAR.

    Order: explicit path → JT400_JAR env → ./jt400.jar → ~/.db2ilens/jt400.jar.
    The JAR is never committed; see docs/JT400.md and scripts/fetch_jt400.sh.
    """
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    env_jar = os.environ.get("JT400_JAR")
    if env_jar:
        candidates.append(Path(env_jar))
    candidates.append(Path.cwd() / "jt400.jar")
    candidates.append(Path.home() / ".db2ilens" / "jt400.jar")

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise JdbcConfigError(
        "JT400 JAR not found. Set JT400_JAR or run scripts/fetch_jt400.sh "
        "(see docs/JT400.md)."
    )


def normalize_ibm_data_type(data_type: str) -> str:
    """Normalize QSYS2.SYSCOLUMNS2 DATA_TYPE labels to offline-compatible names."""
    raw = data_type.strip().upper()
    aliases = {
        "CHARACTER": "CHAR",
        "CHARACTER VARYING": "VARCHAR",
        "CHAR VARYING": "VARCHAR",
    }
    return aliases.get(raw, raw)


def map_syscolumns2_row(row: dict[str, Any]) -> ColumnMeta:
    """
    Map one QSYS2.SYSCOLUMNS2 row to ColumnMeta (offline-compatible).

    ``COLUMN_TEXT`` becomes ``comment`` (drives R06 suppression).
    ``CCSID`` is preserved as-is (drives R03).
    ``implied_scale`` is always None — not a catalog attribute on IBM i.
    """
    name = str(row["COLUMN_NAME"]).strip()
    data_type = normalize_ibm_data_type(str(row.get("DATA_TYPE", "VARCHAR")))
    length = _optional_int(row.get("LENGTH"))
    scale = _optional_int(row.get("NUMERIC_SCALE"))
    if data_type not in {"DECIMAL", "NUMERIC"} and scale == 0:
        # Non-numeric types often report SCALE 0; treat as absent.
        scale = None
    nullable = str(row.get("IS_NULLABLE", "Y")).strip().upper() in {"Y", "YES", "1"}
    ccsid = _optional_int(row.get("CCSID"))
    comment = _optional_comment(row.get("COLUMN_TEXT"))
    return ColumnMeta(
        name=name,
        data_type=data_type,
        length=length,
        scale=scale,
        implied_scale=None,
        nullable=nullable,
        ccsid=ccsid,
        comment=comment,
    )


def connect(
    *,
    host: str,
    user: str,
    password: str,
    schema: str,
    jar_path: Path | None = None,
    login_timeout_seconds: int = 15,
) -> Any:
    """Open a read-only JDBC connection to IBM i (JT400)."""
    try:
        import jaydebeapi  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - dependency declared
        raise JdbcConfigError(
            "jaydebeapi is required for JDBC mode; install project dependencies"
        ) from exc

    jar = resolve_jt400_jar(jar_path)
    # libraries= sets the default library list; prompt=false avoids GUI auth.
    url = (
        f"jdbc:as400://{host}"
        f";libraries={schema}"
        f";prompt=false"
        f";errors=full"
        f";date format=iso"
        f";login timeout={login_timeout_seconds}"
    )
    try:
        connection = jaydebeapi.connect(
            "com.ibm.as400.access.AS400JDBCDriver",
            url,
            [user, password],
            str(jar),
        )
    except Exception as exc:  # noqa: BLE001 - JDBC driver raises Java exceptions
        raise JdbcQueryError(f"failed to connect to jdbc:as400://{host}: {exc}") from exc
    return connection


def load_jdbc_export(
    *,
    host: str,
    user: str,
    password: str,
    schema: str,
    sample_rows: int = 5000,
    jar_path: Path | None = None,
    login_timeout_seconds: int = 15,
) -> OfflineExport:
    """
    Load schema metadata + sampled rows into the same Offline export structure.

    SELECT-only: SYSTABLES / SYSCOLUMNS2 for catalog, FETCH FIRST for samples.
    """
    connection = connect(
        host=host,
        user=user,
        password=password,
        schema=schema,
        jar_path=jar_path,
        login_timeout_seconds=login_timeout_seconds,
    )
    schema_name = schema.strip().upper()
    try:
        table_names = _list_tables(connection, schema_name)
        tables: dict[str, TableData] = {}
        for table_name in table_names:
            columns = _list_columns(connection, schema_name, table_name)
            rows = _sample_rows(
                connection,
                schema=schema_name,
                table=table_name,
                columns=columns,
                sample_rows=sample_rows,
            )
            tables[table_name] = TableData(name=table_name, columns=columns, rows=rows)
    finally:
        connection.close()

    return OfflineExport(
        schema_name=schema_name,
        tables=tables,
        source_path=Path(f"jdbc:as400://{host}/{schema_name}"),
    )


def _list_tables(connection: Any, schema: str) -> list[str]:
    rows = _fetch_all(connection, _SQL_LIST_TABLES, [schema])
    names: list[str] = []
    for row in rows:
        name = row.get("TABLE_NAME")
        if name is None and len(row) == 1:
            name = next(iter(row.values()))
        if name is not None:
            names.append(str(name).strip())
    return names


def _list_columns(connection: Any, schema: str, table: str) -> list[ColumnMeta]:
    rows = _fetch_all(connection, _SQL_LIST_COLUMNS, [schema, table])
    return [map_syscolumns2_row(row) for row in rows]


def _sample_rows(
    connection: Any,
    *,
    schema: str,
    table: str,
    columns: list[ColumnMeta],
    sample_rows: int,
) -> list[dict[str, Any]]:
    if not columns:
        return []
    # Identifiers come from the system catalog (quoted for safety).
    col_sql = ", ".join(_quote_ident(column.name) for column in columns)
    sql = (
        f"SELECT {col_sql} "
        f"FROM {_quote_ident(schema)}.{_quote_ident(table)} "
        f"FETCH FIRST {int(sample_rows)} ROWS ONLY"
    )
    raw_rows = _fetch_all(connection, sql, [])
    typed_rows: list[dict[str, Any]] = []
    column_by_name = {column.name.upper(): column for column in columns}
    for raw in raw_rows:
        typed: dict[str, Any] = {}
        for key, value in raw.items():
            meta = column_by_name.get(str(key).upper())
            name = meta.name if meta is not None else str(key)
            typed[name] = _coerce_jdbc_value(value, meta)
        typed_rows.append(typed)
    return typed_rows


def _fetch_all(connection: Any, sql: str, params: list[Any]) -> list[dict[str, Any]]:
    cursor = connection.cursor()
    try:
        cursor.execute(sql, params)
        description = cursor.description or []
        names = [str(col[0]) for col in description]
        rows: list[dict[str, Any]] = []
        for values in cursor.fetchall():
            rows.append({names[index]: values[index] for index in range(len(names))})
        return rows
    except Exception as exc:  # noqa: BLE001 - surface Java/JDBC failures clearly
        raise JdbcQueryError(f"JDBC query failed: {exc}") from exc
    finally:
        cursor.close()


def _quote_ident(name: str) -> str:
    cleaned = name.replace('"', "")
    return f'"{cleaned}"'


def _coerce_jdbc_value(value: Any, meta: ColumnMeta | None) -> Any:
    if value is None:
        return None
    if meta is None:
        return _java_to_python(value)
    data_type = meta.data_type.upper()
    if data_type in {"DECIMAL", "NUMERIC", "INTEGER", "SMALLINT", "BIGINT"}:
        number = _java_to_python(value)
        if number is None:
            return None
        if meta.scale and meta.scale > 0:
            return float(number)
        return int(number)
    return str(value)


def _java_to_python(value: Any) -> Any:
    """Convert JT400/JPype scalars to plain Python builtins."""
    if value is None:
        return None
    value_type = type(value)
    if value_type is bool or value_type is str:
        return value
    if value_type is int or value_type is float:
        return value
    text = str(value).strip()
    if text == "":
        return None
    try:
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            return int(text)
        return float(text)
    except ValueError:
        return str(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    converted = _java_to_python(value)
    if converted is None:
        return None
    if type(converted) is bool:
        return int(converted)
    if type(converted) is int:
        return converted
    if type(converted) is float:
        return int(converted)
    text = str(converted).strip()
    if text == "":
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _optional_comment(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
