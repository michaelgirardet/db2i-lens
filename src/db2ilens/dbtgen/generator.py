"""Generate a dbt project from a scan artifact using Jinja2 templates only."""

from __future__ import annotations

import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

from db2ilens.dbtgen.context import ProjectContext, build_project_context
from db2ilens.scan import validate_scan_document


def generate_dbt_project(scan_path: Path, out_dir: Path, target: str = "duckdb") -> None:
    """Write staging/mart models, sources.yml, and dbt_project.yml."""
    scan = yaml.safe_load(scan_path.read_text(encoding="utf-8"))
    validate_scan_document(scan)
    context = build_project_context(scan, target=target)

    out_dir.mkdir(parents=True, exist_ok=True)
    staging_dir = out_dir / "models" / "staging"
    marts_dir = out_dir / "models" / "marts"
    data_dir = out_dir / "data"
    staging_dir.mkdir(parents=True, exist_ok=True)
    marts_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    env = _jinja_env()
    payload = _template_payload(context)

    _write(out_dir / "dbt_project.yml", env.get_template("dbt_project.yml.j2").render(payload))
    _write(
        out_dir / "profiles.yml.example",
        env.get_template("profiles.yml.example.j2").render(payload),
    )
    _write(out_dir / "models" / "sources.yml", env.get_template("sources.yml.j2").render(payload))
    _write(
        staging_dir / "schema.yml",
        env.get_template("staging_schema.yml.j2").render(payload),
    )
    _write(
        marts_dir / "schema.yml",
        env.get_template("marts_schema.yml.j2").render(payload),
    )

    for table in context.tables:
        table_payload = {**payload, "table": asdict(table)}
        _write(
            staging_dir / f"{table.staging_name}.sql",
            env.get_template("staging_model.sql.j2").render(table_payload),
        )
        _write(
            marts_dir / f"{table.model_name}.sql",
            env.get_template("mart_model.sql.j2").render(table_payload),
        )

    _copy_offline_data(scan, data_dir, context)


def _jinja_env() -> Environment:
    return Environment(
        loader=PackageLoader("db2ilens.dbtgen", "templates"),
        undefined=StrictUndefined,
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _template_payload(context: ProjectContext) -> dict[str, Any]:
    return {
        "target": context.target,
        "schema_name": context.schema_name,
        "source_name": context.source_name,
        "project_name": context.project_name,
        "profile_name": context.profile_name,
        "tables": [asdict(table) for table in context.tables],
        "relationships": [asdict(rel) for rel in context.relationships],
    }


def _copy_offline_data(
    scan: dict[str, Any],
    data_dir: Path,
    context: ProjectContext,
) -> None:
    source = Path(str(scan.get("source", "")))
    if not source.is_dir():
        return
    for table in context.tables:
        candidate = source / f"{table.name}.csv"
        if candidate.is_file():
            shutil.copy2(candidate, data_dir / f"{table.name}.csv")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = content if content.endswith("\n") else content + "\n"
    path.write_text(text, encoding="utf-8")
