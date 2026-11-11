"""TDD: R02 IBM CYYMMDD century-date rule."""

from __future__ import annotations

from pathlib import Path

from db2ilens.connector.offline import load_export
from db2ilens.profiler.sampling import profile_column
from db2ilens.rules import RULES, IbmCenturyDateRule
from db2ilens.rules.base import Finding, Severity
from db2ilens.rules.date_rules import decode_cyymmdd

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_erp"


def test_r02_is_registered() -> None:
    assert any(isinstance(rule, IbmCenturyDateRule) for rule in RULES)


def test_cyymmdd_decoding_examples() -> None:
    assert decode_cyymmdd(1220101) == "2022-01-01"
    assert decode_cyymmdd(1260301) == "2026-03-01"
    assert decode_cyymmdd(990615) == "1999-06-15"  # century digit 0 → 19xx
    assert decode_cyymmdd(990615) == decode_cyymmdd(990615)


def test_r02_detects_crtdte_on_articles() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["ARTICLES"], "CRTDTE")

    # Fixture includes both 20xx (C=1) and 19xx (C=0) century dates.
    assert 1220101 in profile.sample_values
    assert 990615 in profile.sample_values  # stored without leading century zero as int

    findings = IbmCenturyDateRule().detect(profile)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "R02"
    assert finding.table == "ARTICLES"
    assert finding.column == "CRTDTE"
    assert finding.severity == Severity.WARNING


def test_r02_fix_sql_uses_century_logic() -> None:
    finding = Finding(
        rule_id="R02",
        table="ARTICLES",
        column="CRTDTE",
        severity=Severity.WARNING,
        message="cyymmdd",
    )
    sql = IbmCenturyDateRule().fix(finding)
    assert sql is not None
    assert "TO_DATE" in sql
    assert "CRTDTE" in sql
    assert "'19'" in sql
    assert "'20'" in sql
    assert "SUBSTR" in sql


def test_r02_does_not_flag_non_date_dec7_qty() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["LIGNES_CMD"], "QTY")

    assert profile.length == 7
    assert profile.scale == 0
    assert IbmCenturyDateRule().detect(profile) == []
