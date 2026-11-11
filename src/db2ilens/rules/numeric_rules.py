"""Numeric legacy rules (stubs in P0)."""

from __future__ import annotations

from db2ilens.rules.base import Finding, Rule, Severity


class ImplicitPackedDecimalRule(Rule):
    """R04 — packed decimal stored without an explicit scale point."""

    id = "R04"
    name = "implicit_packed_decimal"
    severity = Severity.WARNING

    def detect(self, column_profile: object) -> list[Finding]:
        return []

    def fix(self, finding: Finding) -> str | None:
        return None


class ZeroSentinelRule(Rule):
    """R09 — zero used as a NULL sentinel on numeric columns."""

    id = "R09"
    name = "zero_sentinel"
    severity = Severity.INFO

    def detect(self, column_profile: object) -> list[Finding]:
        return []

    def fix(self, finding: Finding) -> str | None:
        return None
