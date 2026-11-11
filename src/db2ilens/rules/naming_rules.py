"""Naming and value-shape legacy rules."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import yaml

from db2ilens.profiler.sampling import ColumnProfile
from db2ilens.rules.base import Finding, Rule, Severity

_CHAR_TYPES = {"CHAR", "VARCHAR", "CHARACTER", "CHARACTER VARYING"}
_BINARY_FLAG_SETS = ({"Y", "N"}, {"1", "0"})
BLANK_RATIO_THRESHOLD = 0.20
MULTI_VALUE_SEPARATOR_THRESHOLD = 0.25
_MULTI_VALUE_SEPARATORS = ("|", ";", ",")
_SHORT_NAME_MAX_LEN = 10


def _load_abbreviations() -> dict[str, str]:
    """Load the enrichable abbreviation dictionary (YAML next to this module)."""
    try:
        raw = resources.files("db2ilens.rules").joinpath("abbreviations.yaml").read_text(
            encoding="utf-8"
        )
    except (FileNotFoundError, OSError, TypeError):
        path = Path(__file__).with_name("abbreviations.yaml")
        raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ValueError("abbreviations.yaml must be a mapping")
    return {str(key).upper(): str(value) for key, value in data.items()}


ABBREVIATIONS: dict[str, str] = _load_abbreviations()


def suggest_long_name(
    column_name: str,
    abbreviations: dict[str, str] | None = None,
) -> str | None:
    """Decode a short IBM i column name using greedy longest-token matching."""
    abbrevs = abbreviations if abbreviations is not None else ABBREVIATIONS
    text = column_name.upper()
    if not text:
        return None
    keys = sorted(abbrevs.keys(), key=len, reverse=True)
    parts: list[str] = []
    index = 0
    while index < len(text):
        matched = False
        for key in keys:
            if text.startswith(key, index):
                parts.append(abbrevs[key])
                index += len(key)
                matched = True
                break
        if not matched:
            return None
    return "_".join(parts) if parts else None


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
        if not isinstance(column_profile, ColumnProfile):
            return []
        profile = column_profile
        if profile.data_type.upper() not in _CHAR_TYPES:
            return []
        if len(profile.column) > _SHORT_NAME_MAX_LEN:
            return []
        if profile.comment is not None and str(profile.comment).strip() != "":
            return []

        suggested = suggest_long_name(profile.column)
        decoded = suggested is not None
        message = (
            f"Column {profile.table}.{profile.column} has an obscure short name"
            if decoded
            else (
                f"Column {profile.table}.{profile.column} has an undecoded "
                "short name"
            )
        )
        finding = Finding(
            rule_id=self.id,
            table=profile.table,
            column=profile.column,
            severity=self.severity,
            message=message,
            evidence={
                "column_name": profile.column,
                "suggested_name": suggested,
                "decoded": decoded,
            },
            suggested_fix=suggested,
        )
        return [finding]

    def fix(self, finding: Finding) -> str | None:
        suggested = finding.evidence.get("suggested_name")
        return str(suggested) if isinstance(suggested, str) and suggested else None


class MultiValueColumnRule(Rule):
    """R07 — columns with a recurring separator (warning only in v1)."""

    id = "R07"
    name = "multi_value_column"
    severity = Severity.WARNING

    def detect(self, column_profile: object) -> list[Finding]:
        if not isinstance(column_profile, ColumnProfile):
            return []
        profile = column_profile
        if profile.data_type.upper() not in _CHAR_TYPES:
            return []

        non_empty = [
            str(value)
            for value in profile.sample_values
            if value is not None and str(value).strip() != ""
        ]
        if not non_empty:
            return []

        best_separator: str | None = None
        best_frequency = 0.0
        for separator in _MULTI_VALUE_SEPARATORS:
            frequency = sum(1 for value in non_empty if separator in value) / len(non_empty)
            if frequency > best_frequency:
                best_frequency = frequency
                best_separator = separator

        if best_separator is None or best_frequency <= MULTI_VALUE_SEPARATOR_THRESHOLD:
            return []

        finding = Finding(
            rule_id=self.id,
            table=profile.table,
            column=profile.column,
            severity=self.severity,
            message=(
                f"Column {profile.table}.{profile.column} looks multi-valued "
                f"(separator {best_separator!r} in {best_frequency:.0%} of samples)"
            ),
            evidence={
                "separator": best_separator,
                "frequency": best_frequency,
                "threshold": MULTI_VALUE_SEPARATOR_THRESHOLD,
                "sample_size": len(non_empty),
            },
            suggested_fix=None,
        )
        return [finding]

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
