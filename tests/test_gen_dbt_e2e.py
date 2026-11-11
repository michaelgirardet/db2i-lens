"""E2E: scan fixtures then generate a complete dbt project (#15)."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from db2ilens.cli import cli

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_erp"


def test_gen_dbt_creates_expected_project_layout_and_fixes(tmp_path: Path) -> None:
    scan_path = tmp_path / "scan.yaml"
    out_dir = tmp_path / "dbt_project"
    runner = CliRunner()

    scan = runner.invoke(
        cli,
        ["scan", "--offline", str(FIXTURE_DIR), "--out", str(scan_path)],
    )
    assert scan.exit_code == 0, scan.output

    result = runner.invoke(
        cli,
        [
            "gen-dbt",
            str(scan_path),
            "--out",
            str(out_dir),
            "--target",
            "duckdb",
        ],
    )
    assert result.exit_code == 0, result.output
    assert out_dir.is_dir()

    # Project skeleton.
    assert (out_dir / "dbt_project.yml").is_file()
    assert (out_dir / "profiles.yml.example").is_file()
    assert (out_dir / "models" / "sources.yml").is_file() or (
        out_dir / "models" / "staging" / "sources.yml"
    ).is_file() or (out_dir / "sources.yml").is_file()

    staging = out_dir / "models" / "staging"
    marts = out_dir / "models" / "marts"
    assert staging.is_dir()
    assert marts.is_dir()

    for table in ("clients", "commandes", "lignes_cmd", "articles"):
        assert (staging / f"stg_{table}.sql").is_file(), table
        assert (marts / f"{table}.sql").is_file(), table

    assert (staging / "schema.yml").is_file()
    assert (marts / "schema.yml").is_file()

    # Staging headers list findings.
    clients_stg = (staging / "stg_clients.sql").read_text(encoding="utf-8")
    assert "R03" in clients_stg
    assert "critical" in clients_stg.lower() or "CRITICAL" in clients_stg

    # Marts contain cleaning expressions (DuckDB-oriented via templates).
    clients_mart = (marts / "clients.sql").read_text(encoding="utf-8")
    assert "R05" in clients_mart
    assert "nullif" in clients_mart.lower()
    assert "R08" in clients_mart
    assert "R03" in clients_mart

    commandes_mart = (marts / "commandes.sql").read_text(encoding="utf-8")
    assert "R01" in commandes_mart
    assert "orddte" in commandes_mart.lower() or "order" in commandes_mart.lower()

    articles_mart = (marts / "articles.sql").read_text(encoding="utf-8")
    assert "R02" in articles_mart

    lignes_mart = (marts / "lignes_cmd.sql").read_text(encoding="utf-8")
    assert "R04" in lignes_mart

    # sources / schema document relationships and tests.
    sources_text = _read_sources(out_dir)
    assert "CUSID" in sources_text or "customer_identifier" in sources_text
    assert "relationships" in (marts / "schema.yml").read_text(encoding="utf-8")
    marts_schema = (marts / "schema.yml").read_text(encoding="utf-8")
    assert "not_null" in marts_schema
    assert "accepted_values" in marts_schema

    # Offline CSV raw data is packaged for DuckDB.
    data_dir = out_dir / "data"
    assert data_dir.is_dir()
    for name in ("CLIENTS.csv", "COMMANDES.csv", "LIGNES_CMD.csv", "ARTICLES.csv"):
        assert (data_dir / name).is_file(), name

    # No raw SQL modules under dbtgen Python (templates only) — smoke via files.
    templates = Path(__file__).resolve().parents[1] / "src" / "db2ilens" / "dbtgen" / "templates"
    assert templates.is_dir()
    assert any(templates.glob("*.j2")), "expected Jinja2 templates"


def _read_sources(out_dir: Path) -> str:
    candidates = [
        out_dir / "sources.yml",
        out_dir / "models" / "sources.yml",
        out_dir / "models" / "staging" / "sources.yml",
    ]
    for path in candidates:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    raise AssertionError("sources.yml not found in generated project")
