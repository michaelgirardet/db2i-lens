"""Tests for the Rule ABC and stub rule registry."""

from __future__ import annotations

import pytest

from db2ilens.rules import ABBREVIATIONS, ALL_RULES
from db2ilens.rules.base import Finding, Rule, Severity


def test_incomplete_rule_cannot_be_instantiated() -> None:
    class IncompleteRule(Rule):
        id = "RX"
        name = "incomplete"
        severity = Severity.INFO

    with pytest.raises(TypeError):
        IncompleteRule()  # type: ignore[abstract]


def test_concrete_rule_detect_and_fix() -> None:
    class DummyRule(Rule):
        id = "R99"
        name = "dummy"
        severity = Severity.INFO

        def detect(self, column_profile: object) -> list[Finding]:
            return [
                Finding(
                    rule_id=self.id,
                    table="T",
                    column="C",
                    severity=self.severity,
                    message="hit",
                )
            ]

        def fix(self, finding: Finding) -> str | None:
            return f"select {finding.column}"

    rule = DummyRule()
    findings = rule.detect({})
    assert len(findings) == 1
    assert findings[0].rule_id == "R99"
    assert rule.fix(findings[0]) == "select C"


def test_all_rules_registered_and_ignore_empty_profile() -> None:
    expected_ids = {"R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09"}
    assert {cls.id for cls in ALL_RULES} == expected_ids
    implemented_fix_ids = {"R01", "R02", "R03", "R04", "R05", "R06", "R08"}
    for cls in ALL_RULES:
        rule = cls()
        assert rule.detect({}) == []
        evidence: dict[str, object] = {}
        if rule.id == "R04":
            evidence = {"implied_scale": 2, "length": 9}
        elif rule.id == "R06":
            evidence = {"suggested_name": "customer_name"}
        finding = Finding(
            rule_id=rule.id,
            table="T",
            column="C",
            severity=rule.severity,
            message="n/a",
            evidence=evidence,
        )
        if rule.id in implemented_fix_ids:
            assert rule.fix(finding) is not None
        else:
            assert rule.fix(finding) is None


def test_abbreviations_dictionary_has_core_entries() -> None:
    assert ABBREVIATIONS["CST"] == "customer"
    assert ABBREVIATIONS["ORD"] == "order"
    assert ABBREVIATIONS["DTE"] == "date"
