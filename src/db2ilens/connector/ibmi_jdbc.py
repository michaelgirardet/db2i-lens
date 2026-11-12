"""JDBC connector for Db2 for i via JayDeBeApi + JT400 (read-only)."""

from __future__ import annotations

import csv
import os
import re
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

_SQL_LIST_TABLES_LIKE = """
SELECT TABLE_NAME
FROM QSYS2.SYSTABLES
WHERE TABLE_SCHEMA = ?
  AND TABLE_TYPE = 'T'
  AND TABLE_NAME LIKE ?
ORDER BY TABLE_NAME
"""

_SQL_LIST_TABLES_EQ = """
SELECT TABLE_NAME
FROM QSYS2.SYSTABLES
WHERE TABLE_SCHEMA = ?
  AND TABLE_TYPE = 'T'
  AND TABLE_NAME = ?
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

# Exact name list vs SQL LIKE pattern for --tables / PUB400_TABLES.
TablesFilter = tuple[str, ...] | str


class JdbcConfigError(ValueError):
    """Invalid JDBC / JT400 configuration."""


class JdbcQueryError(RuntimeError):
    """Failure while querying Db2 for i over JDBC."""


_JDBC_SOURCE_RE = re.compile(
    r"^jdbc:as400://(?P<host>[^/;]+)(?:/(?P<schema>[^/;]+))?",
    re.IGNORECASE,
)


def parse_jdbc_source(source: str) -> tuple[str, str]:
    """Parse ``jdbc:as400://host/SCHEMA`` scan.source into (host, schema)."""
    match = _JDBC_SOURCE_RE.match(source.strip())
    if match is None:
        raise JdbcConfigError(f"unsupported JDBC source: {source!r}")
    host = match.group("host")
    schema = match.group("schema")
    if not schema:
        raise JdbcConfigError(f"JDBC source missing schema: {source!r}")
    return host, schema.upper()


def parse_tables_filter(raw: str | None) -> TablesFilter | None:
    """
    Parse a ``--tables`` / ``PUB400_TABLES`` filter.

    - ``None`` / blank → no filter (all tables in the schema).
    - Comma-separated list → exact table names (case-insensitive → UPPER).
    - Value containing ``%`` → SQL ``LIKE`` pattern (UPPER).
    - Otherwise → single exact table name.
    """
    if raw is None:
        return None
    text = raw.strip()
    if text == "":
        return None
    if "," in text:
        names = tuple(
            part.strip().upper() for part in text.split(",") if part.strip()
        )
        return names or None
    if "%" in text:
        return text.upper()
    return (text.upper(),)


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


