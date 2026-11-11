# Db2iLens

Outil open source qui profile les données d'un IBM i (AS/400), détecte les pièges legacy
(EBCDIC, décimales packées, dates numériques, noms courts) et génère automatiquement
le SQL dbt de nettoyage pour une migration vers un stack moderne.

> **Statut :** phase **P0** (squelette) — CLI, règles stubs, fixtures mini-ERP, CI.
> Le scan réel, le rapport et le générateur dbt arrivent en P1–P4.

## Problème

Les migrations AS/400 → cloud échouent souvent sur les *quirks* des données
(dates `YYYYMMDD`, CCSID 65535, blancs au lieu de NULL, colonnes à 10 caractères),
pas sur la connexion elle-même.

## MVP (roadmap)

| Phase | Contenu |
|---|---|
| **P0** | Squelette repo, CLI, `Rule`, fixtures mini-ERP, CI |
| P1 | Connector offline + profiling + règles R01, R05, R08 |
| P2 | Règles R02–R04, R06 + dictionnaire d'abréviations |
| P3 | Rapport Markdown/HTML + `scan.yaml` stable |
| P4 | Générateur dbt + e2e DuckDB |
| P5 | Connector JDBC JT400 + doc PUB400 |
| P6 | Relations R10, naming LLM, Postgres/Snowflake (backlog) |

## Installation (dev)

```bash
uv sync
uv run db2ilens --help
```

## Commandes prévues

```bash
# Scanner (offline — P1+)
db2ilens scan --offline examples/mini_erp/ --out scan.yaml

# Rapport de découverte (P3+)
db2ilens report scan.yaml --format html --out rapport.html

# Projet dbt bronze/silver (P4+)
db2ilens gen-dbt scan.yaml --out dbt_project/ --target duckdb
```

Le mot de passe IBM i passe uniquement via `--password-stdin` ou `DB2ILENS_PASSWORD`
(jamais en argument CLI ni en fichier).

## Structure

```text
src/db2ilens/
├── cli.py
├── connector/     # JDBC + offline
├── profiler/      # métadonnées + échantillonnage
├── rules/         # détection des pièges legacy
├── report/        # Markdown / HTML
└── dbtgen/        # templates Jinja2 → projet dbt
```

## Développement

Voir [AGENTS.md](AGENTS.md) pour les conventions (lecture seule, typing strict, tests).

```bash
uv run ruff check .
uv run mypy src
uv run pytest
```

## Licence

MIT — voir [LICENSE](LICENSE).
