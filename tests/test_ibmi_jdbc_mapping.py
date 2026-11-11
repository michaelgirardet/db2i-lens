"""Unit tests for Db2 for i SYSCOLUMNS2 → ColumnMeta mapping (no live JDBC)."""

from __future__ import annotations

from db2ilens.connector.ibmi_jdbc import (
    JdbcConfigError,
    map_syscolumns2_row,
    normalize_ibm_data_type,
    resolve_jt400_jar,
    resolve_password,
)


def test_map_character_column_with_ccsid_65535() -> None:
    meta = map_syscolumns2_row(
        {
            "COLUMN_NAME": "CUSNAME",
            "DATA_TYPE": "CHARACTER",
            "LENGTH": 30,
            "NUMERIC_SCALE": None,
            "IS_NULLABLE": "N",
            "CCSID": 65535,
            "COLUMN_TEXT": "   ",
        }
    )
    assert meta.name == "CUSNAME"
    assert meta.data_type == "CHAR"
    assert meta.length == 30
    assert meta.scale is None
    assert meta.implied_scale is None
    assert meta.nullable is False
    assert meta.ccsid == 65535
    assert meta.comment is None  # blank COLUMN_TEXT → no comment (R06 can fire)


def test_map_decimal_column_precision_and_scale() -> None:
    meta = map_syscolumns2_row(
        {
            "COLUMN_NAME": "ORDDTE",
            "DATA_TYPE": "DECIMAL",
            "LENGTH": 8,
            "NUMERIC_SCALE": 0,
            "IS_NULLABLE": "N",
            "CCSID": None,
            "COLUMN_TEXT": None,
        }
    )
    assert meta.data_type == "DECIMAL"
    assert meta.length == 8
    assert meta.scale == 0
    assert meta.ccsid is None
    assert meta.comment is None
    assert meta.implied_scale is None  # never present in SYSCOLUMNS2


def test_map_column_text_becomes_comment() -> None:
    meta = map_syscolumns2_row(
        {
            "COLUMN_NAME": "ARTDESC",
            "DATA_TYPE": "CHAR",
            "LENGTH": 40,
            "NUMERIC_SCALE": None,
            "IS_NULLABLE": "N",
            "CCSID": 37,
            "COLUMN_TEXT": "Article description",
        }
    )
    assert meta.comment == "Article description"
    assert meta.ccsid == 37


def test_map_varchar_and_nullable_yes() -> None:
    meta = map_syscolumns2_row(
        {
            "COLUMN_NAME": "TAGS",
            "DATA_TYPE": "VARCHAR",
            "LENGTH": 50,
            "NUMERIC_SCALE": None,
            "IS_NULLABLE": "Y",
            "CCSID": 37,
            "COLUMN_TEXT": "",
        }
    )
    assert meta.data_type == "VARCHAR"
    assert meta.nullable is True
    assert meta.comment is None


def test_normalize_ibm_data_types() -> None:
    assert normalize_ibm_data_type("CHARACTER") == "CHAR"
    assert normalize_ibm_data_type("CHARACTER VARYING") == "VARCHAR"
    assert normalize_ibm_data_type("DECIMAL") == "DECIMAL"


def test_resolve_password_prefers_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DB2ILENS_PASSWORD", "from-env")
    assert resolve_password(password_stdin=True) == "from-env"


def test_resolve_password_reads_stdin(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("DB2ILENS_PASSWORD", raising=False)
    monkeypatch.setattr("sys.stdin.readline", lambda: "from-stdin\n")
    assert resolve_password(password_stdin=True) == "from-stdin"


def test_resolve_password_requires_source(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("DB2ILENS_PASSWORD", raising=False)
    try:
        resolve_password(password_stdin=False)
        raised = False
    except JdbcConfigError:
        raised = True
    assert raised


def test_resolve_jt400_jar_uses_env(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    jar = tmp_path / "jt400.jar"
    jar.write_bytes(b"fake")
    monkeypatch.setenv("JT400_JAR", str(jar))
    assert resolve_jt400_jar() == jar.resolve()


def test_resolve_jt400_jar_missing_raises(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("JT400_JAR", raising=False)
    monkeypatch.chdir(tmp_path)
    try:
        resolve_jt400_jar()
        raised = False
    except JdbcConfigError:
        raised = True
    assert raised
