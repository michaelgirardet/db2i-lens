"""Numeric legacy rules."""

from __future__ import annotations

from db2ilens.profiler.sampling import ColumnProfile
from db2ilens.rules.base import Finding, Rule, Severity

_NUMERIC_TYPES = {"DECIMAL", "NUMERIC", "INTEGER", "SMALLINT", "BIGINT"}


class ImplicitPackedDecimalRule(Rule):
    """R04 — packed decimal stored without an explicit scale point."""

    id = "R04"
    name = "implicit_packed_decimal"
    severity = Severity.WARNING

    def detect(self, column_profile: object) -> list[Finding]:
        if not isinstance(column_profile, ColumnProfile):
            return []
        profile = column_profile
        if profile.data_type.upper() not in _NUMERIC_TYPES:
            return []
        scale = 0 if profile.scale is None else profile.scale
        implied = profile.implied_scale
        if scale != 0 or implied is None or implied <= 0:
            return []

        finding = Finding(
            rule_id=self.id,
            table=profile.table,
            column=profile.column,
            severity=self.severity,
            message=(
                f"Column {profile.table}.{profile.column} stores an implied "
                f"decimal with scale {implied}"
            ),
            evidence={
                "data_type": profile.data_type,
                "length": profile.length,
                "scale": profile.scale,
                "implied_scale": implied,
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
        implied = int(finding.evidence.get("implied_scale", 0))
        length = finding.evidence.get("length")
        if implied <= 0:
            return None
        divisor = 10**implied
        precision = int(length) if isinstance(length, int) else implied + 1
        return f"CAST({finding.column} / {divisor} AS DECIMAL({precision}, {implied}))"


class ZeroSentinelRule(Rule):
    """R09 — zero used as a NULL sentinel on numeric columns."""

    id = "R09"
    name = "zero_sentinel"
    severity = Severity.INFO

    def detect(self, column_profile: object) -> list[Finding]:
        return []

    def fix(self, finding: Finding) -> str | None:
        return None
