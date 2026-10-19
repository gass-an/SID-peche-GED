# Présentation du système d'information décisionnelle (SID) pour la province Sud : données de pêche

## Compte-rendu de réunion
**Date :** 19/10/2026  
**Participants :** Bastian, Élodie, Anthony

### 1. Résumé

La réunion porte sur la présentation détaillée du projet de construction d’un système d’information décisionnelle (SID) dédié à l’analyse des données de pêche de la province Sud. L’équipe expose la démarche suivie, de la collecte des besoins utilisateurs à la restitution des indicateurs, en passant par la conception de l’architecture technique, la gestion des données, la modélisation, la qualité et les choix d’outils. Les limites rencontrées, les choix techniques, les contrôles de cohérence et les perspectives d’évolution sont également abordés. La réunion se termine par une session de questions-réponses sur les aspects techniques, méthodologiques et organisationnels du projet.

### 2. Déroulé détaillé par sujet

#### Contexte et objectifs du SID

- Le SID est conçu pour permettre l’analyse des données de pêche détenues par la province Sud, qui sont actuellement brutes et difficilement exploitables pour des analyses décisionnelles.
- L’objectif est de transformer ces données en indicateurs pertinents pour des utilisateurs tels que managers ou directeurs, facilitant la prise de décision.
- L’approche choisie est de partir des besoins utilisateurs pour définir les indicateurs et la restitution, plutôt que de partir des seules données disponibles.

#### Spécifications fonctionnelles et architecture

- Le premier livrable a été la rédaction des spécifications fonctionnelles détaillées (SFD), réalisées avec l’aide d’un expert métier.
- L’architecture comprend plusieurs couches : ODS (copie brute des données via API), data warehouse (entrepôt de données filtrées), et un ou plusieurs data marts selon les indicateurs à restituer.
- 20 indicateurs ont été définis, 17 réalisés et 3 exclus pour cause de données insuffisantes (notamment absence de lien entre frais d’entretien et navire).

#### Familles d’indicateurs et règles de gestion

- Les indicateurs sont répartis en 5 familles : sociologie (profil des pêcheurs), matériel (type de navire), environnement (espèces pêchées), activité (nombre de sorties), économie (rentabilité).
- Les règles de gestion incluent, par exemple, la définition d’un pêcheur actif (dernière carte sans cessation d’activité), la gestion des campagnes (dates de début et de fin), le calcul de l’âge du navire (année de référence - année de construction), et la reprise des montants sans recalcul.

#### Collecte et normalisation des données

- Les données sont récupérées via une API de la province Sud, comportant 5 endpoints (pêcheur anonymisé, navire pêche anonymisé, campagne de pêche, capture pêche, carrière pêche).
- Les données sont stockées en fichiers JSON, puis normalisées pour correspondre à un schéma relationnel (création de tables supplémentaires pour gérer les listes, ex : navire-moteur).
- L’ODS final comporte 10 tables (5 issues de l’API, 5 créées pour la normalisation).

#### Choix techniques et gestion multi-plateformes

- L’équipe a dû gérer la diversité des environnements (Windows, autres OS) et a donc développé une application permettant de choisir entre SQL Server et PostgreSQL.
- Les scripts suppriment et rechargent les données à chaque exécution (pas d’historisation).
- Des tests de scripts sont automatisés via GitHub Actions.

#### Qualité des données

- Plusieurs problèmes de qualité ont été rencontrés : données incomplètes (années de construction manquantes, identifiants changeants), valeurs à normaliser, relations mal alimentées.
- Les données manquantes sont signalées ou neutralisées (valeur "inconnue" ou -1 dans le data warehouse).
- L’équipe a choisi de ne pas inventer de données pour corriger les manques.

#### Modélisation du data warehouse

- Le data warehouse comprend 4 tables de faits (carte, campagne, capture, frais), 11 dimensions (temps, personne, matériel, capture, réglementation) et 2 tables de pont (pour gérer les relations multiples, ex : capture-zones).
- Les tables de pont permettent de répartir correctement les valeurs (ex : une capture sur plusieurs zones).
- Chaque dimension a une clé numérique indépendante, avec une ligne "inconnue" pour éviter les pertes lors des jointures.

#### Data mart et restitution

