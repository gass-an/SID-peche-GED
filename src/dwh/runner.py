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
    try:
        relative_path = SCRIPT_PATHS[engine]
    except KeyError as exc:
        raise ValueError(f"Moteur DWH non pris en charge : {db_engine}") from exc
    return PROJECT_ROOT / relative_path


def split_sqlserver_batches(script: str) -> list[str]:
    """Découpe un script uniquement sur les lignes constituées de GO."""
    return [batch.strip() for batch in GO_SEPARATOR.split(script) if batch.strip()]


def _consume_result_sets(cursor: Any) -> None:
    """Consomme les résultats de contrôle sans imposer leur journalisation."""
    while True:
        if getattr(cursor, "description", None) is not None:
            cursor.fetchall()
        nextset = getattr(cursor, "nextset", None)
        if nextset is None or not nextset():
            return


def ensure_env_mer_exists(connection: Any, db_engine: str) -> None:
    """Vérifie que le schéma ODS requis existe dans la base courante."""
    engine = db_engine.strip().lower()
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
    """Exécute transactionnellement le script DWH du moteur sélectionné."""
    engine = db_engine.strip().lower()
    script_path = get_dwh_script_path(engine)
    script = script_path.read_text(encoding="utf-8")
    logging.info("Construction du DWH...")
    logging.info("Moteur : %s", ENGINE_LABELS[engine])

    try:
        with connection.cursor() as cursor:
            if engine == "postgresql":
                cursor.execute(script)
                _consume_result_sets(cursor)
            else:
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
        connection.commit()
    except Exception:
        connection.rollback()
        logging.exception(
            "Construction du DWH interrompue (moteur=%s, script=%s)",
            ENGINE_LABELS[engine],
            script_path,
        )
        raise

    logging.info("DWH dwh construit avec succès.")
