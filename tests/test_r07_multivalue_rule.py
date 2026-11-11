"""TDD: R07 multi-value column warning."""

from __future__ import annotations

from pathlib import Path

from db2ilens.connector.offline import load_export
from db2ilens.profiler.sampling import profile_column
from db2ilens.rules import RULES, MultiValueColumnRule
from db2ilens.rules.naming_rules import MULTI_VALUE_SEPARATOR_THRESHOLD

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_erp"


def test_r07_is_registered() -> None:
    assert any(isinstance(rule, MultiValueColumnRule) for rule in RULES)


def test_r07_detects_pipe_separator_on_tags() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["LIGNES_CMD"], "TAGS")

    findings = MultiValueColumnRule().detect(profile)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "R07"
    assert finding.severity.value == "warning"
    assert finding.suggested_fix is None
    assert finding.evidence["separator"] == "|"
    assert finding.evidence["frequency"] > MULTI_VALUE_SEPARATOR_THRESHOLD


def test_r07_fix_is_none_in_v1() -> None:
    from db2ilens.rules.base import Finding, Severity

    finding = Finding(
        rule_id="R07",
        table="LIGNES_CMD",
        column="TAGS",
        severity=Severity.WARNING,
        message="multi",
        evidence={"separator": "|", "frequency": 0.5},
    )
    assert MultiValueColumnRule().fix(finding) is None


def test_r07_does_not_flag_artdesc() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["ARTICLES"], "ARTDESC")

    assert MultiValueColumnRule().detect(profile) == []
