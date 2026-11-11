"""Naming and value-shape legacy rules (stubs in P0)."""

from __future__ import annotations

from db2ilens.rules.base import Finding, Rule, Severity

# Minimal abbreviation dictionary; enrichable via YAML in later phases.
ABBREVIATIONS: dict[str, str] = {
    "CST": "customer",
    "CUS": "customer",
    "ORD": "order",
    "ART": "article",
    "DTE": "date",
    "QTY": "quantity",
    "PRC": "price",
    "FLG": "flag",
    "STS": "status",
    "ID": "id",
    "NM": "name",
    "DESC": "description",
    "CRT": "created",
    "ACT": "active",
    "CMD": "order_line",
}


class BlankAsNullRule(Rule):
    """R05 — blank / whitespace strings standing in for NULL."""

    id = "R05"
    name = "blank_as_null"
    severity = Severity.WARNING

    def detect(self, column_profile: object) -> list[Finding]:
        return []

    def fix(self, finding: Finding) -> str | None:
        return None


class ObscureShortNameRule(Rule):
    """R06 — column names ≤ 10 characters without a comment."""

    id = "R06"
    name = "obscure_short_name"
    severity = Severity.INFO

    def detect(self, column_profile: object) -> list[Finding]:
        return []

    def fix(self, finding: Finding) -> str | None:
        return None


class MultiValueColumnRule(Rule):
    """R07 — columns with a recurring separator (warning only in v1)."""

    id = "R07"
    name = "multi_value_column"
    severity = Severity.WARNING

    def detect(self, column_profile: object) -> list[Finding]:
        return []

    def fix(self, finding: Finding) -> str | None:
        return None


class YnFlagRule(Rule):
    """R08 — CHAR(1) flags with cardinality 2 ('Y'/'N' or '1'/'0')."""

    id = "R08"
    name = "yn_flag"
    severity = Severity.INFO

    def detect(self, column_profile: object) -> list[Finding]:
        return []

    def fix(self, finding: Finding) -> str | None:
        return None
