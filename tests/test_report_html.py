"""E2E: scan fixtures then generate a self-contained HTML discovery report."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import yaml
from click.testing import CliRunner

from db2ilens.cli import cli

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_erp"
GOLDEN_PATH = Path(__file__).parent / "golden" / "scan_mini_erp.yaml"


class _TagBalanceParser(HTMLParser):
    """Track open/close tags; void elements do not need a closer."""

    _VOID = frozenset(
        {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }
    )

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in self._VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack:
            self.errors.append(f"unexpected </{tag}>")
            return
        expected = self.stack.pop()
        if expected != tag:
            self.errors.append(f"expected </{expected}>, got </{tag}>")


def test_report_html_e2e_golden_structure(tmp_path: Path) -> None:
    scan_path = tmp_path / "scan.yaml"
    report_path = tmp_path / "rapport.html"
    runner = CliRunner()

    scan = runner.invoke(
        cli,
        ["scan", "--offline", str(FIXTURE_DIR), "--out", str(scan_path)],
    )
    assert scan.exit_code == 0, scan.output

    result = runner.invoke(
        cli,
        ["report", str(scan_path), "--format", "html", "--out", str(report_path)],
    )
    assert result.exit_code == 0, result.output
    assert report_path.is_file()

    html = report_path.read_text(encoding="utf-8")

    assert html.lstrip().lower().startswith("<!doctype html>")
    assert "<html" in html.lower()
    assert "</html>" in html.lower()

    # Four fixture tables + navigation anchors.
    for table in ("ARTICLES", "CLIENTS", "COMMANDES", "LIGNES_CMD"):
        assert table in html
        assert f'id="table-{table.lower()}"' in html
        assert f'href="#table-{table.lower()}"' in html

    golden = yaml.safe_load(GOLDEN_PATH.read_text(encoding="utf-8"))
    golden_rule_ids: set[str] = set()
    for table in golden["tables"]:
        for column in table["columns"]:
            for finding in column["findings"]:
                golden_rule_ids.add(finding["rule_id"])
                assert finding["rule_id"] in html

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

    # Severity dashboard cards.
    assert "critical" in html.lower()
    assert "warning" in html.lower()
    assert "info" in html.lower()

    # Migration priorities table + sequential numbering (not all "1.").
    assert "Migration priorities" in html
    assert re.search(r">\s*1\s*<", html) is not None
    assert re.search(r">\s*2\s*<", html) is not None

    # Business line for R03 before the technical SQL.
    assert "Character data stored in binary encoding" in html
    assert "must be translated before any export" in html

    # No external network references (anchors and inline CSS only).
    for match in re.finditer(r"https?://[^\s\"']+", html):
        raise AssertionError(f"external URL found in HTML report: {match.group(0)}")

    parser = _TagBalanceParser()
    parser.feed(html)
    parser.close()
    assert parser.stack == [], f"unclosed tags: {parser.stack}"
    assert parser.errors == [], f"tag errors: {parser.errors}"


def test_report_help_lists_html_format() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["report", "--help"])
    assert result.exit_code == 0
    assert "html" in result.output
