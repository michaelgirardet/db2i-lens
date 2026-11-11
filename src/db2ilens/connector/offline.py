"""Offline connector for CSV/Parquet exports (stub in P0)."""

from __future__ import annotations

from pathlib import Path


def load_export(path: Path) -> None:
    """Load tables from an offline export directory."""
    raise NotImplementedError("Offline connector is not implemented in P0")
