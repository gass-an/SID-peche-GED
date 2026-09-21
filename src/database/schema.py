from __future__ import annotations

from typing import Any

from src.config import TABLES, validate_table_name
from src.database.dialect import is_sqlserver, qualified_table, transaction

CHILD_TABLES = {
    "navire_peche_anonymise": "navire_moteur",
    "pecheur_anonymise": "carte_pecherie_specifique",
    "campagne_peche": "campagne_frais",
    "capture_peche": "capture_zone",
}

FRAIS = {
    "mat": "Matériel",
    "glace": "Glace",
    "vivre": "Vivres",
    "appats": "Appâts",
    "divers": "Divers",
    "stockage": "Stockage",
    "carburant": "Carburant",
    "petit_mat": "Petit matériel",
    "lubrifiant": "Lubrifiant",
    "commerciaux": "Frais commerciaux",
    "exceptionnel": "Frais exceptionnels",
    "entretien_bateau": "Entretien du bateau",
    "entretien_moteur": "Entretien du moteur",
}

TABLE_COLUMNS = {
    "navire_peche_anonymise": ["categorie_navigation", "constructeur", "materiau", "navire_annee_construction", "navire_id", "navire_jauge_brute", "navire_longueur", "navire_origine", "row_hash"],
    "pecheur_anonymise": ["capitaine_commune", "capitaine_date_naissance", "capitaine_id", "capitaine_sexe", "carte_annee", "carte_autorisation_annee", "carte_autorisation_commune", "carte_autorisation_date_delivrance", "carte_autorisation_navire_id", "carte_autorisation_province", "carte_autorisation_statut", "carte_benefice", "carte_carburant_qte", "carte_date_delivrance", "carte_depense", "carte_id", "carte_maree", "carte_recette", "carte_rendement", "carte_renouvellement", "carte_tonnage_epe", "carte_type", "patron_pecheur_commune", "patron_pecheur_date_naissance", "patron_pecheur_id", "patron_pecheur_sexe", "row_hash"],
    "campagne_peche": ["campagne_benefice", "campagne_carburant_qte", "campagne_carte_id", "campagne_charges_sociales", "campagne_commentaire", "campagne_date_debut", "campagne_date_fin", "campagne_depense", "campagne_id", "campagne_instance_label", "campagne_jours_mer", "campagne_jours_peche", "campagne_nbr_femme_abord", "campagne_nbre_equipage", "campagne_recette", "campagne_rendement", "campagne_salaire_matelots", "campagne_salaire_patron", "campagne_tonnage_epe", "row_hash"],
    "carroyage_peche": ["carroyage_commune", "carroyage_eth", "carroyage_id", "carroyage_nouvelle_zone_peche", "carroyage_repartition_commune_ancien_carroyage", "carroyage_repartition_commune_nouveau_carroyage", "carroyage_superficie_commune_associee_km2", "carroyage_superficie_intersectee_km2", "carroyage_superficie_nv_carroyage_km2", "carroyage_zone_peche", "coarroyage_zone_peche_id", "row_hash"],
    "capture_peche": ["capture_campagne_id", "capture_categorie_capt_unit_effort_moyen", "capture_categorie_code", "capture_categorie_nb_moy_camp_declaree", "capture_categorie_nom", "capture_categorie_poids_prix_moyen", "capture_categorie_seuil_fiabilite70", "capture_categorie_seuil_fiabilite95", "capture_id", "capture_nombre", "capture_poids_entier_total", "capture_poids_transf_total", "capture_produit", "capture_technique", "capture_transformation", "capture_valeurxpf", "row_hash"],
    "navire_moteur": ["moteur_id", "navire_id", "usage", "marque", "carburant"],
    "carte_pecherie_specifique": ["carte_id", "code", "nom", "zone", "taille", "periode", "quantite", "description"],
    "frais": ["frais_id", "libelle"],
    "campagne_frais": ["campagne_id", "frais_id", "montant"],
    "capture_zone": ["capture_id", "zone_peche_id", "label"],
}

