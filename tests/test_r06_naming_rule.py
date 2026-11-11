"""TDD: R06 obscure short column names + abbreviation dictionary."""

from __future__ import annotations

from pathlib import Path

from db2ilens.connector.offline import load_export
from db2ilens.profiler.sampling import profile_column
from db2ilens.rules import RULES, ObscureShortNameRule
from db2ilens.rules.naming_rules import ABBREVIATIONS, suggest_long_name

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_erp"


def test_r06_is_registered() -> None:
    assert any(isinstance(rule, ObscureShortNameRule) for rule in RULES)


def test_abbreviation_dictionary_has_required_entries() -> None:
    assert ABBREVIATIONS["CST"] == "customer"
    assert ABBREVIATIONS["CUS"] == "customer"
    assert ABBREVIATIONS["ORD"] == "order"
    assert ABBREVIATIONS["DTE"] == "date"
    assert ABBREVIATIONS["PRC"] == "price"
    assert ABBREVIATIONS["STD"] == "standard"
    assert ABBREVIATIONS["QTY"] == "quantity"
    assert ABBREVIATIONS["AMT"] == "amount"
    assert ABBREVIATIONS["NAM"] == "name"
    assert ABBREVIATIONS["FLG"] == "flag"
    assert ABBREVIATIONS["ID"] == "identifier"


def test_suggest_long_name_examples() -> None:
    assert suggest_long_name("ORDDTE") == "order_date"
    assert suggest_long_name("CUSNAME") == "customer_name"
    assert suggest_long_name("STDPRC") == "standard_price"
    assert suggest_long_name("ZZZQQQ") is None


def test_r06_detects_cusname_with_suggestion() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["CLIENTS"], "CUSNAME")

    findings = ObscureShortNameRule().detect(profile)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "R06"
    assert finding.severity.value == "info"
    assert finding.evidence["suggested_name"] == "customer_name"
    assert finding.evidence["decoded"] is True


def test_r06_emits_undecoded_finding_when_dictionary_misses() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["LIGNES_CMD"], "TAGS")

    findings = ObscureShortNameRule().detect(profile)

    assert len(findings) == 1
    assert findings[0].evidence["suggested_name"] is None
    assert findings[0].evidence["decoded"] is False
    assert "undecoded" in findings[0].message.lower()


def test_r06_skips_column_with_comment() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["ARTICLES"], "ARTDESC")

    assert profile.comment == "Article description"
    assert ObscureShortNameRule().detect(profile) == []
