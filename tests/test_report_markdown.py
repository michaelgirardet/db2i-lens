"""E2E: scan fixtures then generate a Markdown discovery report."""

from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from db2ilens.cli import cli

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_erp"
GOLDEN_PATH = Path(__file__).parent / "golden" / "scan_mini_erp.yaml"


def test_report_markdown_covers_all_golden_findings(tmp_path: Path) -> None:
    scan_path = tmp_path / "scan.yaml"
    report_path = tmp_path / "rapport.md"
    runner = CliRunner()

    scan = runner.invoke(
        cli,
        ["scan", "--offline", str(FIXTURE_DIR), "--out", str(scan_path)],
    )
    assert scan.exit_code == 0, scan.output

    result = runner.invoke(
        cli,
        ["report", str(scan_path), "--format", "markdown", "--out", str(report_path)],
    )
    assert result.exit_code == 0, result.output
    assert report_path.is_file()

    markdown = report_path.read_text(encoding="utf-8")

    # Badges and anchors.
    assert "🔴 critical" in markdown
    assert "🟡 warning" in markdown
    assert "🔵 info" in markdown
    for table in ("ARTICLES", "CLIENTS", "COMMANDES", "LIGNES_CMD"):
        assert f"[`{table}`](#table-{table.lower()})" in markdown
        assert f'<a id="table-{table.lower()}"></a>' in markdown or (
            f"# Table `{table}`" in markdown and f"table-{table.lower()}" in markdown
        )

    # Every golden finding rule_id appears in the report.
    golden = yaml.safe_load(GOLDEN_PATH.read_text(encoding="utf-8"))
    golden_rule_ids: set[str] = set()
    for table in golden["tables"]:
        for column in table["columns"]:
            for finding in column["findings"]:
                golden_rule_ids.add(finding["rule_id"])
                assert finding["rule_id"] in markdown
                if finding.get("suggested_fix"):
                    assert finding["suggested_fix"] in markdown

    assert golden_rule_ids == {
        "R01",
        "R02",
        "R03",
        "R04",
        "R05",
        "R06",
        "R07",
        "R08",
    }

    # SQL fixes are in fenced code blocks.
    assert "```sql" in markdown

    # Migration priorities section exists and lists critical first.
    assert "## Migration priorities" in markdown
    priorities_section = markdown.split("## Migration priorities", 1)[1]
    critical_pos = priorities_section.find("🔴 critical")
    warning_pos = priorities_section.find("🟡 warning")
    assert critical_pos != -1
    assert warning_pos != -1
    assert critical_pos < warning_pos

    # Decoded names appendix.
    assert "## Decoded column names" in markdown
    assert "customer_name" in markdown


def test_report_help_lists_markdown_format() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["report", "--help"])
    assert result.exit_code == 0
    assert "markdown" in result.output
