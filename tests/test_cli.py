"""CLI smoke tests (help must work in P0)."""

from __future__ import annotations

from click.testing import CliRunner

from db2ilens.cli import cli


def test_root_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "scan" in result.output
    assert "report" in result.output
    assert "gen-dbt" in result.output


def test_scan_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--offline" in result.output
    assert "--password-stdin" in result.output
    assert "--sample-rows" in result.output
    assert "--tables" in result.output


def test_report_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["report", "--help"])
    assert result.exit_code == 0
    assert "--format" in result.output


def test_gen_dbt_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["gen-dbt", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output


def test_scan_jdbc_requires_host_user_schema() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--host", "example.com", "--user", "QUSER"])
    assert result.exit_code == 2
    assert "--schema" in result.output


def test_scan_jdbc_requires_password(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("DB2ILENS_PASSWORD", raising=False)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "scan",
            "--host",
            "example.com",
            "--user",
            "QUSER",
            "--schema",
            "DEMO_LIB",
        ],
    )
    assert result.exit_code == 1
    assert "password" in result.output.lower()
