from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from psycopg import Connection, sql

from src.config import TABLES
from src.database.schema import TABLE_COLUMNS, managed_tables


def _insert_batch(
    connection: Connection, table_name: str, rows: Sequence[dict[str, Any]]
) -> None:
    """Insère un lot de lignes dans une table gérée."""
    if not rows:
        return
    columns = TABLE_COLUMNS[table_name]
    statement = sql.SQL("INSERT INTO env_mer.{} ({}) VALUES ({})").format(
        sql.Identifier(table_name),
        sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )
    values = [tuple(row.get(column) for column in columns) for row in rows]
    with connection.cursor() as cursor:
        cursor.executemany(statement, values)


def insert_page(
    connection: Connection,
    parent_table: str,
    parent_rows: Sequence[dict[str, Any]],
    child_table: str | None,
    child_rows: Sequence[dict[str, Any]],
) -> None:
    """Insère atomiquement une page de lignes parentes et enfants."""
    if parent_table not in TABLES:
        raise ValueError(f"Table principale inconnue : {parent_table}")
    with connection.transaction():
        _insert_batch(connection, parent_table, parent_rows)
        if child_table is not None:
            _insert_batch(connection, child_table, child_rows)


def count_rows(connection: Connection, table_name: str) -> int:
    """Compte les lignes d'une table gérée."""
    if table_name not in managed_tables(TABLES):
        raise ValueError(f"Table gérée inconnue : {table_name}")
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("SELECT COUNT(*) FROM env_mer.{}").format(
                    sql.Identifier(table_name)
                )
            )
            result = cursor.fetchone()
    return int(result[0])


def find_json_columns(
    connection: Connection, source_tables: list[str]
) -> list[tuple[str, str, str]]:
    """Recherche les colonnes JSON résiduelles dans les tables demandées."""
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'env_mer'
                  AND data_type IN ('json', 'jsonb')
                  AND table_name = ANY(%s)
                ORDER BY table_name, column_name
                """,
                (managed_tables(source_tables),),
            )
            return list(cursor.fetchall())


def relation_statistics(connection: Connection) -> list[tuple[str, int, int, int]]:
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
    with connection.transaction():
        with connection.cursor() as cursor:
            for column, source, target, target_id in relations:
                query = sql.SQL("""
                    SELECT COUNT(s.{column}), COUNT(t.{target_id}),
                           COUNT(s.{column}) - COUNT(t.{target_id})
                    FROM env_mer.{source} s
                    LEFT JOIN env_mer.{target} t ON t.{target_id} = s.{column}
                    WHERE s.{column} IS NOT NULL
                """).format(
                    column=sql.Identifier(column), target_id=sql.Identifier(target_id),
                    source=sql.Identifier(source), target=sql.Identifier(target),
                )
                cursor.execute(query)
                non_null, valid, orphans = cursor.fetchone()
                statistics.append((f"{source}.{column}", non_null, valid, orphans))
    return statistics
