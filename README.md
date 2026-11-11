# Db2iLens

Outil open source qui profile les données d'un IBM i (AS/400), détecte les pièges legacy
(EBCDIC, décimales packées, dates numériques, noms courts) et génère automatiquement
le SQL dbt de nettoyage pour une migration vers un stack moderne.

> **Statut :** phases **P0–P5** livrées — scan offline + JDBC (JT400), rapports HTML,
> générateur dbt + `dbt run`/`dbt test` DuckDB, guide PUB400.
> Backlog : **P6** (R09/R10, naming LLM, cibles Postgres/Snowflake).

[![CI](https://github.com/michaelgirardet/db2i-lens/actions/workflows/ci.yml/badge.svg)](https://github.com/michaelgirardet/db2i-lens/actions/workflows/ci.yml)
License: MIT

## Problème

Les migrations AS/400 → cloud échouent souvent sur les *quirks* des données
(dates `YYYYMMDD`, CCSID 65535, blancs au lieu de NULL, colonnes à 10 caractères),
pas sur la connexion elle-même.

## MVP (roadmap)

| Phase | Contenu | Statut |
|---|---|---|
| **P0** | Squelette repo, CLI, `Rule`, fixtures mini-ERP, CI | [x] |
| **P1** | Connector offline + profiling + R01, R05, R08 + `scan --offline` | [x] |
| **P2** | Règles R02–R04, R06, R07 + dictionnaire d'abréviations | [x] |
| **P3** | Rapport Markdown/HTML + `scan.yaml` stable | [x] |
| **P4** | Générateur dbt + e2e DuckDB | [x] |
| **P5** | Connector JDBC JT400 + doc PUB400 | [x] |
| **P6** | Relations R10, naming LLM, Postgres/Snowflake (backlog) | [ ] |

## Installation (dev)

```bash
uv sync
./scripts/fetch_jt400.sh   # JDBC only — see docs/JT400.md
uv run db2ilens --help
```

## Commandes

```bash
# Scanner (offline)
db2ilens scan --offline examples/mini_erp/ --out scan.yaml

# Scanner (IBM i / PUB400)
export JT400_JAR=$HOME/.db2ilens/jt400.jar
export DB2ILENS_PASSWORD='…'
db2ilens scan --host pub400.com --user YOUR_USER --schema DEMO_LENS --out scan.yaml

# Rapport de découverte (Markdown / HTML)
db2ilens report scan.yaml --format html --out rapport.html

# Projet dbt bronze/silver
db2ilens gen-dbt scan.yaml --out dbt_project/ --target duckdb
```

Le mot de passe IBM i passe uniquement via `--password-stdin` ou `DB2ILENS_PASSWORD`
(jamais en argument CLI ni en fichier).

## Try it on PUB400

1. **Compte** : [pub400.com](https://pub400.com) (activation parfois différée de quelques heures).
2. **Driver** : Java 11+ et `./scripts/fetch_jt400.sh` (détails dans [docs/JT400.md](docs/JT400.md)).
3. **Schéma démo** (recommandé, pour ne pas écraser vos tables) dans ACS *Run SQL Scripts* :
   ```sql
   CREATE SCHEMA DEMO_LENS;
   ```
   Puis éditez [`examples/mini_erp/pub400_setup.sql`](examples/mini_erp/pub400_setup.sql) :
   remplacez `YOUR_LIBRARY` par `DEMO_LENS`, exécutez tout le script.
4. **Vérifs ACS** :
   ```sql
   SELECT COUNT(*) FROM DEMO_LENS.COMMANDES;  -- 5
   SELECT CCSID FROM QSYS2.SYSCOLUMNS2
     WHERE TABLE_SCHEMA = 'DEMO_LENS' AND COLUMN_NAME = 'CUSNAME';  -- 65535
   ```
5. **Scan + rapport + dbt** :
   ```bash
   export JT400_JAR=$HOME/.db2ilens/jt400.jar
   export DB2ILENS_USER=YOUR_USER
   export DB2ILENS_PASSWORD='…'
   export PUB400_SCHEMA=DEMO_LENS   # for integration tests

   uv run db2ilens scan --host pub400.com --user "$DB2ILENS_USER" \
     --schema DEMO_LENS --out /tmp/scan_pub400.yaml
   uv run db2ilens report /tmp/scan_pub400.yaml --format html --out /tmp/rapport.html
   uv run db2ilens gen-dbt /tmp/scan_pub400.yaml --out /tmp/dbt_pub400 --target duckdb
   ```
6. **Limites PUB400** : quota CPU/connexion, première session JT400 parfois lente,
   bibliothèques en **majuscules**.  
   **R04** (`implied_scale` sur `PRC`) : *implicit decimal scale is a schema-level
   declaration, invisible in SYSCOLUMNS2* — attendu **absent** en JDBC, présent
   en mode offline.

Tests live (hors CI) :

```bash
uv run pytest -m integration
```

## Structure

```text
src/db2ilens/
├── cli.py
├── connector/     # JDBC + offline
├── profiler/      # métadonnées + échantillonnage
├── rules/         # détection des pièges legacy
├── report/        # Markdown / HTML
├── scan.py        # contrat scan.yaml
└── dbtgen/        # templates Jinja2 → projet dbt
```

## Développement

Voir [AGENTS.md](AGENTS.md) et [docs/PRD.md](docs/PRD.md).

```bash
uv run ruff check .
uv run mypy src
uv run pytest                 # exclut @pytest.mark.integration
uv run pytest -m integration  # PUB400 live
```

## Licence

MIT — voir [LICENSE](LICENSE).
