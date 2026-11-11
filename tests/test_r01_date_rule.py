"""TDD: R01 numeric YYYYMMDD date rule on mini-ERP fixtures."""

from __future__ import annotations

from pathlib import Path

from db2ilens.connector.offline import load_export
from db2ilens.profiler.sampling import profile_column
from db2ilens.rules import RULES, NumericDateYYYYMMDDRule
from db2ilens.rules.base import Finding, Severity

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_erp"


def test_r01_is_registered() -> None:
    assert any(isinstance(rule, NumericDateYYYYMMDDRule) for rule in RULES)
    assert any(rule.id == "R01" for rule in RULES)


def test_r01_detects_orddte_on_commandes() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["COMMANDES"], "ORDDTE")

    findings = NumericDateYYYYMMDDRule().detect(profile)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "R01"
    assert finding.table == "COMMANDES"
    assert finding.column == "ORDDTE"
    assert finding.severity == Severity.WARNING


def test_r01_fix_sql_matches_prd() -> None:
    finding = Finding(
        rule_id="R01",
        table="COMMANDES",
        column="ORDDTE",
        severity=Severity.WARNING,
        message="numeric YYYYMMDD",
    )

    sql = NumericDateYYYYMMDDRule().fix(finding)

    assert sql == "TO_DATE(TO_CHAR(ORDDTE), 'YYYYMMDD')"


def test_r01_does_not_flag_cyymmdd_crtdte() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["ARTICLES"], "CRTDTE")

    findings = NumericDateYYYYMMDDRule().detect(profile)

    assert findings == []


def test_r01_does_not_flag_non_date_dec8_phnnum() -> None:
    """DEC(8,0) phone numbers must not be mistaken for YYYYMMDD dates."""
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["CLIENTS"], "PHNNUM")

    assert profile.length == 8
    assert profile.scale == 0
    assert profile.data_type == "DECIMAL"
    # Sanity: values are 8-digit numbers that are NOT valid calendar dates.
    assert all(isinstance(v, int) and len(f"{v:08d}") == 8 for v in profile.sample_values)

    findings = NumericDateYYYYMMDDRule().detect(profile)

    assert findings == []
