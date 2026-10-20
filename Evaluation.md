# Compte-rendu d'évaluation — SID-peche-GED (SID Pêche, Province Sud)
Date de la soutenance : 19/10/2026  
Sources utilisées : dépôt `SID-peche-GED`, commit analysé `71ada3b` (branche master, 44 commits) ; « Compte-rendu présentation.md » (résumé de réunion).

## 1. Synthèse
Note finale proposée : 17,85 (dossier 18/20, oral 17,5/20, pondération 70/30)
Chaîne complète et reproductible (API → JSON horodatés → ODS → DWH → DTM → rapport HTML en une commande), ingestion robuste, DWH argumenté qui traite explicitement les pièges de grain, 17 indicateurs testés, soutenance claire et lucide. Ce qui retient la note : clés étrangères non déclarées dans le DWH, reporting lisant en partie le DWH au lieu du DTM, ODS sans colonnes techniques.

## 2. Présentation du projet
- **Objectif métier** : analyser l'activité de pêche de la province Sud à partir de besoins utilisateurs (managers, directeurs) formalisés dans un SFD : 20 indicateurs définis, 17 réalisés, 3 exclus faute de lien fiable navire/campagne.
- **Source** : API Open Data Province Sud, 5 jeux (`env_mer`), clé via `.env`.
- **Stack** : Python (`requests`, `pandas`, Plotly, Jinja2), PostgreSQL 17 (Docker) ou SQL Server (`DB_ENGINE`), scripts SQL par moteur, pytest + GitHub Actions.
- **Étages** : tous présents. API→JSON (`data/raw/`, archivés), ODS `env_mer` (10 tables), DWH `dwh` (4 faits, 11 dimensions, 2 ponts), DTM `dtm_performance_campagnes` (3 tables), reporting HTML (`reporting/performance_campagnes/index.html`). `main.py` enchaîne tout, avec points de reprise `--from-json|ods|dwh|dtm`.
- **README** : complet (prérequis, SQL Server, reprise), `.env.example`.

