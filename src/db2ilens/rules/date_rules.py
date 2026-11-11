"""Date-related legacy rules (stubs in P0)."""

from __future__ import annotations

from db2ilens.rules.base import Finding, Rule, Severity


class NumericDateYYYYMMDDRule(Rule):
    """R01 — DEC(8,0) values that match valid YYYYMMDD dates."""

    id = "R01"
    name = "numeric_date_yyyymmdd"
    severity = Severity.WARNING

    def detect(self, column_profile: object) -> list[Finding]:
        return []

    def fix(self, finding: Finding) -> str | None:
        return None


class IbmCenturyDateRule(Rule):
    """R02 — DEC(7,0) IBM CYYMMDD century dates."""

    id = "R02"
    name = "ibm_century_date_cyymmdd"
    severity = Severity.WARNING

    def detect(self, column_profile: object) -> list[Finding]:
        return []

    def fix(self, finding: Finding) -> str | None:
        return None
