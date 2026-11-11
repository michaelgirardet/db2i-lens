"""TDD: R05 blank-as-null and R08 Y/N flag rules."""

from __future__ import annotations

from pathlib import Path

from db2ilens.connector.offline import load_export
from db2ilens.profiler.sampling import profile_column
from db2ilens.rules import RULES, BlankAsNullRule, YnFlagRule
from db2ilens.rules.base import Finding, Severity

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_erp"
BLANK_THRESHOLD = 0.20


def test_r05_and_r08_are_registered() -> None:
    assert any(isinstance(rule, BlankAsNullRule) for rule in RULES)
    assert any(isinstance(rule, YnFlagRule) for rule in RULES)
    assert {rule.id for rule in RULES} >= {"R05", "R08"}


def test_r05_detects_cusname_blanks_above_20_percent() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["CLIENTS"], "CUSNAME")

    # Fixture has 2 blanks out of 5 rows → 40% > 20% threshold.
    assert profile.blank_count / profile.row_count > BLANK_THRESHOLD

    findings = BlankAsNullRule().detect(profile)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "R05"
    assert finding.table == "CLIENTS"
    assert finding.column == "CUSNAME"
    assert finding.severity == Severity.WARNING
    assert finding.evidence["blank_ratio"] > BLANK_THRESHOLD


def test_r05_fix_sql() -> None:
    finding = Finding(
        rule_id="R05",
        table="CLIENTS",
        column="CUSNAME",
        severity=Severity.WARNING,
        message="blanks",
    )
    assert BlankAsNullRule().fix(finding) == "NULLIF(TRIM(CUSNAME), '')"


def test_r05_does_not_flag_rich_text_without_blanks() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["ARTICLES"], "ARTDESC")

    assert profile.blank_count / profile.row_count <= BLANK_THRESHOLD
    assert BlankAsNullRule().detect(profile) == []


def test_r08_detects_actflg_yn() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["CLIENTS"], "ACTFLG")

    findings = YnFlagRule().detect(profile)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "R08"
    assert finding.table == "CLIENTS"
    assert finding.column == "ACTFLG"
    assert finding.severity == Severity.INFO
    assert set(finding.evidence["values"]) == {"Y", "N"}


def test_r08_fix_cast_boolean() -> None:
    finding = Finding(
        rule_id="R08",
        table="CLIENTS",
        column="ACTFLG",
        severity=Severity.INFO,
        message="flag",
    )
    assert YnFlagRule().fix(finding) == (
        "CASE WHEN ACTFLG IN ('Y', '1') THEN TRUE "
        "WHEN ACTFLG IN ('N', '0') THEN FALSE END"
    )


def test_r08_does_not_flag_non_binary_ordsts() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["COMMANDES"], "ORDSTS")

    assert profile.length == 1
    assert profile.distinct_count == 3  # O, C, X — not binary
    assert YnFlagRule().detect(profile) == []
