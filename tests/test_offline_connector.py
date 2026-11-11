"""TDD: offline connector loads mini-ERP CSV + schema.yaml."""

from __future__ import annotations

from pathlib import Path

import pytest

from db2ilens.connector.offline import OfflineExportError, load_export

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_erp"


def test_load_export_reads_schema_name_and_four_tables() -> None:
    export = load_export(FIXTURE_DIR)

    assert export.schema_name == "DEMO_LIB"
    assert set(export.tables) == {"CLIENTS", "COMMANDES", "LIGNES_CMD", "ARTICLES"}


def test_load_export_exposes_column_metadata_from_schema_yaml() -> None:
    export = load_export(FIXTURE_DIR)
    clients = export.tables["CLIENTS"]

    assert [c.name for c in clients.columns] == ["CUSID", "CUSNAME", "ACTFLG", "PHNNUM"]
    cusname = clients.columns[1]
    assert cusname.data_type == "CHAR"
    assert cusname.length == 30
    assert cusname.nullable is False
    assert cusname.ccsid == 65535


def test_load_export_loads_sampleable_rows() -> None:
    export = load_export(FIXTURE_DIR)
    clients = export.tables["CLIENTS"]

    assert len(clients.rows) == 5
    assert clients.rows[0]["CUSID"] == "C0001"
    assert clients.rows[0]["ACTFLG"] == "Y"
    # Blank-ish CUSNAME preserved as string (not dropped)
    assert isinstance(clients.rows[1]["CUSNAME"], str)
    assert clients.rows[1]["CUSNAME"].strip() == ""


def test_load_export_parses_numeric_columns_from_csv() -> None:
    export = load_export(FIXTURE_DIR)
    commandes = export.tables["COMMANDES"]

    assert commandes.rows[0]["ORDDTE"] == 20260115
    assert isinstance(commandes.rows[0]["ORDDTE"], int)


def test_load_export_missing_schema_raises() -> None:
    with pytest.raises(OfflineExportError, match="schema.yaml"):
        load_export(Path("/tmp/does-not-exist-db2ilens"))
