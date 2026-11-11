"""CLI entry point for Db2iLens."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from db2ilens.connector.ibmi_jdbc import JdbcConfigError, resolve_password
from db2ilens.dbtgen import generate_dbt_project
from db2ilens.report.html import render_html
from db2ilens.report.markdown import render_markdown
from db2ilens.scan import scan_jdbc, scan_offline, write_scan_yaml


@click.group()
@click.version_option(package_name="db2ilens")
def cli() -> None:
    """Profile IBM i data and generate dbt cleaning models."""


@cli.command("scan")
@click.option("--host", default=None, help="IBM i hostname (JDBC mode).")
@click.option("--user", default=None, help="IBM i user profile.")
@click.option("--schema", default=None, help="Library / schema to scan.")
@click.option(
    "--password-stdin",
    is_flag=True,
    default=False,
    help=(
        "Read password from stdin (or use DB2ILENS_PASSWORD). "
        "Ignored in --offline mode."
    ),
)
@click.option(
    "--sample-rows",
    default=5000,
    show_default=True,
    type=int,
    help="Rows to sample per table.",
)
@click.option(
    "--offline",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Directory with CSV/Parquet export (offline mode).",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(path_type=Path),
    default=Path("scan.yaml"),
    show_default=True,
    help="Output scan artifact (YAML).",
)
def scan(
    host: str | None,
    user: str | None,
    schema: str | None,
    password_stdin: bool,
    sample_rows: int,
    offline: Path | None,
    out_path: Path,
) -> None:
    """Scan an IBM i schema or an offline export (one pass → scan.yaml)."""
    if offline is not None:
        if password_stdin:
            # Consume stdin so pipes don't hang; value is intentionally unused offline.
            sys.stdin.readline()
        result = scan_offline(offline, sample_rows=sample_rows)
        write_scan_yaml(result, out_path)
        click.echo(
            f"Wrote {out_path} "
            f"({result.summary.table_count} tables, "
            f"{result.summary.finding_count} findings)"
        )
        return

    if not host or not user or not schema:
        click.echo(
            "JDBC mode requires --host, --user, and --schema "
            "(or use --offline PATH).",
            err=True,
        )
        raise SystemExit(2)

    try:
        password = resolve_password(password_stdin=password_stdin)
        result = scan_jdbc(
            host=host,
            user=user,
            password=password,
            schema=schema,
            sample_rows=sample_rows,
        )
    except (JdbcConfigError, OSError, RuntimeError) as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1) from exc

    write_scan_yaml(result, out_path)
    click.echo(
        f"Wrote {out_path} "
        f"({result.summary.table_count} tables, "
        f"{result.summary.finding_count} findings)"
    )


@cli.command("report")
@click.argument("scan_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["markdown", "html"], case_sensitive=False),
    default="html",
    show_default=True,
    help="Report format.",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(path_type=Path),
    default=Path("rapport.html"),
    show_default=True,
    help="Output report path.",
)
def report(scan_file: Path, fmt: str, out_path: Path) -> None:
    """Generate a discovery report from a scan.yaml artifact."""
    normalized = fmt.lower()
    if normalized == "markdown":
        render_markdown(scan_file, out_path)
        click.echo(f"Wrote Markdown report to {out_path}")
        return

    if normalized == "html":
        render_html(scan_file, out_path)
        click.echo(f"Wrote HTML report to {out_path}")
        return

    click.echo(f"Report format {fmt!r} is not supported.", err=True)
    raise SystemExit(1)


@cli.command("gen-dbt")
@click.argument("scan_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--out",
    "out_path",
    type=click.Path(path_type=Path),
    default=Path("dbt_project"),
    show_default=True,
    help="Output directory for the generated dbt project.",
)
@click.option(
    "--target",
    type=click.Choice(["duckdb", "snowflake", "postgres"], case_sensitive=False),
    default="duckdb",
    show_default=True,
    help="dbt warehouse target.",
)
def gen_dbt(scan_file: Path, out_path: Path, target: str) -> None:
    """Generate a bronze/silver dbt project from a scan.yaml artifact."""
    if target.lower() != "duckdb":
        click.echo(
            f"Target {target!r} is not implemented yet; use --target duckdb.",
            err=True,
        )
        raise SystemExit(1)
    generate_dbt_project(scan_file, out_path, target=target.lower())
    click.echo(f"Wrote dbt project to {out_path}")


if __name__ == "__main__":
    cli()
