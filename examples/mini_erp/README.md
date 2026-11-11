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
| R06 | `ARTICLES.ARTDESC` | Nom ≤ 10 caractères, sans commentaire |
| R07 | `LIGNES_CMD.TAGS` | Valeurs multi-séparateurs (`,` et `\|`) |
| R08 | `CLIENTS.ACTFLG` | Drapeau `Y`/`N` sur `CHAR(1)` |
| R09 | `ARTICLES.STDPRC` | Zéro sentinelle fréquent |

## Usage prévu (P1+)

```bash
db2ilens scan --offline examples/mini_erp/ --out scan.yaml
```

Les fichiers CSV + `schema.yaml` sont la source de vérité pour les tests offline
(`tests/fixtures/mini_erp/` est une copie miroir utilisée par pytest).
