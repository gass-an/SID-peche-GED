import re

from src.config import TABLES
from src.database.schema import (
    SQLSERVER_TABLE_DEFINITIONS,
    TABLE_COLUMNS,
    TABLE_DEFINITIONS,
    managed_tables,
    reset_tables,
)


EXPECTED_TABLES = {
    "pecheur_anonymise",
    "navire_peche_anonymise",
    "navire_moteur",
    "carte_pecherie_specifique",
    "campagne_peche",
    "frais",
    "campagne_frais",
    "capture_peche",
    "capture_zone",
    "carroyage_peche",
}


def test_schema_contains_exactly_the_ten_expected_tables() -> None:
    """Vérifie que le schéma contient exactement les dix tables prévues."""
    assert set(managed_tables(TABLES)) == EXPECTED_TABLES
    assert EXPECTED_TABLES <= TABLE_DEFINITIONS.keys()


def test_schema_defines_the_eight_expected_foreign_keys() -> None:
    """Vérifie la présence des huit clés étrangères attendues."""
    definitions = " ".join(TABLE_DEFINITIONS[name] for name in EXPECTED_TABLES)
    assert definitions.count("FOREIGN KEY") == 8


def test_sqlserver_schema_uses_compatible_data_types() -> None:
    """Vérifie la conversion des types propres à PostgreSQL."""
    definitions = " ".join(SQLSERVER_TABLE_DEFINITIONS.values())

    assert "DOUBLE PRECISION" not in definitions
    assert "BOOLEAN" not in definitions
    assert re.search(r"\bNUMERIC\b(?!\s*\()", definitions) is None
    assert " FLOAT" in definitions
    assert " BIT" in definitions
    assert "DECIMAL(18,8)" in definitions


def test_sqlserver_schema_defines_every_column_exactly_once() -> None:
    """Vérifie que chaque attribut normalisé possède une colonne SQL Server."""
    column_pattern = re.compile(
        r"(?:^|, )([a-z_][a-z0-9_]*) "
        r"(?:VARCHAR|FLOAT|INTEGER|DATE|BIT|DECIMAL)"
    )

    for table_name, expected_columns in TABLE_COLUMNS.items():
        definition = SQLSERVER_TABLE_DEFINITIONS[table_name]
        assert column_pattern.findall(definition) == expected_columns


def test_sqlserver_varchar_lengths_are_valid() -> None:
    """Vérifie que les tailles VARCHAR respectent la limite de SQL Server."""
    for definition in SQLSERVER_TABLE_DEFINITIONS.values():
        lengths = re.findall(r"VARCHAR\((\d+)\)", definition)
        assert all(1 <= int(length) <= 8000 for length in lengths)


def test_sqlserver_reset_passes_a_sequence_to_executemany() -> None:
    """Vérifie que pyodbc reçoit une liste pour l'insertion des frais."""

    class FakeCursor:
        """Curseur minimal enregistrant les commandes du test."""

        def __enter__(self):
            """Retourne le curseur factice."""
            return self

        def __exit__(self, *_args):
            """Termine le contexte sans masquer les exceptions."""
            return False

        def execute(self, _statement):
            """Accepte une commande SQL unitaire."""
            return self

        def executemany(self, _statement, rows):
            """Imite l'exigence de pyodbc concernant la séquence de lignes."""
            assert isinstance(rows, list)

    class FakeConnection:
        """Connexion SQL Server minimale utilisée sans serveur réel."""

        def cursor(self):
            """Crée un curseur factice."""
            return FakeCursor()

        def commit(self):
            """Simule la validation de la transaction."""

        def rollback(self):
            """Simule l'annulation de la transaction."""

    FakeConnection.__module__ = "pyodbc"

    reset_tables(FakeConnection(), TABLES)
