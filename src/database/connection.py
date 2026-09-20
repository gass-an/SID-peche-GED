from __future__ import annotations

import psycopg
from psycopg import Connection

from src.config import Settings


def connect(settings: Settings) -> Connection:
    return psycopg.connect(**settings.postgres_kwargs)


def check_connection(connection: Connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    # SELECT ouvre une transaction avec l'autocommit désactivé. La terminer ici
    # garantit que reset_tables() démarre bien une transaction racine atomique.
    connection.commit()