TABLE_DEFINITIONS = {
    "navire_peche_anonymise": """categorie_navigation VARCHAR(4000), constructeur VARCHAR(4000), materiau VARCHAR(4000), navire_annee_construction VARCHAR(255), navire_id VARCHAR(255) PRIMARY KEY, navire_jauge_brute DOUBLE PRECISION, navire_longueur DOUBLE PRECISION, navire_origine VARCHAR(255), row_hash TEXT""",
    "pecheur_anonymise": """capitaine_commune VARCHAR(4000), capitaine_date_naissance DATE, capitaine_id VARCHAR(255), capitaine_sexe VARCHAR(255), carte_annee VARCHAR(255), carte_autorisation_annee VARCHAR(255), carte_autorisation_commune VARCHAR(4000), carte_autorisation_date_delivrance DATE, carte_autorisation_navire_id VARCHAR(255), carte_autorisation_province VARCHAR(4000), carte_autorisation_statut VARCHAR(255), carte_benefice DOUBLE PRECISION, carte_carburant_qte DOUBLE PRECISION, carte_date_delivrance DATE, carte_depense DOUBLE PRECISION, carte_id VARCHAR(255) PRIMARY KEY, carte_maree INTEGER, carte_recette DOUBLE PRECISION, carte_rendement DOUBLE PRECISION, carte_renouvellement BOOLEAN, carte_tonnage_epe DOUBLE PRECISION, carte_type VARCHAR(255), patron_pecheur_commune VARCHAR(4000), patron_pecheur_date_naissance DATE, patron_pecheur_id VARCHAR(255), patron_pecheur_sexe VARCHAR(255), row_hash TEXT, CONSTRAINT fk_pecheur_navire FOREIGN KEY (carte_autorisation_navire_id) REFERENCES env_mer.navire_peche_anonymise(navire_id)""",
    "campagne_peche": """campagne_benefice DOUBLE PRECISION, campagne_carburant_qte DOUBLE PRECISION, campagne_carte_id VARCHAR(255), campagne_charges_sociales DOUBLE PRECISION, campagne_commentaire VARCHAR(255), campagne_date_debut DATE, campagne_date_fin DATE, campagne_depense DOUBLE PRECISION, campagne_id VARCHAR(255) PRIMARY KEY, campagne_instance_label VARCHAR(4000), campagne_jours_mer DOUBLE PRECISION, campagne_jours_peche DOUBLE PRECISION, campagne_nbr_femme_abord INTEGER, campagne_nbre_equipage DOUBLE PRECISION, campagne_recette DOUBLE PRECISION, campagne_rendement DOUBLE PRECISION, campagne_salaire_matelots DOUBLE PRECISION, campagne_salaire_patron DOUBLE PRECISION, campagne_tonnage_epe DOUBLE PRECISION, row_hash TEXT, CONSTRAINT fk_campagne_carte FOREIGN KEY (campagne_carte_id) REFERENCES env_mer.pecheur_anonymise(carte_id)""",
    "carroyage_peche": """carroyage_commune VARCHAR(50), carroyage_eth VARCHAR(50), carroyage_id INTEGER PRIMARY KEY, carroyage_nouvelle_zone_peche VARCHAR(50), carroyage_repartition_commune_ancien_carroyage INTEGER, carroyage_repartition_commune_nouveau_carroyage DOUBLE PRECISION, carroyage_superficie_commune_associee_km2 NUMERIC, carroyage_superficie_intersectee_km2 NUMERIC, carroyage_superficie_nv_carroyage_km2 NUMERIC, carroyage_zone_peche VARCHAR(50), coarroyage_zone_peche_id VARCHAR(255), row_hash TEXT""",
    "capture_peche": """capture_campagne_id VARCHAR(255), capture_categorie_capt_unit_effort_moyen DOUBLE PRECISION, capture_categorie_code VARCHAR(255), capture_categorie_nb_moy_camp_declaree INTEGER, capture_categorie_nom VARCHAR(255), capture_categorie_poids_prix_moyen VARCHAR(255), capture_categorie_seuil_fiabilite70 DOUBLE PRECISION, capture_categorie_seuil_fiabilite95 DOUBLE PRECISION, capture_id VARCHAR(255) PRIMARY KEY, capture_nombre DOUBLE PRECISION, capture_poids_entier_total DOUBLE PRECISION, capture_poids_transf_total DOUBLE PRECISION, capture_produit VARCHAR(4000), capture_technique VARCHAR(4000), capture_transformation VARCHAR(4000), capture_valeurxpf DOUBLE PRECISION, row_hash TEXT, CONSTRAINT fk_capture_campagne FOREIGN KEY (capture_campagne_id) REFERENCES env_mer.campagne_peche(campagne_id)""",
    "navire_moteur": """moteur_id VARCHAR(255) PRIMARY KEY, navire_id VARCHAR(255) NOT NULL, usage VARCHAR(4000), marque VARCHAR(4000), carburant VARCHAR(255), CONSTRAINT fk_navire_moteur_navire FOREIGN KEY (navire_id) REFERENCES env_mer.navire_peche_anonymise(navire_id) ON DELETE CASCADE""",
    "carte_pecherie_specifique": """carte_id VARCHAR(255) NOT NULL, code VARCHAR(255) NOT NULL, nom VARCHAR(4000), zone VARCHAR(4000), taille VARCHAR(4000), periode VARCHAR(4000), quantite VARCHAR(4000), description VARCHAR(4000), CONSTRAINT pk_carte_pecherie_specifique PRIMARY KEY (carte_id, code), CONSTRAINT fk_carte_pecherie_specifique_carte FOREIGN KEY (carte_id) REFERENCES env_mer.pecheur_anonymise(carte_id) ON DELETE CASCADE""",
    "frais": """frais_id VARCHAR(255) PRIMARY KEY, libelle VARCHAR(255) NOT NULL UNIQUE""",
    "campagne_frais": """campagne_id VARCHAR(255) NOT NULL, frais_id VARCHAR(255) NOT NULL, montant DOUBLE PRECISION NOT NULL, CONSTRAINT pk_campagne_frais PRIMARY KEY (campagne_id, frais_id), CONSTRAINT fk_campagne_frais_campagne FOREIGN KEY (campagne_id) REFERENCES env_mer.campagne_peche(campagne_id) ON DELETE CASCADE, CONSTRAINT fk_campagne_frais_frais FOREIGN KEY (frais_id) REFERENCES env_mer.frais(frais_id)""",
    "capture_zone": """capture_id VARCHAR(255) NOT NULL, zone_peche_id VARCHAR(255) NOT NULL, label VARCHAR(4000), CONSTRAINT pk_capture_zone PRIMARY KEY (capture_id, zone_peche_id), CONSTRAINT fk_capture_zone_capture FOREIGN KEY (capture_id) REFERENCES env_mer.capture_peche(capture_id) ON DELETE CASCADE""",
}

