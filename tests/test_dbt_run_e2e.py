"""E2E #16: generated dbt project runs and tests cleanly on DuckDB."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import duckdb
from click.testing import CliRunner

from db2ilens.cli import cli

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_erp"


def test_generated_dbt_project_run_and_test_semantics(tmp_path: Path) -> None:
    scan_path = tmp_path / "scan.yaml"
    project_dir = tmp_path / "dbt_project"
    runner = CliRunner()

    scan = runner.invoke(
        cli,
        ["scan", "--offline", str(FIXTURE_DIR), "--out", str(scan_path)],
    )
    assert scan.exit_code == 0, scan.output

    generated = runner.invoke(
        cli,
        ["gen-dbt", str(scan_path), "--out", str(project_dir), "--target", "duckdb"],
    )
    assert generated.exit_code == 0, generated.output

    # Activate the example profile without hand-editing generated models.
    shutil.copy2(project_dir / "profiles.yml.example", project_dir / "profiles.yml")

    env = os.environ.copy()
    env["DBT_PROFILES_DIR"] = str(project_dir)

    started = time.monotonic()
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
    elapsed = time.monotonic() - started
    assert elapsed < 120, f"dbt run+test took too long: {elapsed:.1f}s"

    db_path = project_dir / "db2ilens_generated.duckdb"
    assert db_path.is_file()
    con = duckdb.connect(str(db_path), read_only=True)

    # R01 semantic: numeric YYYYMMDD → real dates (ORDDTE kept as orddte).
    order_dates = {
        row[0]: row[1]
        for row in con.execute(
            "select order_identifier, cast(orddte as varchar) "
            "from main.commandes order by 1"
        ).fetchall()
    }
    assert order_dates["O1001"].startswith("2026-01-15")
    assert order_dates["O1002"].startswith("2026-02-28")

    # R08 semantic: ACTFLG → boolean.
    flags = con.execute(
        "select active_flag from main.clients where customer_identifier = 'C0001'"
    ).fetchone()
    assert flags is not None
    assert flags[0] is True

    # R05 semantic: blank customer names become NULL.
    blanks = con.execute(
        "select count(*) from main.clients "
        "where customer_name is not null and trim(customer_name) = ''"
    ).fetchone()
    assert blanks is not None
    assert blanks[0] == 0
    null_names = con.execute(
        "select count(*) from main.clients where customer_name is null"
    ).fetchone()
    assert null_names is not None
    assert null_names[0] >= 2

    con.close()
