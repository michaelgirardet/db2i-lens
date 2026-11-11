"""Encoding / CCSID legacy rules (stubs in P0)."""

from __future__ import annotations

from db2ilens.rules.base import Finding, Rule, Severity


class Ccsid65535Rule(Rule):
    """R03 — CCSID 65535 (binary / EBCDIC) character columns."""

    id = "R03"
    name = "ccsid_65535"
    severity = Severity.CRITICAL

    def detect(self, column_profile: object) -> list[Finding]:
        return []

    def fix(self, finding: Finding) -> str | None:
        return None
