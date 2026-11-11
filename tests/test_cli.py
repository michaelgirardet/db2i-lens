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


def test_scan_not_implemented() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--offline", "examples/mini_erp"])
    assert result.exit_code == 1
    assert "not implemented in P0" in result.output
