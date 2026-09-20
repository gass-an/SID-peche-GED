import pytest

from src.config import load_settings, validate_table_name


def test_validate_table_name_accepts_known_table() -> None:
    """Vérifie qu'une table déclarée est acceptée."""
    assert validate_table_name("capture_peche") == "capture_peche"


def test_validate_table_name_rejects_unknown_table() -> None:
    """Vérifie qu'une table inconnue est rejetée explicitement."""
    with pytest.raises(ValueError, match="Table inconnue"):
        validate_table_name("not_a_table")


def test_api_key_is_optional_for_local_json_mode(monkeypatch) -> None:
    """Vérifie que le mode JSON local ne requiert pas de clé d'API."""
    monkeypatch.setattr("src.config.load_dotenv", lambda: None)
    monkeypatch.delenv("PROVINCE_SUD_API_KEY", raising=False)

    assert load_settings(require_api_key=False).api_key == ""


def test_postgresql_is_the_default_database_engine(monkeypatch) -> None:
    """Vérifie que l'environnement existant reste sur PostgreSQL par défaut."""
    monkeypatch.setattr("src.config.load_dotenv", lambda: None)
    monkeypatch.delenv("DB_ENGINE", raising=False)

    assert load_settings(require_api_key=False).db_engine == "postgresql"


def test_sqlserver_requires_a_connection_string(monkeypatch) -> None:
    """Vérifie que SQL Server ne démarre pas sans chaîne de connexion."""
    monkeypatch.setattr("src.config.load_dotenv", lambda: None)
    monkeypatch.setenv("DB_ENGINE", "sqlserver")
    monkeypatch.delenv("SQLSERVER_CONNECTION_STRING", raising=False)

    with pytest.raises(ValueError, match="SQLSERVER_CONNECTION_STRING"):
        load_settings(require_api_key=False)


def test_sqlserver_accepts_windows_authentication_string(monkeypatch) -> None:
    """Vérifie le chargement d'une connexion SQL Server intégrée à Windows."""
    connection_string = (
        "Driver={ODBC Driver 18 for SQL Server};Server=localhost\\SQLEXPRESS;"
        "Database=peche_nc;Trusted_Connection=yes"
    )
    monkeypatch.setattr("src.config.load_dotenv", lambda: None)
    monkeypatch.setenv("DB_ENGINE", "sqlserver")
    monkeypatch.setenv("SQLSERVER_CONNECTION_STRING", connection_string)

    settings = load_settings(require_api_key=False)

    assert settings.db_engine == "sqlserver"
    assert settings.sqlserver_connection_string == connection_string
