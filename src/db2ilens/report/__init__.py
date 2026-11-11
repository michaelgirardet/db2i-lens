"""Discovery report generators."""

from db2ilens.report.html import build_html_report, render_html
from db2ilens.report.markdown import build_markdown_report, render_markdown

__all__ = [
    "build_html_report",
    "build_markdown_report",
    "render_html",
    "render_markdown",
]
