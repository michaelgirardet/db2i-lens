"""Naming and value-shape legacy rules."""

from __future__ import annotations

from db2ilens.profiler.sampling import ColumnProfile
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

_CHAR_TYPES = {"CHAR", "VARCHAR", "CHARACTER", "CHARACTER VARYING"}
_BINARY_FLAG_SETS = ({"Y", "N"}, {"1", "0"})
BLANK_RATIO_THRESHOLD = 0.20


class BlankAsNullRule(Rule):
    """R05 — blank / whitespace strings standing in for NULL."""

    id = "R05"
    name = "blank_as_null"
    severity = Severity.WARNING

    def detect(self, column_profile: object) -> list[Finding]:
        if not isinstance(column_profile, ColumnProfile):
            return []
        profile = column_profile
        if profile.data_type.upper() not in _CHAR_TYPES:
            return []
        if profile.row_count == 0:
            return []
        blank_ratio = profile.blank_count / profile.row_count
        if blank_ratio <= BLANK_RATIO_THRESHOLD:
            return []

        finding = Finding(
            rule_id=self.id,
            table=profile.table,
            column=profile.column,
            severity=self.severity,
            message=(
                f"Column {profile.table}.{profile.column} uses blanks as NULL "
                f"({blank_ratio:.0%} of sample)"
            ),
            evidence={
                "blank_count": profile.blank_count,
                "row_count": profile.row_count,
                "blank_ratio": blank_ratio,
                "threshold": BLANK_RATIO_THRESHOLD,
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
        return f"NULLIF(TRIM({finding.column}), '')"


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
        if not isinstance(column_profile, ColumnProfile):
            return []
        profile = column_profile
        if profile.data_type.upper() not in _CHAR_TYPES:
            return []
        if profile.length != 1:
            return []
        if profile.distinct_count != 2:
            return []

        values = {str(value) for value, _count in profile.top_values if value is not None}
        if {value.upper() for value in values} not in _BINARY_FLAG_SETS:
            return []

        finding = Finding(
            rule_id=self.id,
            table=profile.table,
            column=profile.column,
            severity=self.severity,
            message=(
                f"Column {profile.table}.{profile.column} looks like a "
                f"binary flag ({sorted(values)})"
            ),
            evidence={
                "values": sorted(values),
                "distinct_count": profile.distinct_count,
                "length": profile.length,
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
        col = finding.column
        return (
            f"CASE WHEN {col} IN ('Y', '1') THEN TRUE "
            f"WHEN {col} IN ('N', '0') THEN FALSE END"
        )
