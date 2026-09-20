from unittest.mock import Mock

import pytest

from src.api.province_sud_client import PaginationError, ProvinceSudClient


def response(payload: dict) -> Mock:
    """Construit une réponse HTTP factice contenant le JSON fourni."""
    mocked = Mock()
    mocked.json.return_value = payload
    mocked.raise_for_status.return_value = None
    return mocked


def test_pagination_keeps_api_key_and_uses_dynamic_cursor() -> None:
    """Vérifie la conservation de la clé et l'emploi du curseur dynamique."""
    session = Mock()
    session.get.side_effect = [
        response({"data": [{"navire_id": "1"}], "hasNextPage": True,
                  "paramsNextPageQuery": {"custom_id|Gt": "1"}}),
        response({"data": [{"navire_id": "2"}], "hasNextPage": False}),
    ]
    client = ProvinceSudClient("secret", session=session)

    assert list(client.fetch_pages("navire_peche_anonymise")) == [
        [{"navire_id": "1"}], [{"navire_id": "2"}]
    ]
    assert session.get.call_args_list[0].kwargs["params"] == {"apiKey": "secret"}
    assert session.get.call_args_list[1].kwargs["params"] == {
        "apiKey": "secret", "custom_id|Gt": "1"
    }


def test_stops_when_has_next_page_is_false() -> None:
    """Vérifie l'arrêt lorsque la source annonce la dernière page."""
    session = Mock()
    session.get.return_value = response({"data": [], "hasNextPage": False})
    assert list(ProvinceSudClient("secret", session=session).fetch_pages("capture_peche")) == [[]]
    session.get.assert_called_once()


def test_repeated_cursor_is_rejected() -> None:
    """Vérifie qu'un curseur répété ne provoque pas de boucle infinie."""
    session = Mock()
    page = response({"data": [], "hasNextPage": True,
                     "paramsNextPageQuery": {"capture_id|Gt": "abc"}})
    session.get.side_effect = [page, page]
    with pytest.raises(PaginationError, match="pagination bloquée"):
        list(ProvinceSudClient("secret", session=session).fetch_pages("capture_peche"))


@pytest.mark.parametrize("cursor", [None, {}])
def test_missing_cursor_with_next_page_is_rejected(cursor: object) -> None:
    """Vérifie le rejet d'une page suivante dépourvue de curseur."""
    session = Mock()
    session.get.return_value = response({"data": [], "hasNextPage": True,
                                         "paramsNextPageQuery": cursor})
    with pytest.raises(PaginationError, match="absent ou vide"):
        list(ProvinceSudClient("secret", session=session).fetch_pages("capture_peche"))


def test_api_key_from_response_cursor_cannot_replace_secret() -> None:
    """Vérifie qu'un curseur distant ne peut remplacer la clé privée."""
    session = Mock()
    session.get.side_effect = [
        response({"data": [], "hasNextPage": True,
                  "paramsNextPageQuery": {"apiKey": "hostile", "id|Gt": "1"}}),
        response({"data": [], "hasNextPage": False}),
    ]
    list(ProvinceSudClient("secret", session=session).fetch_pages("capture_peche"))
    assert session.get.call_args_list[1].kwargs["params"]["apiKey"] == "secret"
