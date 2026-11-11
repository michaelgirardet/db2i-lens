# Règles du projet Db2iLens

## Contexte
Outil Python en lecture seule qui profile des données IBM i et génère du dbt.
L'utilisateur travaille en français ou anglais ; le code et les identifiants sont en anglais.

## Conventions
- Python 3.11+, typing strict (mypy), formatage ruff, tests pytest obligatoires.
- Tout accès DB passe par src/db2ilens/connector/. Aucun SQL en dehors.
- Aucune requête ne doit modifier la source : SELECT uniquement, jamais de DML/DDL.
- Chaque règle de détection hérite de rules/base.py::Rule (id, sévérité, detect, fix).
- Les mots de passe ne sont jamais écrits dans le code, les logs ou les fichiers de test.
- Les templates dbt sont en Jinja2 dans db2ilens/dbtgen/templates/, jamais de SQL en dur dans le Python.

## Avant de terminer une tâche
1. `ruff check . && mypy src && pytest` passent.
2. Toute nouvelle règle vient avec un fixture la déclenchant et un test.
3. Toute nouvelle commande CLI vient avec un test e2e en mode offline.
