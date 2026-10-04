from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATHS = {
    "postgresql": Path("sql/postgresql/dwh/init_dwh.sql"),
    "sqlserver": Path("sql/sqlserver/dwh/init_dwh.sql"),
}
ENGINE_LABELS = {"postgresql": "PostgreSQL", "sqlserver": "SQL Server"}
GO_SEPARATOR = re.compile(r"^\s*GO\s*$", re.IGNORECASE | re.MULTILINE)


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


def split_sqlserver_batches(script: str) -> list[str]:
    """Découpe un script uniquement sur les lignes constituées de GO."""
    # GO est compris par les clients SQL Server, pas par le pilote pyodbc. Chaque
    # bloc doit donc être envoyé séparément, sans couper un mot inclus dans du SQL.
    return [batch.strip() for batch in GO_SEPARATOR.split(script) if batch.strip()]


def _consume_result_sets(cursor: Any) -> None:
    """Consomme les jeux de résultats sans interpréter leurs valeurs."""
    while True:
        # Les scripts contiennent notamment des requêtes de contrôle. Leurs
        # résultats sont lus pour avancer dans le curseur, mais une valeur signalant
        # des anomalies n'est pas interprétée et ne provoque donc pas d'erreur ici.
        if getattr(cursor, "description", None) is not None:
            cursor.fetchall()
        nextset = getattr(cursor, "nextset", None)
        if nextset is None or not nextset():
            return


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
    script = script_path.read_text(encoding="utf-8")
    logging.info("Construction du DWH...")
    logging.info("Moteur : %s", ENGINE_LABELS[engine])

    try:
        with connection.cursor() as cursor:
            if engine == "postgresql":
                # psycopg accepte le script PostgreSQL complet en une exécution.
                cursor.execute(script)
                _consume_result_sets(cursor)
            else:
                # Sous SQL Server, chaque lot délimité par GO est exécuté dans
                # l'ordre. Le numéro journalisé localise précisément un échec.
                for batch_number, batch in enumerate(
                    split_sqlserver_batches(script), start=1
                ):
                    try:
                        cursor.execute(batch)
                        _consume_result_sets(cursor)
                    except Exception:
                        logging.exception(
                            "Échec du batch SQL Server n°%d (%s)",
                            batch_number,
                            script_path,
                        )
                        raise
        # Le commit indique que toutes les instructions se sont terminées sans
        # exception. Il ne signifie pas que les valeurs retournées par les requêtes
        # de contrôle satisfont des règles de qualité métier.
        connection.commit()
    except Exception:
        # Une erreur annule l'ensemble de la construction afin de ne pas exposer
        # un DWH partiellement reconstruit, puis elle remonte au pipeline principal.
        connection.rollback()
        logging.exception(
            "Construction du DWH interrompue (moteur=%s, script=%s)",
            ENGINE_LABELS[engine],
            script_path,
        )
        raise

    logging.info("DWH dwh construit avec succès.")
