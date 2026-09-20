# Import des données de pêche de la Province Sud

Ce projet importe les cinq jeux de données dans PostgreSQL 17 ou SQL Server
`env_mer` de l'API Open Data Province Sud. Les tableaux imbriqués sont normalisés
dans `navire_moteur`, `carte_pecherie_specifique`, `campagne_frais` et
`capture_zone`. Le script télécharge d'abord un instantané complet dans
`data/raw/*.json`, puis remplit PostgreSQL uniquement depuis ces fichiers. La base
existante n'est donc pas modifiée si le téléchargement échoue.

Lors d'une nouvelle exécution, les JSON courants sont déplacés dans un dossier
daté sous `data/raw/archive/`. Les cinq instantanés précédents sont conservés.
Les types de frais sont répertoriés dans `frais`, puis associés aux campagnes
par `campagne_frais(campagne_id, frais_id, montant)`.

Les relations présentes dans les données sont garanties par des clés étrangères :
carte vers navire, campagne vers carte et capture vers campagne.

Le modèle est volontairement limité aux dix tables du schéma :
`pecheur_anonymise`, `navire_peche_anonymise`, `navire_moteur`,
`carte_pecherie_specifique`, `campagne_peche`, `frais`, `campagne_frais`,
`capture_peche`, `capture_zone` et `carroyage_peche`. Aucun référentiel
supplémentaire de cartes ou de zones n'est créé.
Le reset SQL est exécuté par Python à chaque extraction, pas par le conteneur.

Le moteur est choisi avec `DB_ENGINE=postgresql` ou `DB_ENGINE=sqlserver`.
Chaque membre du groupe peut donc utiliser son moteur sans modifier le code.

## Installation et lancement

```bash
cp .env.example .env
# Renseigner PROVINCE_SUD_API_KEY dans .env
docker compose up -d
pip install -r requirements.txt
python main.py
```

Le fichier `docker-compose.yml` reste dédié à PostgreSQL. Pour SQL Server sous
Windows, installer SQL Server (Express ou Developer), SQL Server Management
Studio et Microsoft ODBC Driver 18 for SQL Server, puis créer la base une fois :

```sql
CREATE DATABASE peche_nc;
```

Configurer ensuite `.env` avec l'authentification Windows :

```dotenv
DB_ENGINE=sqlserver
SQLSERVER_CONNECTION_STRING=Driver={ODBC Driver 18 for SQL Server};Server=localhost\SQLEXPRESS;Database=peche_nc;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes
```

`localhost\SQLEXPRESS` est fréquent avec SQL Server Express. Pour une instance
par défaut, utiliser simplement `Server=localhost`. Le compte Windows qui lance
Python doit disposer des droits de création et de suppression des objets dans
la base `peche_nc`.

Pour reconstruire et remplir PostgreSQL uniquement depuis les JSON déjà
présents dans `data/raw/`, sans aucun appel à l'API ni rotation des fichiers :

```bash
python main.py --depuis-json
```

L'alias anglais `python main.py --from-json` est également disponible. La clé
`PROVINCE_SUD_API_KEY` n'est pas obligatoire dans ce mode.

Les tables feuilles, qui ne sont référencées par aucune autre table, peuvent
être reconstruites et importées seules :

```bash
python main.py capture_peche
```

Pour `navire_peche_anonymise`, `pecheur_anonymise` ou `campagne_peche`, relancer
le script sans argument afin de reconstruire ensemble toutes les relations.

Les copies JSON sont écrites progressivement dans `data/raw/`. Pour arrêter la
base, utiliser `docker compose down`; ajouter `-v` supprime volontairement son
volume persistant.

## Tests unitaires

```bash
pip install -r requirements-dev.txt
python -m pytest
```