def _sqlserver_definition(definition: str) -> str:
    """Traduit les types PostgreSQL vers leurs équivalents SQL Server."""
    return (
        definition.replace("DOUBLE PRECISION", "FLOAT")
        .replace("BOOLEAN", "BIT")
        .replace(" NUMERIC", " DECIMAL(18,8)")
        .replace(" TEXT", " VARCHAR(MAX)")
    )


SQLSERVER_TABLE_DEFINITIONS = {
    table_name: _sqlserver_definition(definition)
    for table_name, definition in TABLE_DEFINITIONS.items()
}

INDEX_DEFINITIONS = {
    "pecheur_anonymise": "CREATE INDEX idx_pecheur_navire_id ON env_mer.pecheur_anonymise(carte_autorisation_navire_id)",
    "campagne_peche": "CREATE INDEX idx_campagne_carte_id ON env_mer.campagne_peche(campagne_carte_id)",
    "capture_peche": "CREATE INDEX idx_capture_campagne_id ON env_mer.capture_peche(capture_campagne_id)",
    "navire_moteur": "CREATE INDEX idx_navire_moteur_navire_id ON env_mer.navire_moteur(navire_id)",
    "carte_pecherie_specifique": "CREATE INDEX idx_carte_pecherie_specifique_carte_id ON env_mer.carte_pecherie_specifique(carte_id)",
    "capture_zone": "CREATE INDEX idx_capture_zone_capture_id ON env_mer.capture_zone(capture_id)",
    "campagne_frais": "CREATE INDEX idx_campagne_frais_frais_id ON env_mer.campagne_frais(frais_id)",
}

