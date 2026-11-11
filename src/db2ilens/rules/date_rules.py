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
        if not isinstance(column_profile, ColumnProfile):
            return []
        profile = column_profile
        if not _is_dec7_numeric(profile):
            return []
        values = [value for value in profile.sample_values if value is not None]
        if not values:
            return []
        if not all(_is_valid_cyymmdd(value) for value in values):
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
                    "DEC(7,0) IBM CYYMMDD"
                ),
                evidence={
                    "data_type": profile.data_type,
                    "length": profile.length,
                    "scale": profile.scale,
                    "sample_size": len(values),
                    "format": "CYYMMDD",
                    "decoded_samples": [
                        decode_cyymmdd(value) for value in values[:5]
                    ],
                },
                suggested_fix=suggested,
            )
        ]

    def fix(self, finding: Finding) -> str | None:
        col = finding.column
        padded = f"LPAD(CAST({col} AS VARCHAR), 7, '0')"
        return (
            f"TO_DATE("
            f"CASE WHEN SUBSTR({padded}, 1, 1) = '0' THEN '19' ELSE '20' END "
            f"|| SUBSTR({padded}, 2, 6), "
            f"'YYYYMMDD')"
        )


def decode_cyymmdd(value: Any) -> str:
    """Decode an IBM CYYMMDD numeric value to ISO date YYYY-MM-DD."""
    text = _cyymmdd_text(value)
    century = text[0]
    year_prefix = "19" if century == "0" else "20"
    iso = f"{year_prefix}{text[1:3]}-{text[3:5]}-{text[5:7]}"
    datetime.strptime(iso, "%Y-%m-%d")
    return iso


def _is_dec8_numeric(profile: ColumnProfile) -> bool:
    if profile.data_type.upper() not in _NUMERIC_TYPES:
        return False
    if profile.length != 8:
        return False
    scale = 0 if profile.scale is None else profile.scale
    return scale == 0


def _is_dec7_numeric(profile: ColumnProfile) -> bool:
    if profile.data_type.upper() not in _NUMERIC_TYPES:
        return False
    if profile.length != 7:
        return False
    scale = 0 if profile.scale is None else profile.scale
    return scale == 0


def _is_valid_yyyymmdd(value: Any) -> bool:
    text = _digit_text(value, width=8)
    if text is None:
        return False
    try:
        datetime.strptime(text, "%Y%m%d")
    except ValueError:
        return False
    return True


def _is_valid_cyymmdd(value: Any) -> bool:
    try:
        decode_cyymmdd(value)
    except (TypeError, ValueError):
        return False
    return True


def _cyymmdd_text(value: Any) -> str:
    text = _digit_text(value, width=7)
    if text is None:
        raise ValueError(f"not a CYYMMDD value: {value!r}")
    if text[0] not in {"0", "1"}:
        raise ValueError(f"invalid century digit in CYYMMDD: {value!r}")
    return text


def _digit_text(value: Any, width: int) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        text = str(value)
    elif isinstance(value, float) and value.is_integer():
        text = str(int(value))
    elif isinstance(value, str) and value.strip().isdigit():
        text = value.strip()
    else:
        return None
    if len(text) > width:
        return None
    return text.zfill(width)
