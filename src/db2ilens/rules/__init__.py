"""Legacy quirk detection rules."""

from db2ilens.rules.base import Finding, Rule, Severity
from db2ilens.rules.date_rules import IbmCenturyDateRule, NumericDateYYYYMMDDRule
from db2ilens.rules.encoding_rules import Ccsid65535Rule
from db2ilens.rules.naming_rules import (
    ABBREVIATIONS,
    BlankAsNullRule,
    MultiValueColumnRule,
    ObscureShortNameRule,
    YnFlagRule,
)
from db2ilens.rules.numeric_rules import ImplicitPackedDecimalRule, ZeroSentinelRule

ALL_RULES: list[type[Rule]] = [
    NumericDateYYYYMMDDRule,
    IbmCenturyDateRule,
    Ccsid65535Rule,
    ImplicitPackedDecimalRule,
    BlankAsNullRule,
    ObscureShortNameRule,
    MultiValueColumnRule,
    YnFlagRule,
    ZeroSentinelRule,
]

__all__ = [
    "ABBREVIATIONS",
    "ALL_RULES",
    "BlankAsNullRule",
    "Ccsid65535Rule",
    "Finding",
    "IbmCenturyDateRule",
    "ImplicitPackedDecimalRule",
    "MultiValueColumnRule",
    "NumericDateYYYYMMDDRule",
    "ObscureShortNameRule",
    "Rule",
    "Severity",
    "YnFlagRule",
    "ZeroSentinelRule",
]
