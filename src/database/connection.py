from __future__ import annotations

from typing import Any

import psycopg

from src.config import Settings


def connect(settings: Settings) -> Any:
    """Ouvre une connexion avec le moteur sélectionné dans la configuration."""
    if settings.db_engine == "postgresql":
        return psycopg.connect(**settings.postgres_kwargs)

    # Import différé : PostgreSQL reste utilisable sans pilote SQL Server.
    import pyodbc

    return pyodbc.connect(settings.sqlserver_connection_string)


def check_connection(connection: Any) -> None:
    """Vérifie que la connexion répond puis clôt la transaction de contrôle."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    # SELECT ouvre une transaction avec l'autocommit désactivé. La terminer ici
    # garantit que reset_tables() démarre bien une transaction racine atomique.
    connection.commit()