REFERENCED_PARENT_TABLES = {
    "navire_peche_anonymise",
    "pecheur_anonymise",
    "campagne_peche",
}


def managed_tables(table_names: list[str]) -> list[str]:
    """Énumère les tables principales, enfants et référentielles à gérer."""
    tables = list(table_names) + [CHILD_TABLES[name] for name in table_names if name in CHILD_TABLES]
    if "campagne_peche" in table_names:
        tables.append("frais")
    return tables


def validate_reset_scope(table_names: list[str]) -> None:
    """Vérifie que la portée de reconstruction respecte les dépendances."""
    for table_name in table_names:
        validate_table_name(table_name)
    if set(table_names) != set(TABLES):
        referenced = REFERENCED_PARENT_TABLES.intersection(table_names)
        if referenced:
            names = ", ".join(sorted(referenced))
            raise ValueError(
                "Reconstruction isolée impossible pour une table référencée "
                f"({names}). Relancez le script sans argument."
            )


def reset_tables(connection: Any, table_names: list[str]) -> None:
    """Reconstruit atomiquement les tables et index demandés."""
    validate_reset_scope(table_names)
    children = [CHILD_TABLES[name] for name in table_names if name in CHILD_TABLES]
    sqlserver = is_sqlserver(connection)
    definitions = SQLSERVER_TABLE_DEFINITIONS if sqlserver else TABLE_DEFINITIONS
    placeholder = "?" if sqlserver else "%s"
    with transaction(connection):
        with connection.cursor() as cursor:
            if sqlserver:
                cursor.execute(
                    "IF SCHEMA_ID(N'env_mer') IS NULL "
                    "EXEC(N'CREATE SCHEMA [env_mer]')"
                )
            else:
                cursor.execute("CREATE SCHEMA IF NOT EXISTS env_mer")
            for table_name in reversed(children):
                cursor.execute(
                    f"DROP TABLE IF EXISTS "
                    f"{qualified_table(table_name, sqlserver=sqlserver)}"
                )
            if "campagne_peche" in table_names:
                suffix = "" if sqlserver else " CASCADE"
                cursor.execute(
                    f"DROP TABLE IF EXISTS "
                    f"{qualified_table('frais', sqlserver=sqlserver)}{suffix}"
                )
            for table_name in reversed(TABLES):
                if table_name in table_names:
                    cursor.execute(
                        f"DROP TABLE IF EXISTS "
                        f"{qualified_table(table_name, sqlserver=sqlserver)}"
                    )
            for table_name in TABLES:
                if table_name in table_names:
                    cursor.execute(
                        f"CREATE TABLE "
                        f"{qualified_table(table_name, sqlserver=sqlserver)} "
                        f"({definitions[table_name]})"
                    )
                    if table_name == "campagne_peche":
                        cursor.execute(
                            f"CREATE TABLE "
                            f"{qualified_table('frais', sqlserver=sqlserver)} "
                            f"({definitions['frais']})"
                        )
                        cursor.executemany(
                            f"INSERT INTO "
                            f"{qualified_table('frais', sqlserver=sqlserver)} "
                            f"(frais_id, libelle) VALUES ({placeholder}, {placeholder})",
                            list(FRAIS.items()),
                        )
            for table_name in children:
                cursor.execute(
                    f"CREATE TABLE "
                    f"{qualified_table(table_name, sqlserver=sqlserver)} "
                    f"({definitions[table_name]})"
                )
            for table_name in managed_tables(table_names):
                if table_name in INDEX_DEFINITIONS:
                    cursor.execute(INDEX_DEFINITIONS[table_name])
