# Db2iLens Project Rules

## Context
Read-only Python tool that profiles IBM i data and generates dbt.
Users work in French or English; code and identifiers are in English.

## Conventions
- Python 3.11+, strict typing (mypy), ruff formatting, mandatory pytest tests.
- All database access **must** go through `src/db2ilens/connector/`. No SQL outside this directory.
- No query must modify the source: **SELECT only**, never DML/DDL.
- Each detection rule inherits from `rules/base.py::Rule` (id, severity, detect, fix).
- Passwords are **never** written in code, logs, or test files.
- dbt templates are Jinja2 templates in `db2ilens/dbtgen/templates/`, never hardcoded SQL in Python.

## Before Completing a Task
1. `ruff check . && mypy src && pytest` must pass.
2. Every new rule **must** come with a fixture that triggers it and a unit test.
3. Every new CLI command **must** come with an offline end-to-end test.