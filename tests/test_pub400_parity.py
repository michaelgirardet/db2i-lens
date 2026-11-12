"""#18 PUB400 end-to-end parity — excluded from default CI (marker: integration)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import duckdb
import pytest
import yaml

from db2ilens.connector.ibmi_jdbc import JdbcConfigError, parse_jdbc_source
from db2ilens.dbtgen import generate_dbt_project
from db2ilens.report.html import render_html
from db2ilens.scan import scan_jdbc, validate_scan_document, write_scan_yaml

GOLDEN_PATH = Path(__file__).parent / "golden" / "scan_mini_erp.yaml"
MINI_ERP_TABLES = frozenset({"CLIENTS", "COMMANDES", "ARTICLES", "LIGNES_CMD"})
MLENS_PREFIX = "MLENS_"
# Personal PUB400 library may hold unrelated objects — always filter demo tables.
DEFAULT_PUB400_TABLES = "MLENS_%"

_HAS_PUB400 = bool(
    (os.environ.get("PUB400_USER") or os.environ.get("DB2ILENS_USER"))
    and (os.environ.get("PUB400_PASSWORD") or os.environ.get("DB2ILENS_PASSWORD"))
)


def _credentials() -> tuple[str, str, str, str]:
    user = os.environ.get("PUB400_USER") or os.environ.get("DB2ILENS_USER") or ""
    password = os.environ.get("PUB400_PASSWORD") or os.environ.get("DB2ILENS_PASSWORD") or ""
    # Free accounts cannot CREATE SCHEMA — default to the personal library.
    schema = (
        os.environ.get("PUB400_SCHEMA") or os.environ.get("DB2ILENS_SCHEMA") or user
    )
    host = os.environ.get("PUB400_HOST", "pub400.com")
    return host, user, password, schema


def _tables_filter() -> str:
    return os.environ.get("PUB400_TABLES") or DEFAULT_PUB400_TABLES


def _strip_mlens_prefix(name: str) -> str:
    if name.startswith(MLENS_PREFIX):
        return name[len(MLENS_PREFIX) :]
    return name


def _finding_keys(scan: dict, *, strip_prefix: bool = False) -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()
    for table in scan.get("tables", []):
        table_name = str(table.get("name", ""))
        if strip_prefix:
            table_name = _strip_mlens_prefix(table_name)
        for column in table.get("columns", []):
            column_name = str(column.get("name", ""))
            for finding in column.get("findings", []):
                keys.add((str(finding.get("rule_id", "")), table_name, column_name))
    return keys


def _mini_erp_findings(scan: dict, *, strip_prefix: bool = False) -> set[tuple[str, str, str]]:
    return {
        key
        for key in _finding_keys(scan, strip_prefix=strip_prefix)
        if key[1] in MINI_ERP_TABLES
    }


def test_parse_jdbc_source_unit() -> None:
    host, schema = parse_jdbc_source("jdbc:as400://pub400.com/DEMO_LENS")
    assert host == "pub400.com"
    assert schema == "DEMO_LENS"


@pytest.mark.integration
@pytest.mark.skipif(not _HAS_PUB400, reason="needs live PUB400")
def test_pub400_scan_validates_and_matches_golden_minus_r04(tmp_path: Path) -> None:
    host, user, password, schema = _credentials()
    tables = _tables_filter()
    try:
        result = scan_jdbc(
            host=host,
            user=user,
            password=password,
            schema=schema,
            sample_rows=5000,
            tables=tables,
        )
    except (JdbcConfigError, OSError, RuntimeError) as exc:
        pytest.skip(f"PUB400 JDBC unavailable: {exc}")

    scan_path = tmp_path / "scan_pub400.yaml"
    write_scan_yaml(result, scan_path)
    document = yaml.safe_load(scan_path.read_text(encoding="utf-8"))
    validate_scan_document(document)

    assert document["mode"] == "jdbc"
    # Strip MLENS_ before comparing to the offline golden (unprefixed names).
    table_names = {
        _strip_mlens_prefix(str(table["name"])) for table in document["tables"]
    }
    missing_tables = MINI_ERP_TABLES - table_names
    assert not missing_tables, (
        f"mini-ERP tables missing in {schema} (filter={tables!r}): "
        f"{sorted(missing_tables)}. "
        "Load examples/mini_erp/pub400_setup.sql into PUB400_SCHEMA first."
    )

    golden = yaml.safe_load(GOLDEN_PATH.read_text(encoding="utf-8"))
    golden_keys = _mini_erp_findings(golden)
    jdbc_keys = _mini_erp_findings(document, strip_prefix=True)

    # Known JDBC/offline divergence (documented in pub400_setup.sql + README):
    # R04 depends on implied_scale from offline schema.yaml — invisible in
    # SYSCOLUMNS2, so JDBC never raises R04 on LIGNES_CMD.PRC.
    assert ("R04", "LIGNES_CMD", "PRC") not in jdbc_keys
    expected = {key for key in golden_keys if key[0] != "R04"}
    missing = expected - jdbc_keys
    assert not missing, f"JDBC scan missing expected findings: {sorted(missing)}"


@pytest.mark.integration
@pytest.mark.skipif(not _HAS_PUB400, reason="needs live PUB400")
def test_pub400_report_and_dbt_semantics(tmp_path: Path) -> None:
    host, user, password, schema = _credentials()
    tables = _tables_filter()
    try:
        result = scan_jdbc(
            host=host,
            user=user,
            password=password,
            schema=schema,
            sample_rows=5000,
            tables=tables,
        )
    except (JdbcConfigError, OSError, RuntimeError) as exc:
        pytest.skip(f"PUB400 JDBC unavailable: {exc}")

    canonical = {_strip_mlens_prefix(table.name) for table in result.tables}
    if not canonical >= MINI_ERP_TABLES:
        pytest.skip("mini-ERP not loaded in PUB400_SCHEMA; skip dbt semantic check")

    scan_path = tmp_path / "scan_pub400.yaml"
    write_scan_yaml(result, scan_path)

    html_path = tmp_path / "rapport.html"
    render_html(scan_path, html_path)
    html = html_path.read_text(encoding="utf-8")
    assert "R03" in html
    assert "http://" not in html and "https://" not in html

    project_dir = tmp_path / "dbt_project"
    generate_dbt_project(scan_path, project_dir, target="duckdb")
    assert (project_dir / "data" / "MLENS_CLIENTS.csv").is_file()
    assert (project_dir / "data" / "MLENS_COMMANDES.csv").is_file()

    shutil.copy2(project_dir / "profiles.yml.example", project_dir / "profiles.yml")
    env = os.environ.copy()
    env["DBT_PROFILES_DIR"] = str(project_dir)

    run = subprocess.run(
        ["dbt", "run", "--project-dir", str(project_dir), "--profiles-dir", str(project_dir)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=project_dir,
    )
    assert run.returncode == 0, f"dbt run failed:\n{run.stdout}\n{run.stderr}"

    test = subprocess.run(
        ["dbt", "test", "--project-dir", str(project_dir), "--profiles-dir", str(project_dir)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=project_dir,
    )
    assert test.returncode == 0, f"dbt test failed:\n{test.stdout}\n{test.stderr}"

    db_path = project_dir / "db2ilens_generated.duckdb"
    con = duckdb.connect(str(db_path), read_only=True)
    order_dates = {
        row[0]: row[1]
        for row in con.execute(
            "select order_identifier, cast(orddte as varchar) from main.mlens_commandes"
        ).fetchall()
    }
    assert order_dates["O1001"].startswith("2026-01-15")
    flag = con.execute(
        "select active_flag from main.mlens_clients where customer_identifier = 'C0001'"
    ).fetchone()
    assert flag is not None and flag[0] is True
    null_names = con.execute(
        "select count(*) from main.mlens_clients where customer_name is null"
    ).fetchone()
    assert null_names is not None and null_names[0] >= 2
    con.close()
