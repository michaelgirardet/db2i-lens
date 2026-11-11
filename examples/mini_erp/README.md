# Mini-ERP démo (mode offline)

Jeu de données fictif (CLIENTS, COMMANDES, LIGNES_CMD, ARTICLES) qui embarque
volontairement les pièges legacy du catalogue Db2iLens.

## Pièges par colonne

| Règle | Table.colonne | Description |
|---|---|---|
| R01 | `COMMANDES.ORDDTE` | Date numérique `DEC(8,0)` au format `YYYYMMDD` |
| R01− | `CLIENTS.PHNNUM` | Contre-exemple : `DEC(8,0)` téléphone, **pas** une date |
| R02 | `ARTICLES.CRTDTE` | Date IBM `CYYMMDD` sur `DEC(7,0)` (inclut une date 19xx) |
| R02− | `LIGNES_CMD.QTY` | Contre-exemple : `DEC(7,0)` entier, pas une date |
| R03 | `CLIENTS.CUSNAME` | `CCSID 65535` déclaré dans `schema.yaml` |
| R03− | `CLIENTS.CUSID` | Contre-exemple : `CCSID 37` |
| R04 | `LIGNES_CMD.PRC` | Prix packé : `scale: 0` + `implied_scale: 2` |
| R04− | `LIGNES_CMD.QTY` | Contre-exemple : entier sans `implied_scale` |
| R05 | `CLIENTS.CUSNAME` | Blancs / chaînes vides à la place de NULL |
| R06 | colonnes CHAR courtes | Noms ≤ 10 chars sans commentaire (ex. `CUSNAME` → `customer_name`) |
| R06− | `ARTICLES.ARTDESC` | Contre-exemple : `comment: "Article description"` |
| R07 | `LIGNES_CMD.TAGS` | Séparateur récurrent `\|` |
| R07− | `ARTICLES.ARTDESC` | Contre-exemple : texte libre sans séparateur |
| R08 | `CLIENTS.ACTFLG` | Drapeau `Y`/`N` sur `CHAR(1)` |
| R09 | `ARTICLES.STDPRC` | Zéro sentinelle fréquent |

## Usage offline

```bash
db2ilens scan --offline examples/mini_erp/ --out scan.yaml
```

Les fichiers CSV + `schema.yaml` sont la source de vérité pour les tests offline
(`tests/fixtures/mini_erp/` est une copie miroir utilisée par pytest).

## Usage PUB400 (ACS)

1. Compte gratuit sur [pub400.com](https://pub400.com)
2. Éditer `YOUR_LIBRARY` dans [`pub400_setup.sql`](pub400_setup.sql)
3. Exécuter le script dans ACS → *Run SQL Scripts*
4. Scanner (voir aussi `docs/JT400.md`) :

```bash
./scripts/fetch_jt400.sh
export JT400_JAR="$HOME/.db2ilens/jt400.jar"
export DB2ILENS_PASSWORD='…'
db2ilens scan --host pub400.com --user YOUR_USER --schema YOUR_LIBRARY --out scan.yaml
```
