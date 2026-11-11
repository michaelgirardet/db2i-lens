"""Base types for legacy-quirk detection rules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(Enum):
    """Finding severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Finding:
    """A single rule hit on a column (or table)."""

    rule_id: str
    table: str
    column: str
    severity: Severity
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
    suggested_fix: str | None = None


class Rule(ABC):
    """Interface every detection rule must implement."""

    id: str
    name: str
    severity: Severity

    @abstractmethod
    def detect(self, column_profile: object) -> list[Finding]:
        """Inspect a column profile and return zero or more findings."""

    @abstractmethod
    def fix(self, finding: Finding) -> str | None:
        """Return dbt SQL (or expression) that remediates the finding, if any."""
