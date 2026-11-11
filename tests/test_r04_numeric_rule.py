"""TDD: R04 implicit packed-decimal rule."""

from __future__ import annotations

from pathlib import Path

from db2ilens.connector.offline import load_export
from db2ilens.profiler.sampling import profile_column
from db2ilens.rules import RULES, ImplicitPackedDecimalRule
from db2ilens.rules.base import Finding, Severity

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_erp"


def test_r04_is_registered() -> None:
    assert any(isinstance(rule, ImplicitPackedDecimalRule) for rule in RULES)


def test_r04_detects_prc_with_implied_scale() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["LIGNES_CMD"], "PRC")

    assert profile.scale == 0
    assert profile.implied_scale == 2

    findings = ImplicitPackedDecimalRule().detect(profile)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "R04"
    assert finding.table == "LIGNES_CMD"
    assert finding.column == "PRC"
    assert finding.severity == Severity.WARNING
    assert finding.evidence["implied_scale"] == 2


def test_r04_fix_divides_by_power_of_ten() -> None:
    finding = Finding(
        rule_id="R04",
        table="LIGNES_CMD",
        column="PRC",
        severity=Severity.WARNING,
        message="packed",
        evidence={"implied_scale": 2, "length": 9},
    )
    sql = ImplicitPackedDecimalRule().fix(finding)
    assert sql == "CAST(PRC / 100 AS DECIMAL(9, 2))"


def test_r04_does_not_flag_integer_qty() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["LIGNES_CMD"], "QTY")

    assert profile.scale == 0
    assert profile.implied_scale in (None, 0)
    assert ImplicitPackedDecimalRule().detect(profile) == []
