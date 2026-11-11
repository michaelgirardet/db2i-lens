"""TDD: R03 CCSID 65535 encoding rule."""

from __future__ import annotations

from pathlib import Path

from db2ilens.connector.offline import load_export
from db2ilens.profiler.sampling import profile_column
from db2ilens.rules import RULES, Ccsid65535Rule
from db2ilens.rules.base import Finding, Severity

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_erp"


def test_r03_is_registered() -> None:
    assert any(isinstance(rule, Ccsid65535Rule) for rule in RULES)


def test_r03_detects_cusname_ccsid_65535() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["CLIENTS"], "CUSNAME")

    assert profile.ccsid == 65535
    findings = Ccsid65535Rule().detect(profile)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "R03"
    assert finding.table == "CLIENTS"
    assert finding.column == "CUSNAME"
    assert finding.severity == Severity.CRITICAL
    assert finding.evidence["ccsid"] == 65535


def test_r03_fix_cast_with_translation_note() -> None:
    finding = Finding(
        rule_id="R03",
        table="CLIENTS",
        column="CUSNAME",
        severity=Severity.CRITICAL,
        message="ccsid",
    )
    sql = Ccsid65535Rule().fix(finding)
    assert sql is not None
    assert "CAST(CUSNAME AS VARCHAR)" in sql
    assert "CCSID 65535" in sql
    assert "translation" in sql.lower()


def test_r03_does_not_flag_ccsid_37() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["CLIENTS"], "CUSID")

    assert profile.ccsid == 37
    assert Ccsid65535Rule().detect(profile) == []
