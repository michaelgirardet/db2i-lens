"""Structural validation of the scan.yaml contract (beyond golden equality)."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
import yaml

from db2ilens.rules import RULES
from db2ilens.scan import SCAN_FORMAT_VERSION, scan_offline, validate_scan_document

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_erp"
GOLDEN_PATH = Path(__file__).parent / "golden" / "scan_mini_erp.yaml"


def _fixture_scan_dict() -> dict[str, Any]:
    return asdict(scan_offline(FIXTURE_DIR, sample_rows=5000))


def _first_finding(document: dict[str, Any]) -> dict[str, Any]:
    for table in document["tables"]:
        for column in table["columns"]:
            findings = column["findings"]
            if findings:
                return findings[0]
    raise AssertionError("fixture scan has no findings")


def test_fixture_scan_passes_structural_validation() -> None:
    document = _fixture_scan_dict()
    validate_scan_document(document)


def test_golden_scan_passes_structural_validation() -> None:
    document = yaml.safe_load(GOLDEN_PATH.read_text(encoding="utf-8"))
    validate_scan_document(document)


def test_validation_rejects_missing_required_root_field() -> None:
    document = _fixture_scan_dict()
    del document["summary"]
    with pytest.raises(ValueError, match="summary"):
        validate_scan_document(document)


def test_validation_rejects_unknown_severity() -> None:
    document = _fixture_scan_dict()
    finding = _first_finding(document)
    finding["severity"] = "fatal"
    with pytest.raises(ValueError, match="severity"):
        validate_scan_document(document)


def test_validation_rejects_unknown_rule_id() -> None:
    document = _fixture_scan_dict()
    finding = _first_finding(document)
    finding["rule_id"] = "R99"
    with pytest.raises(ValueError, match="R99"):
        validate_scan_document(document)


def test_validation_rejects_wrong_version_type() -> None:
    document = _fixture_scan_dict()
    document["version"] = 1
    with pytest.raises(ValueError, match="version"):
        validate_scan_document(document)


def test_known_rule_ids_match_rules_registry() -> None:
    """Invariant documented in SCAN_CONTRACT: rule_ids ⊆ RULES registry."""
    known = {rule.id for rule in RULES}
    document = _fixture_scan_dict()
    validate_scan_document(document)
    for table in document["tables"]:
        for column in table["columns"]:
            for finding in column["findings"]:
                assert finding["rule_id"] in known


def test_validation_rejects_missing_column_metadata_field() -> None:
    document = deepcopy(_fixture_scan_dict())
    del document["tables"][0]["columns"][0]["metadata"]["nullable"]
    with pytest.raises(ValueError, match="nullable"):
        validate_scan_document(document)


def test_scan_format_version_is_documented_constant() -> None:
    assert SCAN_FORMAT_VERSION == "1.0"
    document = _fixture_scan_dict()
    assert document["version"] == SCAN_FORMAT_VERSION