- Le data mart est conçu pour faciliter la lecture et la performance sur certains indicateurs (ex : campagnes, captures par espèce, frais).
- Trois tables principales : campagnes (avec date, capitaine, commune, durée, captures, recettes, dépenses, bénéfices), captures par campagne/espèce, et frais (carburant, glace, appât, entretien).
- Certaines familles d’indicateurs lisent directement le data warehouse faute de data mart dédié.

#### Restitution et outils utilisés

- La restitution est réalisée en Python, utilisant Pandas (calculs), Plotly (graphiques interactifs), et Jinja2 (génération de pages HTML).
- Chaque indicateur est défini deux fois (formule de référence en DAX, calcul Python) pour vérification.
- Les tests automatiques vérifient la cohérence des calculs, et une fiche décrit les 17 indicateurs réalisés.
- Les rapports HTML sont interactifs, exportables, mais non connectés en temps réel (nécessité de régénérer à chaque mise à jour des données).

#### Limites et perspectives d’évolution

- Limites actuelles : absence d’historique (pas de chargement incrémental), pas de carte géographique fiable (données insuffisantes), restitution non temps réel.
- Évolutions envisagées : historisation, chargement incrémental, enrichissement des données pour de nouveaux indicateurs, création d’une vraie carte, amélioration du lien navire-campagne pour débloquer les 3 indicateurs manquants.

#### Questions et échanges complémentaires

- Discussion sur la pagination de l’API, la possibilité de télécharger les données autrement.
- Précisions sur la construction des SFD à partir des données, faute de connaissance métier approfondie.
- Organisation des schémas de base de données (ODS, data warehouse, data mart).
- Justification du choix multi-SGBD (SQL Server/PostgreSQL) pour répondre aux contraintes d’environnement.
- Contrôles de cohérence mis en place à chaque étape (comparaison du nombre de lignes, vérification des sommes).
- Discussion sur les contraintes d’intégrité dans l’ODS (sécurité vs risque de blocage).
- Clarification sur la gestion des valeurs vides/inconnues.
- Explication sur la génération du reporting HTML (template statique, pas de connexion dynamique).
- Discussion sur les données géographiques et leur représentation.
- Échanges sur l’usage du mot "du coup" et remarques de fin de réunion.

### 3. Décisions

1. Exclusion de 3 indicateurs (frais d’entretien de la flotte et deux autres liés au navire) faute de données fiables. Décision collective, pour garantir la qualité des indicateurs.
2. Choix de Python pour la restitution, afin d’éviter le coût des licences Power BI et bénéficier de bibliothèques adaptées. Décision motivée par l’absence de contrainte de licence et la flexibilité technique.
3. Mise en place d’une application multi-SGBD (SQL Server/PostgreSQL) pour garantir la portabilité du projet selon les environnements des membres. Décision prise pour répondre à la diversité des systèmes d’exploitation.
4. Suppression et rechargement complet des données à chaque exécution des scripts, en l’absence d’historisation. Décision temporaire, en attendant une évolution vers le chargement incrémental.
5. Neutralisation des données manquantes ou incohérentes (valeur "inconnue" ou -1), sans correction arbitraire. Décision prise pour garantir la fiabilité des analyses.

### 5. Points ouverts

- Historisation et chargement incrémental à mettre en place (porteur non précisé).
- Obtention de données géographiques fiables pour la création d’une carte (porteur non précisé).
- Amélioration du lien navire-campagne pour permettre la réalisation des indicateurs exclus (porteur non précisé).
- Définition métier de certains taux non encore fixée (porteur non précisé).

### 6. Risques et points de vigilance

- **Qualité des données** : Données incomplètes, normalisation imparfaite, identifiants changeants, relations mal alimentées.
- **Dépendance à la source** : Impossibilité de réaliser certains indicateurs faute de données.
- **Blocage de la chaîne** : Risque de blocage lors du chargement si contraintes d’intégrité non respectées.
- **Obsolescence du reporting** : Les rapports HTML ne sont pas en temps réel, nécessité de régénération à chaque mise à jour.
- **Coût** : Choix de Python pour éviter le coût des licences Power BI.

---

**Indicateurs clés du projet :**
- 10 tables dans l’ODS, 17 dans le data warehouse, 3 dans le data mart.
- 17 indicateurs réalisés sur 20 définis.
- Utilisation de Python, Pandas, Plotly, Jinja2 pour la restitution.
- Application compatible SQL Server et PostgreSQL.