from src.config import TABLES
from src.database.schema import (
    SQLSERVER_TABLE_DEFINITIONS,
    TABLE_DEFINITIONS,
    managed_tables,
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
    assert " FLOAT" in definitions
    assert " BIT" in definitions
