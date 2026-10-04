from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


def is_sqlserver(connection: Any) -> bool:
    """Indique si une connexion provient du pilote SQL Server pyodbc."""
    # Examiner le module évite d'importer pyodbc : une installation consacrée
    # à PostgreSQL reste ainsi utilisable sans le pilote SQL Server.
    return connection.__class__.__module__.split(".")[0] == "pyodbc"


def quote_identifier(identifier: str, *, sqlserver: bool) -> str:
    """Protège un identifiant SQL selon le dialecte sélectionné."""
    # La validation précède la citation, car encadrer un texte arbitraire ne
    # suffirait pas à sécuriser les identifiants construits dynamiquement.
    if not identifier or not identifier.replace("_", "").isalnum():
        raise ValueError(f"Identifiant SQL invalide : {identifier}")
    return f"[{identifier}]" if sqlserver else f'"{identifier}"'


def qualified_table(table_name: str, *, sqlserver: bool) -> str:
    """Construit le nom qualifié et protégé d'une table du schéma env_mer."""
    schema = quote_identifier("env_mer", sqlserver=sqlserver)
    table = quote_identifier(table_name, sqlserver=sqlserver)
    return f"{schema}.{table}"


@contextmanager
def transaction(connection: Any) -> Iterator[None]:
    """Ouvre une transaction compatible avec PostgreSQL et SQL Server."""
    if not is_sqlserver(connection):
        # Le gestionnaire psycopg valide ou annule automatiquement le bloc.
        with connection.transaction():
            yield
        return

    # pyodbc n'expose pas le même gestionnaire : commit et rollback reproduisent
    # explicitement la même garantie d'atomicité.
    try:
        yield
        connection.commit()
    except Exception:
        connection.rollback()
        raise
