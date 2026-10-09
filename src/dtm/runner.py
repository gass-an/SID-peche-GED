from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.database.sql_script import execute_sql_script

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DTM_DIRECTORIES = {
    "postgresql": Path("sql/postgresql/dtm"),
    "sqlserver": Path("sql/sqlserver/dtm"),
}
ENGINE_LABELS = {"postgresql": "PostgreSQL", "sqlserver": "SQL Server"}


def discover_dtm_scripts(db_engine: str) -> list[Path]:
    """Découvre les scripts DTM du moteur dans un ordre déterministe."""
    engine = db_engine.strip().lower()
    try:
        relative_directory = DTM_DIRECTORIES[engine]
    except KeyError as exc:
        raise ValueError(f"Moteur DTM non pris en charge : {db_engine}") from exc

    dtm_directory = PROJECT_ROOT / relative_directory
    # Un seul niveau de sous-dossier matérialise le nom technique du Data Mart.
    scripts = sorted(
        dtm_directory.glob("*/init.sql"), key=lambda path: path.parent.name
    )
    if not scripts:
        raise FileNotFoundError(
            f"Aucun script DTM trouvé pour le moteur {engine} dans {dtm_directory}"
        )
    return scripts


def run_dtms(connection: Any, db_engine: str) -> None:
    """Exécute successivement tous les Data Marts disponibles pour le moteur."""
    engine = db_engine.strip().lower()
    scripts = discover_dtm_scripts(engine)
    logging.info("Construction des Data Marts...")

    # Chaque script possède sa propre transaction : les exécuter séparément
    # préserve les DTM déjà validés si un script suivant échoue.
    for script_path in scripts:
        dtm_name = script_path.parent.name
        logging.info("DTM %s : démarrage", dtm_name)
        try:
            execute_sql_script(connection, engine, script_path)
        except Exception:
            logging.exception(
                "Construction du DTM interrompue "
                "(moteur=%s, dtm=%s, script=%s)",
                ENGINE_LABELS[engine],
                dtm_name,
                script_path,
            )
            raise
        logging.info("DTM %s : terminé", dtm_name)
