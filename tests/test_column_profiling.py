"""TDD: column profiling stats on mini-ERP fixtures."""

from __future__ import annotations

from pathlib import Path

from db2ilens.connector.offline import load_export
from db2ilens.profiler.sampling import profile_column, profile_table

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_erp"


def test_profile_actflg_distinct_and_top_values() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["CLIENTS"], "ACTFLG")

    assert profile.table == "CLIENTS"
    assert profile.column == "ACTFLG"
    assert profile.row_count == 5
    assert profile.distinct_count == 2
    assert profile.null_count == 0
    assert profile.blank_count == 0
    assert profile.top_values[0] == ("Y", 3)
    assert profile.top_values[1] == ("N", 2)


def test_profile_cusname_counts_blanks() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["CLIENTS"], "CUSNAME")

    assert profile.blank_count == 2
    assert profile.null_count == 0
    assert profile.distinct_count == 5  # two distinct blank strings + 3 names


def test_profile_orddte_min_max() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["COMMANDES"], "ORDDTE")

    assert profile.min_value == 20260115
    assert profile.max_value == 20261231
    assert profile.distinct_count == 5


def test_profile_stdprc_zero_sentinel_stats() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["ARTICLES"], "STDPRC")

    assert profile.min_value == 0
    assert profile.max_value == 4599
    assert ("0", 2) in {(str(v), c) for v, c in profile.top_values} or (0, 2) in profile.top_values


def test_profile_respects_sample_rows() -> None:
    export = load_export(FIXTURE_DIR)
    profile = profile_column(export.tables["CLIENTS"], "ACTFLG", sample_rows=2)

    assert profile.row_count == 2
    assert profile.distinct_count == 2
    assert profile.top_values == [("Y", 1), ("N", 1)]


def test_profile_table_returns_one_profile_per_column() -> None:
    export = load_export(FIXTURE_DIR)
    profiles = profile_table(export.tables["CLIENTS"])

    assert [p.column for p in profiles] == ["CUSID", "CUSNAME", "ACTFLG", "PHNNUM"]
    assert all(p.data_type for p in profiles)
    assert profiles[1].ccsid == 65535
