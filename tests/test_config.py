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
