"""Generate a dbt project from a scan artifact (stub in P0)."""

from __future__ import annotations

from pathlib import Path


def generate_dbt_project(scan_path: Path, out_dir: Path, target: str = "duckdb") -> None:
    """Write staging/mart models, sources.yml, and dbt_project.yml."""
    raise NotImplementedError("dbt generator is not implemented in P0")