def build_jdbc_url(
    host: str,
    schema: str,
    *,
    login_timeout_seconds: int = 15,
) -> str:
    """
    Build a JT400 JDBC URL for read-only catalog + sample access.

    ``translate binary=true`` is required so CCSID 65535 CHAR columns are
    converted with the job CCSID (typically 37). Without it, EBCDIC blanks
    (0x40) arrive as ``@`` and R05 blank detection never fires.
    """
    return (
        f"jdbc:as400://{host}"
        f";libraries={schema}"
        f";prompt=false"
        f";errors=full"
        f";date format=iso"
        f";translate binary=true"
        f";login timeout={login_timeout_seconds}"
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
    url = build_jdbc_url(host, schema, login_timeout_seconds=login_timeout_seconds)
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
    tables: str | None = None,
) -> OfflineExport:
    """
    Load schema metadata + sampled rows into the same Offline export structure.

    SELECT-only: SYSTABLES / SYSCOLUMNS2 for catalog, FETCH FIRST for samples.
    ``tables`` accepts a comma-separated name list or a SQL LIKE pattern
    (see ``parse_tables_filter``).
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
    tables_filter = parse_tables_filter(tables)
    try:
        table_names = _list_tables(connection, schema_name, tables_filter)
        loaded: dict[str, TableData] = {}
        for table_name in table_names:
            columns = _list_columns(connection, schema_name, table_name)
            rows = _sample_rows(
                connection,
                schema=schema_name,
                table=table_name,
                columns=columns,
                sample_rows=sample_rows,
            )
            loaded[table_name] = TableData(name=table_name, columns=columns, rows=rows)
    finally:
        connection.close()

    return OfflineExport(
        schema_name=schema_name,
        tables=loaded,
        source_path=Path(f"jdbc:as400://{host}/{schema_name}"),
    )


def write_export_csvs(export: OfflineExport, data_dir: Path) -> None:
    """Write sampled table rows as CSV files for dbt-duckdb external sources."""
    data_dir.mkdir(parents=True, exist_ok=True)
    for table in export.tables.values():
        path = data_dir / f"{table.name}.csv"
        fieldnames = [column.name for column in table.columns]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in table.rows:
                writer.writerow(
                    {
                        name: "" if row.get(name) is None else row.get(name)
                        for name in fieldnames
                    }
                )


def materialize_jdbc_scan_csvs(scan: dict[str, Any], data_dir: Path) -> None:
    """
    Re-fetch JDBC sample rows into ``data_dir`` for a jdbc-mode scan artifact.

    Credentials: DB2ILENS_USER / PUB400_USER and DB2ILENS_PASSWORD / PUB400_PASSWORD.
    """
    if str(scan.get("mode", "")).lower() != "jdbc":
        return
    user = os.environ.get("DB2ILENS_USER") or os.environ.get("PUB400_USER")
    password = os.environ.get("DB2ILENS_PASSWORD") or os.environ.get("PUB400_PASSWORD")
    if not user or not password:
        raise JdbcConfigError(
            "jdbc scan needs DB2ILENS_USER/PUB400_USER and "
            "DB2ILENS_PASSWORD/PUB400_PASSWORD to materialize CSV data for dbt"
        )
    host, schema = parse_jdbc_source(str(scan.get("source", "")))
    sample_rows = int(scan.get("sample_rows") or 5000)
    # Restrict JDBC reload to tables already present in the scan artifact.
    wanted = sorted(
        {
            str(table.get("name", "")).strip().upper()
            for table in scan.get("tables", [])
            if str(table.get("name", "")).strip()
        }
    )
    tables_arg = ",".join(wanted) if wanted else None
    export = load_jdbc_export(
        host=host,
        user=user,
        password=password,
        schema=schema,
        sample_rows=sample_rows,
        tables=tables_arg,
    )
    filtered = OfflineExport(
        schema_name=export.schema_name,
        tables={
            name: table for name, table in export.tables.items() if name in set(wanted)
        },
        source_path=export.source_path,
    )
    write_export_csvs(filtered, data_dir)


def _list_tables(
    connection: Any,
    schema: str,
    tables_filter: TablesFilter | None = None,
) -> list[str]:
    if isinstance(tables_filter, str):
        rows = _fetch_all(connection, _SQL_LIST_TABLES_LIKE, [schema, tables_filter])
        return _table_names_from_rows(rows)

    if tables_filter is None:
        rows = _fetch_all(connection, _SQL_LIST_TABLES, [schema])
        return _table_names_from_rows(rows)

    # Exact names: one equality query per name (stable binding, no dynamic IN).
    names: list[str] = []
    seen: set[str] = set()
    for wanted in tables_filter:
        rows = _fetch_all(connection, _SQL_LIST_TABLES_EQ, [schema, wanted])
        for name in _table_names_from_rows(rows):
            if name not in seen:
                seen.add(name)
                names.append(name)
    return sorted(names)


def _table_names_from_rows(rows: list[dict[str, Any]]) -> list[str]:
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
    text = str(value)
    # IBM i CHAR is blank-padded to LENGTH; strip so keys/flags match offline CSV.
    if data_type == "CHAR":
        return text.rstrip(" ")
    return text


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
