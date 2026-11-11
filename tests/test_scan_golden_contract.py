"""Golden-file contract for scan.yaml schema stability."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import yaml

from db2ilens.scan import scan_offline, write_scan_yaml

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_erp"
GOLDEN_PATH = Path(__file__).parent / "golden" / "scan_mini_erp.yaml"
STABLE_GENERATED_AT = "STABLE"
STABLE_SOURCE = "tests/fixtures/mini_erp"


def test_scan_yaml_matches_golden_contract(tmp_path: Path) -> None:
    """Fail loudly when the scan.yaml schema/content drifts without updating the golden."""
    result = scan_offline(FIXTURE_DIR, sample_rows=5000)
    stabilized = replace(
        result,
        generated_at=STABLE_GENERATED_AT,
        source=STABLE_SOURCE,
    )

    actual_path = tmp_path / "scan.yaml"
    write_scan_yaml(stabilized, actual_path)

    actual = yaml.safe_load(actual_path.read_text(encoding="utf-8"))
    expected = yaml.safe_load(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert actual == expected, (
        "scan.yaml contract drifted from tests/golden/scan_mini_erp.yaml. "
        "If the change is intentional, regenerate the golden file and document "
        "the schema change in the commit."
    )


def test_golden_scan_file_exists_and_has_expected_shape() -> None:
    assert GOLDEN_PATH.is_file()
    data = yaml.safe_load(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert data["version"] == "1.0"
    assert data["generated_at"] == STABLE_GENERATED_AT
    assert data["source"] == STABLE_SOURCE
    assert data["summary"]["finding_count"] == 6
    assert {table["name"] for table in data["tables"]} == {
        "ARTICLES",
        "CLIENTS",
        "COMMANDES",
        "LIGNES_CMD",
    }
