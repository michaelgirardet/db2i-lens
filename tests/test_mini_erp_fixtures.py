"""Smoke tests for the offline mini-ERP fixtures."""

from __future__ import annotations

from pathlib import Path

import yaml

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_erp"
EXAMPLE_DIR = Path(__file__).resolve().parents[1] / "examples" / "mini_erp"
TABLES = ("CLIENTS", "COMMANDES", "LIGNES_CMD", "ARTICLES")


def test_fixture_csvs_exist_with_header_and_rows() -> None:
    for name in TABLES:
        path = FIXTURE_DIR / f"{name}.csv"
        assert path.is_file(), f"missing fixture {path}"
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) >= 2, f"{path} needs header + ≥1 data row"
        assert "," in lines[0]


def test_schema_yaml_loads_and_lists_tables() -> None:
    schema_path = FIXTURE_DIR / "schema.yaml"
    data = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    assert data["schema"] == "DEMO_LIB"
    assert set(data["tables"]) == set(TABLES)
    assert set(data["traps"]) >= {"R01", "R02", "R05", "R06", "R08"}


def test_example_mirror_matches_fixture_tables() -> None:
    for name in TABLES:
        assert (EXAMPLE_DIR / f"{name}.csv").is_file()
    assert (EXAMPLE_DIR / "schema.yaml").is_file()
