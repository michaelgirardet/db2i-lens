# Contributing to Db2iLens

Thank you for your interest in Db2iLens! This guide explains how to contribute to the project.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Installation](#installation)
- [Running Checks](#running-checks)
- [Commit Message Conventions](#commit-message-conventions)
- [Pull Request Process](#pull-request-process)
- [Adding a New Detection Rule](#adding-a-new-detection-rule)
- [Reporting a Bug or Requesting a Feature](#reporting-a-bug-or-requesting-a-feature)

---

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## How to Contribute

All contributions are welcome:

- **Bug reports**: Open an issue with a detailed description
- **Feature requests**: Share your ideas to improve Db2iLens
- **Pull Requests**: Propose fixes or improvements
- **Documentation**: Help improve the docs
- **Tests**: Add tests to cover new cases

---

## Installation

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Clone the Repository

```bash
git clone https://github.com/michaelgirardet/db2i-lens.git
cd db2i-lens
```

### Install Dependencies

```bash
# With uv (recommended)
uv sync

# Alternative with pip
pip install -e ".[dev]"
```

### Install the JT400 Driver (for JDBC mode)

The JT400 driver is not committed to the repository. For JDBC mode:

```bash
./scripts/fetch_jt400.sh
```

This downloads `jt400.jar` to `~/.db2ilens/jt400.jar`.

---

## Running Checks

Before submitting a Pull Request, ensure all checks pass:

```bash
# Linting (ruff)
uv run ruff check .

# Strict typing (mypy)
uv run mypy src

# Tests (excludes integration tests that require PUB400)
uv run pytest -m "not integration"

# All tests in one command
uv run ruff check . && uv run mypy src && uv run pytest -m "not integration"
```

Integration tests (which require PUB400 access) can be run manually:

```bash
# Requires DB2ILENS_USER, DB2ILENS_PASSWORD, etc. environment variables
uv run pytest -m integration
```

---

## Commit Message Conventions

We use [Conventional Commits](https://www.conventionalcommits.org/) to structure our commit messages.

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Commit Types

| Type | Usage |
|------|-------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Style changes (spacing, formatting, etc.) |
| `refactor` | Code refactoring without changing functionality |
| `test` | Adding or modifying tests |
| `chore` | Build, configuration changes, etc. |

### Examples

```bash
# New detection rule
git commit -m "feat(rules): add R10 implicit relationships detection"

# Bug fix
git commit -m "fix(connector): handle NULL values in JDBC mode"

# Documentation
git commit -m "docs: add JT400 setup guide"

# Refactoring
git commit -m "refactor(profiler): extract sampling logic into separate module"

# Tests
git commit -m "test: add golden fixtures for R09 rule"
```

---

## Pull Request Process

1. **Fork the repository** on your GitHub account
2. **Create a branch** for your change:
   ```bash
   git checkout -b feat/my-new-feature
   ```
3. **Make your changes** following project conventions
4. **Run the checks** (ruff, mypy, pytest)
5. **Commit your changes** with clear commit messages
6. **Push your branch**:
   ```bash
   git push origin feat/my-new-feature
   ```
7. **Open a Pull Request** on the main repository
   - Use the PR template
   - Describe your changes
   - Link related issues
8. **Wait for review** and address comments

### PR Acceptance Criteria

- ✅ All tests pass
- ✅ `ruff check .` passes
- ✅ `mypy src` passes
- ✅ Code follows project conventions
- ✅ Documentation is updated if necessary
- ✅ New tests cover new behaviors

---

## Adding a New Detection Rule

Db2iLens detects IBM i legacy data pitfalls through a modular rule system. Here's how to add a new rule `R##`.

### Rule Structure

All rules are in `src/db2ilens/rules/` and inherit from the base `Rule` class defined in `src/db2ilens/rules/base.py`.

#### 1. Create the Rule File

Create a new file in `src/db2ilens/rules/` (e.g., `src/db2ilens/rules/r10_implicit_relationships.py`):

```python
"""New detection rule for Db2iLens."""

from __future__ import annotations

from db2ilens.rules.base import Finding, Rule, Severity


class R10ImplicitRelationships(Rule):
    """R10: Detect implicit relationships between tables."""

    rule_id: str = "R10"
    severity: Severity = Severity.info  # or .warning, .critical

    def detect(self, column: Column) -> list[Finding]:
        """
        Detects the pitfall in the column data.

        Args:
            column: The column to analyze (with metadata and sample)

        Returns:
            List of findings (may be empty if nothing is detected)
        """
        findings: list[Finding] = []

        # Detection logic here
        # Example: detect if column name is too short
        if len(column.name) <= 10 and column.metadata.comment is None:
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    severity=self.severity,
                    message=f"Short column name '{column.name}' without comment",
                    evidence={"column_name": column.name, "length": len(column.name)},
                    suggested_fix="use_longer_name",
                )
            )

        return findings
```

#### 2. Register the Rule

Add your rule to the registry in `src/db2ilens/rules/__init__.py`:

```python
from db2ilens.rules.r10_implicit_relationships import R10ImplicitRelationships

# In the ALL_RULES list
ALL_RULES: list[type[Rule]] = [
    # ... existing rules
    R10ImplicitRelationships,
]

# In the RULES dictionary (for scan.yaml validation)
RULES: dict[str, type[Rule]] = {rule.rule_id: rule for rule in ALL_RULES}
```

#### 3. Create Unit Tests

Create a test file in `tests/` (e.g., `tests/test_r10_implicit_relationships.py`):

```python
"""Tests for R10 implicit relationships rule."""

from __future__ import annotations

from db2ilens.rules.r10_implicit_relationships import R10ImplicitRelationships


def _make_column(name: str, data_type: str = "CHAR", sample: list | None = None) -> Column:
    """Helper to create a test column."""
    from db2ilens.profiler.metadata import ColumnMeta
    from db2ilens.profiler.sampling import ColumnStats

    meta = ColumnMeta(
        name=name,
        data_type=data_type,
        length=10,
        scale=None,
        implied_scale=None,
        nullable=True,
        ccsid=None,
        comment=None,
    )
    stats = ColumnStats(
        row_count=10,
        null_count=0,
        blank_count=0,
        distinct_count=5,
        min_value=None,
        max_value=None,
        top_values=[],
    )
    sample = sample or []
    return Column(meta=meta, stats=stats, sample=sample)


def test_r10_detects_short_name() -> None:
    """R10 should detect short column names without comment."""
    column = _make_column("SHORT")
    findings = R10ImplicitRelationships().detect(column)
    assert len(findings) == 1
    assert findings[0].rule_id == "R10"
    assert "SHORT" in findings[0].message


def test_r10_ignores_long_name() -> None:
    """R10 should ignore long column names."""
    column = _make_column("LONG_COLUMN_NAME")
    findings = R10ImplicitRelationships().detect(column)
    assert len(findings) == 0
```

#### 4. Add Test Fixtures

If your rule requires specific data, add fixtures in `tests/fixtures/` or modify existing fixtures.

#### 5. Update scan.yaml Contract

If your rule adds new fields to findings, update `docs/SCAN_CONTRACT.md` and the validator in `src/db2ilens/scan.py`.

#### 6. Document the Rule

Add a description of your rule in:
- `docs/SCAN_CONTRACT.md` (technical contract / finding shape)
- `CHANGELOG.md` (rules table for the release)
- `README.md` (if relevant to end users)

---

## Reporting a Bug or Requesting a Feature

### Reporting a Bug

1. Check that the bug has not already been reported
2. Open a new issue with:
   - A clear and descriptive title
   - A detailed description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Your environment (Python version, OS, etc.)
   - Logs or screenshots if relevant

### Requesting a Feature

1. Check that the feature is not already in development
2. Open a new issue with:
   - A clear description of the requested feature
   - The use case (why is this useful?)
   - Examples or specifications if possible

---

## License

By contributing to Db2iLens, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

## Acknowledgments

Thank you to all contributors who help make Db2iLens a better tool!
