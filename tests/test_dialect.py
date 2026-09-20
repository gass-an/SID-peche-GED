from src.database.dialect import qualified_table, quote_identifier


def test_postgresql_identifiers_use_double_quotes() -> None:
    """Vérifie la protection des identifiants PostgreSQL."""
    assert qualified_table("capture_peche", sqlserver=False) == (
        '"env_mer"."capture_peche"'
    )


def test_sqlserver_identifiers_use_brackets() -> None:
    """Vérifie la protection des identifiants SQL Server."""
    assert qualified_table("capture_peche", sqlserver=True) == (
        "[env_mer].[capture_peche]"
    )


def test_identifier_rejects_sql_injection() -> None:
    """Vérifie qu'un nom arbitraire ne peut pas devenir du SQL exécutable."""
    try:
        quote_identifier("capture_peche; DROP TABLE x", sqlserver=True)
    except ValueError:
        pass
    else:
        raise AssertionError("Un identifiant SQL dangereux a été accepté")
