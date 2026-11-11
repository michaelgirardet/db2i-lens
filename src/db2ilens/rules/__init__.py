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
    suggest_long_name,
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

# Instantiated registry used by the scan pipeline.
RULES: list[Rule] = [rule_cls() for rule_cls in ALL_RULES]

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
    "RULES",
    "Rule",
    "Severity",
    "YnFlagRule",
    "ZeroSentinelRule",
    "suggest_long_name",
]
