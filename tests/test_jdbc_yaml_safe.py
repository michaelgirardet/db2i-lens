"""JDBC values from JT400/JPype must become plain Python before YAML dump."""

from __future__ import annotations

import yaml

from db2ilens.connector.ibmi_jdbc import _coerce_jdbc_value, map_syscolumns2_row
from db2ilens.connector.offline import ColumnMeta
from db2ilens.scan import (
    ScanColumnMetadata,
    ScanColumnResult,
    ScanColumnStats,
    ScanFinding,
    ScanResult,
    ScanSummary,
    ScanTableResult,
    _yaml_safe,
    write_scan_yaml,
)


class _FakeJavaInt:
    """Mimics a JT400/JPype boxed integer: looks like 4, is not a Python int."""

    def __init__(self, value: int) -> None:
        self._value = value

    def __int__(self) -> int:
        return self._value

    def __str__(self) -> str:
        return str(self._value)

    def __repr__(self) -> str:
        return str(self._value)


def test_yaml_safe_converts_java_like_int() -> None:
    assert _yaml_safe(_FakeJavaInt(4)) == 4
    assert type(_yaml_safe(_FakeJavaInt(4))) is int


def test_coerce_jdbc_numeric_converts_java_like_int() -> None:
    meta = ColumnMeta(name="QTY", data_type="DECIMAL", length=7, scale=0, nullable=False)
    value = _coerce_jdbc_value(_FakeJavaInt(4), meta)
    assert value == 4
    assert type(value) is int


def test_map_syscolumns2_ccsid_is_plain_int() -> None:
    meta = map_syscolumns2_row(
        {
            "COLUMN_NAME": "CUSNAME",
            "DATA_TYPE": "CHAR",
            "LENGTH": _FakeJavaInt(30),
            "NUMERIC_SCALE": None,
            "IS_NULLABLE": "N",
            "CCSID": _FakeJavaInt(65535),
            "COLUMN_TEXT": None,
        }
    )
    assert type(meta.length) is int
    assert type(meta.ccsid) is int
    assert meta.ccsid == 65535


def test_write_scan_yaml_accepts_java_like_stats(tmp_path) -> None:  # type: ignore[no-untyped-def]
    result = ScanResult(
        version="1.0",
        generated_at="STABLE",
        mode="jdbc",
        source="jdbc:as400://pub400.com/DUCSVEN1",
        schema_name="DUCSVEN1",
        sample_rows=100,
        summary=ScanSummary(
            table_count=1,
            column_count=1,
            finding_count=0,
            findings_by_severity={"critical": 0, "warning": 0, "info": 0},
        ),
        tables=[
            ScanTableResult(
                name="CLIENTS",
                columns=[
                    ScanColumnResult(
                        name="QTY",
                        metadata=ScanColumnMetadata(
                            name="QTY",
                            data_type="DECIMAL",
                            length=7,
                            scale=0,
                            implied_scale=None,
                            nullable=False,
                            ccsid=None,
                            comment=None,
                        ),
                        stats=ScanColumnStats(
                            row_count=1,
                            null_count=0,
                            blank_count=0,
                            distinct_count=1,
                            min_value=_FakeJavaInt(4),
                            max_value=_FakeJavaInt(4),
                            top_values=[{"value": _FakeJavaInt(4), "count": 1}],
                        ),
                        findings=[
                            ScanFinding(
                                rule_id="R03",
                                severity="critical",
                                message="ccsid",
                                evidence={"ccsid": _FakeJavaInt(65535)},
                                suggested_fix=None,
                            )
                        ],
                    )
                ],
            )
        ],
    )
    out = tmp_path / "scan.yaml"
    write_scan_yaml(result, out)
    loaded = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert loaded["tables"][0]["columns"][0]["stats"]["min_value"] == 4
    assert loaded["tables"][0]["columns"][0]["findings"][0]["evidence"]["ccsid"] == 65535
