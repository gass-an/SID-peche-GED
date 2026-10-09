from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.database.sql_script import execute_sql_script, split_sqlserver_batches

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATHS = {
    "postgresql": Path("sql/postgresql/dwh/init_dwh.sql"),
    "sqlserver": Path("sql/sqlserver/dwh/init_dwh.sql"),
}
ENGINE_LABELS = {"postgresql": "PostgreSQL", "sqlserver": "SQL Server"}


def get_dwh_script_path(db_engine: str) -> Path:
    """Retourne le script DWH du moteur, depuis la racine réelle du projet."""
    engine = db_engine.strip().lower()
    # La table de correspondance sélectionne explicitement le dialecte SQL et
    # exclut tout chemin construit à partir d'une valeur libre.
    try:
        relative_path = SCRIPT_PATHS[engine]
    except KeyError as exc:
        raise ValueError(f"Moteur DWH non pris en charge : {db_engine}") from exc
    # PROJECT_ROOT est dérivé de ce module : le script reste accessible quel que
    # soit le répertoire courant utilisé pour lancer main.py.
    return PROJECT_ROOT / relative_path


def ensure_env_mer_exists(connection: Any, db_engine: str) -> None:
    """Vérifie que le schéma ODS requis existe dans la base courante."""
    engine = db_engine.strip().lower()
    # Chaque moteur expose différemment ses schémas système ; le contrôle vise
    # le même prérequis fonctionnel avant toute construction du DWH.
    if engine == "postgresql":
        statement = (
            "SELECT 1 FROM information_schema.schemata "
            "WHERE schema_name = 'env_mer'"
        )
    elif engine == "sqlserver":
        statement = "SELECT 1 WHERE SCHEMA_ID(N'env_mer') IS NOT NULL"
    else:
        raise ValueError(f"Moteur DWH non pris en charge : {db_engine}")

    with connection.cursor() as cursor:
        cursor.execute(statement)
        exists = cursor.fetchone() is not None

    if not exists:
        raise RuntimeError("Le schéma ODS env_mer est absent de la base peche_nc.")


def run_dwh(connection: Any, db_engine: str) -> None:
    """Orchestre le script DWH du moteur sélectionné dans une transaction.

    La logique de création et d'alimentation du DWH demeure dans les scripts SQL ;
    ce runner choisit le dialecte, exécute le script et gère son issue.
    """
    engine = db_engine.strip().lower()
    script_path = get_dwh_script_path(engine)
    logging.info("Construction du DWH...")
    logging.info("Moteur : %s", ENGINE_LABELS[engine])

    try:
        execute_sql_script(connection, engine, script_path)
    except Exception:
        logging.exception(
            "Construction du DWH interrompue (moteur=%s, script=%s)",
            ENGINE_LABELS[engine],
            script_path,
        )
        raise

    logging.info("DWH dwh construit avec succès.")
