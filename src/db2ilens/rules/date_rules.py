"""Date-related legacy rules."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from db2ilens.profiler.sampling import ColumnProfile
from db2ilens.rules.base import Finding, Rule, Severity

_NUMERIC_TYPES = {"DECIMAL", "NUMERIC", "INTEGER", "SMALLINT", "BIGINT"}


class NumericDateYYYYMMDDRule(Rule):
    """R01 — DEC(8,0) values that match valid YYYYMMDD dates."""

    id = "R01"
    name = "numeric_date_yyyymmdd"
    severity = Severity.WARNING

    def detect(self, column_profile: object) -> list[Finding]:
        if not isinstance(column_profile, ColumnProfile):
            return []
        profile = column_profile
        if not _is_dec8_numeric(profile):
            return []
        values = [value for value in profile.sample_values if value is not None]
        if not values:
            return []
        if not all(_is_valid_yyyymmdd(value) for value in values):
            return []

        suggested = self.fix(
            Finding(
                rule_id=self.id,
                table=profile.table,
                column=profile.column,
                severity=self.severity,
                message="",
            )
        )
        return [
            Finding(
                rule_id=self.id,
                table=profile.table,
                column=profile.column,
                severity=self.severity,
                message=(
                    f"Column {profile.table}.{profile.column} stores dates as "
                    "DEC(8,0) YYYYMMDD"
                ),
                evidence={
                    "data_type": profile.data_type,
                    "length": profile.length,
                    "scale": profile.scale,
                    "sample_size": len(values),
                    "format": "YYYYMMDD",
                },
                suggested_fix=suggested,
            )
        ]

    def fix(self, finding: Finding) -> str | None:
        return f"TO_DATE(TO_CHAR({finding.column}), 'YYYYMMDD')"


class IbmCenturyDateRule(Rule):
    """R02 — DEC(7,0) IBM CYYMMDD century dates."""

    id = "R02"
    name = "ibm_century_date_cyymmdd"
    severity = Severity.WARNING

    def detect(self, column_profile: object) -> list[Finding]:
        return []

    def fix(self, finding: Finding) -> str | None:
        return None


def _is_dec8_numeric(profile: ColumnProfile) -> bool:
    if profile.data_type.upper() not in _NUMERIC_TYPES:
        return False
    if profile.length != 8:
        return False
    scale = 0 if profile.scale is None else profile.scale
    return scale == 0


def _is_valid_yyyymmdd(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        text = f"{value:08d}"
    elif isinstance(value, float) and value.is_integer():
        text = f"{int(value):08d}"
    elif isinstance(value, str) and value.strip().isdigit():
        text = value.strip().zfill(8)
    else:
        return False
    if len(text) != 8:
        return False
    try:
        datetime.strptime(text, "%Y%m%d")
    except ValueError:
        return False
    return True
