# scan.yaml contract

`scan.yaml` is the central artifact of Db2iLens. One scan pass produces it;
downstream consumers (`report`, `gen-dbt`, future SaaS) must treat it as the
single source of truth.

Format version constant: `SCAN_FORMAT_VERSION` in `src/db2ilens/scan.py`
(currently **`1.0`**).

Structural validation: `validate_scan_document()` in the same module. Call it
before trusting any scan file that did not come from the current process.

---

## Top-level structure

```yaml
version: "1.0"
generated_at: "<ISO-8601 timestamp>"
mode: offline | jdbc   # producer mode
source: "<path or connection label>"
schema_name: "<IBM i library / schema>"
sample_rows: <int>     # rows sampled per table
summary: { ... }
tables: [ ... ]
```

| Field | Required | Meaning |
|---|---|---|
| `version` | yes | Contract version string. Must equal `SCAN_FORMAT_VERSION`. |
| `generated_at` | yes | UTC generation timestamp (ISO-8601). Golden fixtures may use `STABLE`. |
| `mode` | yes | How the scan was produced (`offline` today; `jdbc` later). |
| `source` | yes | Offline export path, or a JDBC source label. |
| `schema_name` | yes | IBM i library / SQL schema scanned. |
| `sample_rows` | yes | Sampling budget applied per table. |
| `summary` | yes | Aggregate counters for dashboards. |
| `tables` | yes | Ordered list of per-table payloads. |

---

## `summary`

```yaml
summary:
  table_count: <int>
  column_count: <int>
  finding_count: <int>
  findings_by_severity:
    critical: <int>
    warning: <int>
    info: <int>
```

| Field | Required | Meaning |
|---|---|---|
| `table_count` | yes | Number of tables in `tables`. |
| `column_count` | yes | Total columns across all tables. |
| `finding_count` | yes | Total findings across all columns. |
| `findings_by_severity` | yes | Counts keyed by severity. Keys must be known severities. |

Severity keys may be omitted when zero in hand-written fixtures, but the scan
producer always emits `critical`, `warning`, and `info`.

---

## `tables[]`

```yaml
tables:
  - name: CLIENTS
    columns: [ ... ]
```

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Table name as found in the source. |
| `columns` | yes | List of column payloads (metadata + stats + findings). |

---

## `tables[].columns[]`

Each column carries three layers:

1. **metadata** — physical definition from the source catalog / export.
2. **stats** — sample profile for that column.
3. **findings** — zero or more rule hits (may be an empty list).

```yaml
- name: CUSNAME
  metadata: { ... }
  stats: { ... }
  findings: [ ... ]
```

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Column name. |
| `metadata` | yes | Catalog-like attributes. |
| `stats` | yes | Sample statistics. |
| `findings` | yes | List of findings (empty list when clean). |

### `metadata`

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Same as column name (duplicated for self-contained payloads). |
| `data_type` | yes | IBM i / SQL type label (`CHAR`, `DECIMAL`, …). |
| `length` | yes | Length / precision, or `null`. |
| `scale` | yes | Declared scale, or `null`. |
| `implied_scale` | yes | Heuristic packed-decimal scale (R04), or `null`. |
| `nullable` | yes | Boolean nullability. |
| `ccsid` | yes | CCSID when applicable, else `null`. |
| `comment` | yes | Column comment / label, or `null`. |

### `stats`

| Field | Required | Meaning |
|---|---|---|
| `row_count` | yes | Rows in the sample (or table if smaller). |
| `null_count` | yes | Null occurrences in the sample. |
| `blank_count` | yes | Blank / whitespace-only string occurrences. |
| `distinct_count` | yes | Distinct non-null values observed. |
| `min_value` | yes | Minimum observed value (YAML-safe scalar), or `null`. |
| `max_value` | yes | Maximum observed value (YAML-safe scalar), or `null`. |
| `top_values` | yes | List of `{value, count}` pairs (most frequent first). |

### `findings[]`

| Field | Required | Meaning |
|---|---|---|
| `rule_id` | yes | Detector id (`R01`…); must exist in the `RULES` registry. |
| `severity` | yes | One of `critical`, `warning`, `info`. |
| `message` | yes | Human-readable finding description. |
| `evidence` | yes | Structured evidence map (rule-specific keys). |
| `suggested_fix` | yes | Suggested SQL / rename string, or `null`. |

---

## Invariants

1. **Version** — `version` is a string equal to `SCAN_FORMAT_VERSION`.
2. **Severities** — every finding severity and every
   `summary.findings_by_severity` key is one of:
   `critical`, `warning`, `info` (see `Severity` in `rules/base.py`).
3. **Rule registry** — every `rule_id` in the document exists in
   `db2ilens.rules.RULES`. Unknown ids are rejected (protects against stale /
   hand-edited / foreign scans).
4. **Required fields** — all fields listed above are present. Optional *values*
   use YAML `null`; the *keys* remain mandatory.
5. **Findings list** — always a list (never omitted); empty when no rules fire.
6. **Read-only producer** — the scan never mutates the source (SELECT-only /
   offline files). The contract describes observations, not DDL/DML.

Current registered rule ids (as of version `1.0`): `R01`–`R09`
(see `ALL_RULES` / `RULES` in `src/db2ilens/rules/__init__.py`). Not every
registered rule must appear in a given scan; validation only requires that
appearing ids are registered.

---

## Evolution rules

Any intentional schema change must:

1. **Bump** `SCAN_FORMAT_VERSION` (and the `version` written into every new
   scan artifact).
2. **Update** the golden file `tests/golden/scan_mini_erp.yaml`.
3. **Update** this document (`docs/SCAN_CONTRACT.md`) with the new fields /
   invariants and a short changelog note below.
4. **Extend** `validate_scan_document()` and its tests so invalid documents
   still fail loudly.
5. Prefer additive, backward-compatible changes within a major-compatible
   version string when possible; breaking removals / renames require a version
   bump that consumers can detect.

### Changelog

| Version | Date | Notes |
|---|---|---|
| `1.0` | 2026-11-11 | Initial published contract (P3). Markdown + HTML reports consume it. |
