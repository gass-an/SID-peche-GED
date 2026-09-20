from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from src.config import TABLES
from src.database.dialect import (
    is_sqlserver,
    qualified_table,
    quote_identifier,
    transaction,
)
from src.database.schema import TABLE_COLUMNS, managed_tables


def _insert_batch(
    connection: Any, table_name: str, rows: Sequence[dict[str, Any]]
) -> None:
    """Insère un lot de lignes dans une table gérée."""
    if not rows:
        return
    columns = TABLE_COLUMNS[table_name]
    sqlserver = is_sqlserver(connection)
    column_list = ", ".join(
        quote_identifier(column, sqlserver=sqlserver) for column in columns
    )
    placeholder = "?" if sqlserver else "%s"
    placeholders = ", ".join(placeholder for _ in columns)
    statement = (
        f"INSERT INTO {qualified_table(table_name, sqlserver=sqlserver)} "
        f"({column_list}) VALUES ({placeholders})"
    )
    values = [tuple(row.get(column) for column in columns) for row in rows]
    with connection.cursor() as cursor:
        cursor.executemany(statement, values)


def insert_page(
    connection: Any,
    parent_table: str,
    parent_rows: Sequence[dict[str, Any]],
    child_table: str | None,
    child_rows: Sequence[dict[str, Any]],
) -> None:
    """Insère atomiquement une page de lignes parentes et enfants."""
    if parent_table not in TABLES:
        raise ValueError(f"Table principale inconnue : {parent_table}")
    with transaction(connection):
        _insert_batch(connection, parent_table, parent_rows)
        if child_table is not None:
            _insert_batch(connection, child_table, child_rows)


def count_rows(connection: Any, table_name: str) -> int:
    """Compte les lignes d'une table gérée."""
    if table_name not in managed_tables(TABLES):
        raise ValueError(f"Table gérée inconnue : {table_name}")
    sqlserver = is_sqlserver(connection)
    with transaction(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(*) FROM "
                f"{qualified_table(table_name, sqlserver=sqlserver)}"
            )
            result = cursor.fetchone()
    return int(result[0])


def find_json_columns(
    connection: Any, source_tables: list[str]
) -> list[tuple[str, str, str]]:
    """Recherche les colonnes JSON résiduelles dans les tables demandées."""
    tables = managed_tables(source_tables)
    sqlserver = is_sqlserver(connection)
    placeholder = "?" if sqlserver else "%s"
    table_placeholders = ", ".join(placeholder for _ in tables)
    json_types = "('json')" if sqlserver else "('json', 'jsonb')"
    with transaction(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'env_mer'
                  AND data_type IN {json_types}
                  AND table_name IN ({table_placeholders})
                ORDER BY table_name, column_name
                """,
                tuple(tables),
            )
            return list(cursor.fetchall())


def relation_statistics(connection: Any) -> list[tuple[str, int, int, int]]:
    """Calcule les statistiques d'intégrité des principales relations."""
    relations = [
        ("carte_autorisation_navire_id", "pecheur_anonymise", "navire_peche_anonymise", "navire_id"),
        ("navire_id", "navire_moteur", "navire_peche_anonymise", "navire_id"),
        ("carte_id", "carte_pecherie_specifique", "pecheur_anonymise", "carte_id"),
        ("campagne_carte_id", "campagne_peche", "pecheur_anonymise", "carte_id"),
        ("campagne_id", "campagne_frais", "campagne_peche", "campagne_id"),
        ("frais_id", "campagne_frais", "frais", "frais_id"),
        ("capture_campagne_id", "capture_peche", "campagne_peche", "campagne_id"),
        ("capture_id", "capture_zone", "capture_peche", "capture_id"),
    ]
    statistics = []
    sqlserver = is_sqlserver(connection)
    with transaction(connection):
        with connection.cursor() as cursor:
            for column, source, target, target_id in relations:
                column_id = quote_identifier(column, sqlserver=sqlserver)
                target_id_sql = quote_identifier(target_id, sqlserver=sqlserver)
                source_table = qualified_table(source, sqlserver=sqlserver)
                target_table = qualified_table(target, sqlserver=sqlserver)
                query = f"""
                    SELECT COUNT(s.{column_id}), COUNT(t.{target_id_sql}),
                           COUNT(s.{column_id}) - COUNT(t.{target_id_sql})
                    FROM {source_table} s
                    LEFT JOIN {target_table} t
                      ON t.{target_id_sql} = s.{column_id}
                    WHERE s.{column_id} IS NOT NULL
                """
                cursor.execute(query)
                non_null, valid, orphans = cursor.fetchone()
                statistics.append((f"{source}.{column}", non_null, valid, orphans))
    return statistics
