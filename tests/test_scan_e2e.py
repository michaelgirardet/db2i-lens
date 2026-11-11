"""E2E: db2ilens scan --offline produces a complete scan.yaml artifact."""

from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from db2ilens.cli import cli

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_erp"


def test_scan_offline_writes_complete_scan_yaml(tmp_path: Path) -> None:
    out_path = tmp_path / "scan.yaml"
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "scan",
            "--offline",
            str(FIXTURE_DIR),
            "--out",
            str(out_path),
            "--sample-rows",
            "5000",
            "--password-stdin",
        ],
        input="ignored-offline-password\n",
    )

    assert result.exit_code == 0, result.output
    assert out_path.is_file()

    data = yaml.safe_load(out_path.read_text(encoding="utf-8"))

    assert data["version"] == "1.0"
    assert "generated_at" in data
    assert data["mode"] == "offline"
    assert data["schema_name"] == "DEMO_LIB"

    summary = data["summary"]
    assert summary["table_count"] == 4
    assert summary["finding_count"] == 3
    assert summary["findings_by_severity"] == {
        "critical": 0,
        "warning": 2,
        "info": 1,
    }

    tables = {table["name"]: table for table in data["tables"]}
    assert set(tables) == {"CLIENTS", "COMMANDES", "LIGNES_CMD", "ARTICLES"}

    # Metadata present for every column.
    clients_cols = {col["name"]: col for col in tables["CLIENTS"]["columns"]}
    assert clients_cols["CUSNAME"]["metadata"]["data_type"] == "CHAR"
    assert clients_cols["CUSNAME"]["metadata"]["nullable"] is False
    assert clients_cols["CUSNAME"]["metadata"]["ccsid"] == 65535
    assert "stats" in clients_cols["CUSNAME"]
    assert clients_cols["CUSNAME"]["stats"]["blank_count"] == 2

    findings = _all_findings(data)
    by_key = {(f["rule_id"], f["table"], f["column"]): f for f in findings}

    assert set(by_key) == {
        ("R01", "COMMANDES", "ORDDTE"),
        ("R05", "CLIENTS", "CUSNAME"),
        ("R08", "CLIENTS", "ACTFLG"),
    }
    assert by_key[("R01", "COMMANDES", "ORDDTE")]["severity"] == "warning"
    assert by_key[("R05", "CLIENTS", "CUSNAME")]["severity"] == "warning"
    assert by_key[("R08", "CLIENTS", "ACTFLG")]["severity"] == "info"

    assert by_key[("R01", "COMMANDES", "ORDDTE")]["suggested_fix"] == (
        "TO_DATE(TO_CHAR(ORDDTE), 'YYYYMMDD')"
    )
    assert by_key[("R05", "CLIENTS", "CUSNAME")]["suggested_fix"] == (
        "NULLIF(TRIM(CUSNAME), '')"
    )
    assert "TRUE" in by_key[("R08", "CLIENTS", "ACTFLG")]["suggested_fix"]

    # Counter-examples must not produce findings.
    assert ("R01", "CLIENTS", "PHNNUM") not in by_key
    assert ("R05", "ARTICLES", "ARTDESC") not in by_key
    assert ("R08", "COMMANDES", "ORDSTS") not in by_key


def test_scan_help_documents_password_ignored_offline() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--help"])
    assert result.exit_code == 0
    # Click may wrap the help text across lines.
    assert "Ignored in --offline" in result.output
    assert "mode." in result.output


def _all_findings(data: dict[str, object]) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    tables = data["tables"]
    assert isinstance(tables, list)
    for table in tables:
        assert isinstance(table, dict)
        for column in table["columns"]:
            assert isinstance(column, dict)
            for finding in column["findings"]:
                assert isinstance(finding, dict)
                findings.append(
                    {
                        **finding,
                        "table": table["name"],
                        "column": column["name"],
                    }
                )
    return findings
