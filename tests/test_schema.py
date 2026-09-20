from src.config import TABLES
from src.database.schema import TABLE_DEFINITIONS, managed_tables


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
    assert set(managed_tables(TABLES)) == EXPECTED_TABLES
    assert EXPECTED_TABLES <= TABLE_DEFINITIONS.keys()


def test_schema_defines_the_eight_expected_foreign_keys() -> None:
    definitions = " ".join(TABLE_DEFINITIONS[name] for name in EXPECTED_TABLES)
    assert definitions.count("FOREIGN KEY") == 8
