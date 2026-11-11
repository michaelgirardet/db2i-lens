"""Encoding / CCSID legacy rules."""

from __future__ import annotations

from db2ilens.profiler.sampling import ColumnProfile
from db2ilens.rules.base import Finding, Rule, Severity

_CHAR_TYPES = {"CHAR", "VARCHAR", "CHARACTER", "CHARACTER VARYING"}
_BINARY_CCSID = 65535


class Ccsid65535Rule(Rule):
    """R03 — CCSID 65535 (binary / EBCDIC) character columns."""

    id = "R03"
    name = "ccsid_65535"
    severity = Severity.CRITICAL

    def detect(self, column_profile: object) -> list[Finding]:
        if not isinstance(column_profile, ColumnProfile):
            return []
        profile = column_profile
        if profile.data_type.upper() not in _CHAR_TYPES:
            return []
        if profile.ccsid != _BINARY_CCSID:
            return []

        finding = Finding(
            rule_id=self.id,
            table=profile.table,
            column=profile.column,
            severity=self.severity,
            message=(
                f"Column {profile.table}.{profile.column} has CCSID 65535 "
                "(binary / no character conversion)"
            ),
            evidence={
                "ccsid": profile.ccsid,
                "data_type": profile.data_type,
            },
        )
        return [
            Finding(
                rule_id=finding.rule_id,
                table=finding.table,
                column=finding.column,
                severity=finding.severity,
                message=finding.message,
                evidence=finding.evidence,
                suggested_fix=self.fix(finding),
            )
        ]

    def fix(self, finding: Finding) -> str | None:
        return (
            f"CAST({finding.column} AS VARCHAR) "
            f"/* TODO: apply CCSID 65535 translation table */"
        )