## 3. Déroulé de la soutenance
1. Contexte : données brutes difficilement exploitables ; démarche partant des besoins, SFD rédigées.
2. Architecture ODS / DWH / DTM ; 20 indicateurs en 5 familles (sociologie, matériel, environnement, activité, économie) ; règles de gestion (pêcheur actif, âge du navire, montants repris sans recalcul).
3. Collecte : 5 endpoints, JSON, normalisation vers 10 tables ODS.
4. Choix techniques : multi-SGBD (Windows/autres OS), rechargement complet à chaque exécution, tests GitHub Actions.
5. Qualité des données : années de construction manquantes, identifiants changeants ; « inconnu » / −1 sans invention de valeur.
6. DWH : 4 faits, 11 dimensions, 2 ponts (capture-zones), clés de substitution, ligne « inconnue ».
7. DTM : 3 tables (campagnes, captures par espèce, frais) ; certaines familles lisent directement le DWH.
8. Restitution Python (Pandas, Plotly, Jinja2), chaque indicateur défini en DAX de référence et en Python, tests ; HTML non temps réel.
9. Limites (pas d'historique ni de chargement incrémental, pas de carte fiable) et perspectives.

**Questions et réponses**
| Sujet | Réponse | Qualification |
|---|---|---|
| Pagination de l'API, autre moyen de télécharger | Discussion mentionnée, contenu non restitué | Non qualifiable |
| Construction du SFD faute de connaissance métier | Reconnue : SFD construit à partir des données | Satisfaisante (lucidité) |
| Organisation des schémas ODS/DWH/DTM | Schémas distincts dans une base | Satisfaisante |
| Multi-SGBD SQL Server / PostgreSQL | Diversité des postes des membres | Satisfaisante |
| Contrôles de cohérence | Comptage de lignes et vérification des sommes à chaque étape | Satisfaisante (conforme au dépôt) |
| Contraintes d'intégrité dans l'ODS | Sécurité contre risque de blocage de la chaîne | Satisfaisante (arbitrage assumé ; l'ODS déclare pourtant des FK) |
| Valeurs vides / inconnues | « Inconnu » / −1, pas de correction arbitraire | Satisfaisante |
| Génération du reporting HTML | Template statique, régénération nécessaire | Satisfaisante |
| Données géographiques / carte | Données insuffisantes pour une carte fiable | Satisfaisante |

## 4. Notation détaillée — dossier
| Section | Note | Justification et preuves (fichier, extrait, résultat) | Statut |
|---|---|---|---|
| A. Pipeline | 4/4 | `main.py` enchaîne ODS → DWH → DTM → rapport (`run_ods`, `run_dwh`, `run_dtms`, `run_report`) ; sorties compatibles entre étages (noms de champs `TABLE_COLUMNS`, DWH lu par DTM et reporting). Aucun artefact fait main : `data/raw` est ignoré par Git et reconstruit depuis l'API. Données réelles (p. ex. 1 086 captures à technique/transformation NULL, README et `init_dwh.sql:530`). Aucune étape manuelle cachée (seul `CREATE DATABASE peche_nc` SQL Server, documenté). Hésitation 4→3 si l'exécution échouait. | Observé |
| B. Ingestion | 3/3 | Client API : retry/backoff sur 429/5xx (`province_sud_client.py:35-43`), `Retry-After`, validation de la structure, pagination avec détection de curseur répété (l.86-112), clé jamais recopiée dans les erreurs (l.64-70). JSON écrit en zone `.staging`, publication seulement si tous les téléchargements réussissent, archive horodatée avec rétention de 5 (`peche_extractor.py:94-152`). Normalisation des tableaux imbriqués en 4 tables filles, types raisonnés, comptages JSON/base vérifiés (`import_table`). Limites : ODS sans date de chargement ni identifiant de lot, colonne `row_hash` déclarée dans 9 tables mais jamais alimentée (seule occurrence : `schema.py`), table `frais` ajoutée (documentée). Hésitation 3→2. | Observé |
| C. DWH | 3/4 | Constellation, grain écrit pour chaque fait (README, `init_dwh.sql`), clés de substitution, membre inconnu −1, calendrier généré (1990-2050), ponts avec facteur 1/nb_zones, `DIM_PERSONNE` au grain strict, jointures null-safe, cinq contrôles SQL. Choix justifiés (commentaires, README, oral). Faiblesses : aucune PK/FK entre faits et dimensions (0 occurrence de `REFERENCES` dans `init_dwh.sql`), pas d'historisation (SCD) — assumée par écrit, `FAIT_CARTE` agrégat qui recoupe `FAIT_CAMPAGNE` (documenté), axe navire indicatif. | Observé |
| D. DTM | 2/2 | 3 tables à grain explicite (campagne ; campagne × espèce ; poste de frais), attributs à plat, agrégation des captures par campagne, libellés « Non renseigné », contrôles DTM vs DWH sur lignes, recettes, frais, poids, écart bénéfice (`dtm/.../init.sql:319-358`). Valeur démontrable vs DWH. Réserve : un seul datamart ; en-tête qui parle encore de Power BI. | Observé |
| E. Reporting | 2/3 | 17 indicateurs en 5 thèmes, bandeaux de KPI, Plotly, export CSV client, mode jour/nuit ; question métier claire (SFD). Mais `data.py` lit `dwh.*` directement pour les thèmes sociologie, matériel et environnement ; seuls 3 tables DTM alimentent le reste (`data.py:11-61`), ce que le groupe reconnaît à l'oral. Tests de cohérence des calculs (`tests/test_reporting.py`). Chiffres du HTML non recoupés avec le DTM de mon côté. Hésitation 2→3 : ce choix est assumé et le DTM couvre l'économie et l'activité. | Observé / chiffres non vérifiables |
| F. Robustesse | 2/2 | Rejouable : `DROP`/`CREATE` à chaque exécution, PK sur les tables de faits (« la clé primaire évite qu'un rechargement double les montants »). Erreurs gérées : exit code 1/2, logs `logging`, ODS préservé si le téléchargement échoue, DTM vérifie la présence du DWH avant `DROP`, transaction. Anomalies traitées : 5 orthographes de `carte_type`, durée négative → NULL, dates hors calendrier → −1, années de construction non numériques, `carte_maree` négatif. Limite : les contrôles SQL du DWH sont journalisés sans interrompre le pipeline. 133 tests verts. | Observé (tests) ; idempotence réelle non rejouée |
| G. Code/doc/Git | 2/2 | README détaillé (objectif, prérequis, lancement, reprise, pièges d'interprétation), `.env.example`, `.gitignore`, structure `src/` claire, docstrings, CI. Aucun secret trouvé dans l'arbre ni dans l'historique (`PROVINCE_SUD_API_KEY=` toujours vide ; `admin/admin` est une valeur de dev Docker, pas un secret). 44 commits sur 4 semaines (21/09 → 19/10), messages conventionnels. Mineur : en-têtes SQL périmés (Power BI). | Observé |
| Ajustements | 0 | Aucun secret réel, pas de données jouet, pas d'incohérence déclaré/réel (README reconnaît l'absence d'historique et le caractère indicatif du lien navire). | Observé |
| **Total dossier** | **18/20** | | Provisoire |

## 5. Notation détaillée — oral (collectif)
| Critère | Note | Justification et éléments de la soutenance | Statut |
|---|---|---|---|
| O1. Structure et clarté | 4/4 | Fil conducteur du besoin utilisateur jusqu'aux limites, étages enchaînés dans l'ordre, objectif métier posé d'emblée. Hésitation 4→3. | Observé (résumé) |
| O2. Démonstration | non noté | Le résumé décrit les rapports HTML « interactifs, exportables » mais aucune exécution du pipeline. | Non vérifiable |
| O3. Justification des choix | 4/5 | Python plutôt que Power BI (licences), multi-SGBD, rechargement complet « décision temporaire », exclusion de 3 indicateurs, pas d'invention de données, ponts pour les relations multiples. Le grain des faits et le choix SCD ne sont pas évoqués dans le résumé. | Observé (résumé) |
| O4. Réponses aux questions | 3/4 | Réponses dont le contenu est restitué justes et lucides (SFD sans expertise métier, contrôles, arbitrage sur les contraintes de l'ODS). | Déduit (résumé) |
| O5. Cohérence et honnêteté | 3/3 | Chiffres recoupés avec le dépôt : 10 tables ODS, 17 tables DWH (4+11+2), 3 tables DTM, 17 indicateurs / 3 exclus, SQL Server/PostgreSQL, tests CI. Limites annoncées spontanément (historisation, carte, temps réel). Point non vérifiable : « formule de référence DAX » (les mesures ne figurent que dans les docstrings). | Observé |
| **Total oral** | **14/16 évaluables → 17,5/20** (provisoire) | O2 exclu du dénominateur ; avec O2 = 4 : 18/20 ; O2 = 3 : 17/20 ; O2 = 2 : 16/20 | |

## 6. Calcul de la note finale
- Pondération : dossier 70 % / oral 30 % (défaut).
- Calcul exact : 0,7 × 18 + 0,3 × 17,5 = 12,6 + 5,25 = **17,85**.
- Écart dossier/oral : 0,5 point (< 6), rien à signaler.

## 7. Points forts
**Dossier**
- Ingestion exemplaire : retry avec backoff, protection contre les boucles de pagination, staging puis publication, archives horodatées avec rétention, clé API jamais journalisée.
- DWH qui traite les pièges classiques : ponts pondérés pour les captures multi-zones, jointures null-safe (avec contrôle dédié), `DIM_PERSONNE` au grain strict, moteurs en dimension plutôt qu'un `MAX` incohérent, README qui avertit sur la double comptabilité `FAIT_CARTE`/`FAIT_CAMPAGNE`.
- Contrôles SQL à chaque étage (DWH, DTM) journalisés par le runner.
- 133 tests pytest + GitHub Actions, points de reprise `--from-*`, moteur interchangeable PostgreSQL / SQL Server (scripts SQL parallèles).
- Honnêteté documentée : absence d'historique, caractère indicatif de l'axe navire, indicateurs exclus.

**Oral**
- Démarche partie des besoins (SFD) ; limites et évolutions annoncées spontanément ; chiffres du discours conformes au dépôt.

## 8. Points faibles et axes d'amélioration
1. **DWH sans clés étrangères déclarées** (C). Constat : 0 `REFERENCES` dans `init_dwh.sql` ; intégrité assurée seulement par `-1` et contrôles. Impact : C 3/4. Piste : déclarer les FK (le membre −1 le permet) ou tester l'orphelinat dans les contrôles.
2. **Reporting en partie branché sur le DWH** (E). Constat : `data.py` lit `dwh.*` pour trois familles. Impact : E 2/3. Piste : étendre le DTM (personnes, flotte, captures par mois/zone) ou documenter un second datamart.
3. **ODS sans traçabilité de lot, `row_hash` jamais rempli** (B). Constat : aucune date de chargement ; colonne `row_hash` morte dans 9 tables. Impact : hésitation B 3→2. Piste : ajouter `load_ts` et `batch_id` (nom du dossier d'archive), ou supprimer `row_hash`.
4. **Pas d'historisation ni de chargement incrémental** (C, F). Assumé et documenté. Piste : SCD1 argumenté par écrit ou SCD2 sur `DIM_NAVIRE`/`DIM_PERSONNE`.
5. **Contrôles SQL non bloquants** (F). Un écart reste dans les logs sans arrêter le pipeline. Piste : seuils d'arrêt (p. ex. `personnes_en_double > 0`).
6. **Pièces du SFD et mesures DAX absentes du dépôt** (E, O5). La « fiche d'indicateurs » et les formules DAX de référence ne sont pas versionnées, donc la double définition annoncée n'est pas vérifiable. Piste : joindre la fiche au dépôt.
7. **Mineur** : en-têtes SQL mentionnent encore Power BI ; publication des JSON non atomique (documentée).
