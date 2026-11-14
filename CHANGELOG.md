# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-11-13

### Added

- **P0: Project skeleton** - Initial repository structure with CLI, Rule base class, mini-ERP fixtures, and GitHub Actions CI
- **P1: Core scanning** - Offline connector (CSV/Parquet), metadata profiling, sampling, and initial rules (R01, R05, R08)
- **P2: Rule expansion** - Additional detection rules (R02-R04, R06, R07) with abbreviation dictionary
- **P3: Reporting** - Markdown and HTML discovery reports with stable `scan.yaml` contract (version 1.0)
- **P4: dbt generation** - Complete dbt project generator with Jinja2 templates (staging + cleaning models), e2e testing with DuckDB
- **P5: JDBC connector** - JT400 JDBC connector for live IBM i connections, PUB400 integration guide and documentation

### Detection Rules Implemented

| ID | Rule | Description |
|---|---|---|
| R01 | Numeric Date (YYYYMMDD) | Detects DEC(8,0) columns with YYYYMMDD date format |
| R02 | IBM Date (CYYMMDD) | Detects DEC(7,0) columns with IBM CYYMMDD format (century digit) |
| R03 | EBCDIC/CCSID 65535 | Detects CCSID 65535 columns (EBCDIC binary) |
| R04 | Packed Decimal | Detects DEC columns with implied scale (packed decimals) |
| R05 | Blank as NULL | Detects columns where blanks/empty strings should be NULL |
| R06 | Short Column Names | Detects column names <= 10 chars without comment, suggests long names |
| R07 | Multi-value Columns | Detects columns with recurring separators (comma, semicolon, pipe) |
| R08 | Y/N or 1/0 Flags | Detects CHAR(1) columns with Y/N or 1/0 flag values |
| R09 | Sentinel Zero | Detects frequent zero values that should be NULL |

### CLI Commands

- `db2ilens scan` - Scan IBM i (JDBC) or offline export, produces `scan.yaml`
- `db2ilens report` - Generate discovery report (Markdown or HTML) from `scan.yaml`
- `db2ilens gen-dbt` - Generate dbt project from `scan.yaml`

### Features

- **Offline mode** - Full functionality without IBM i access using CSV/Parquet exports
- **PUB400 support** - Step-by-step guide for testing with free PUB400 accounts
- **Security** - Passwords via `--password-stdin` or `DB2ILENS_PASSWORD` env var only, never in CLI args
- **Quality gates** - ruff linting, mypy strict typing, pytest coverage
- **Demo path** - Reproducible offline demo with mini-ERP fixtures

### Mini-ERP Fixtures

Complete test dataset with intentional legacy quirks:
- CLIENTS table (CUSID, CUSNAME with CCSID 65535, ACTFLG Y/N flag)
- COMMANDES table (ORDDTE numeric date, ORDSTS status)
- LIGNES_CMD table (PRC packed decimal, TAGS multi-value)
- ARTICLES table (CRTDTE IBM date, STDPRC sentinel zero)

---

## [Unreleased]

### Backlog (P6)

- R10: Implicit relationships detection between tables
- LLM-based column naming suggestions
- Postgres and Snowflake target support for dbt generation
- Additional date format detection
- Enhanced multi-value column splitting

---

[0.1.0]: https://github.com/michaelgirardet/db2i-lens/compare/main...0.1.0
