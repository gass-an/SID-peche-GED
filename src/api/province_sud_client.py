from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config import API_BASE_URL, validate_table_name


class PaginationError(RuntimeError):
    """Réponse de pagination incohérente ou bloquée."""


class ProvinceSudClient:
    def __init__(
        self,
        api_key: str,
        timeout: float = 30,
        session: requests.Session | None = None,
    ) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.session = session or self._build_session()

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=5,
            connect=3,
            read=3,
            backoff_factor=0.8,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
        )
        session.mount("https://", HTTPAdapter(max_retries=retry))
        return session

    def fetch_pages(self, table_name: str) -> Iterator[list[dict[str, Any]]]:
        validate_table_name(table_name)
        url = f"{API_BASE_URL}/{table_name}/data"
        cursor: dict[str, Any] = {}
        seen_cursors: set[tuple[tuple[str, str], ...]] = set()
        page_number = 1

        while True:
            params = {"apiKey": self.api_key, **cursor}
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
            except requests.RequestException as exc:
                # Le texte d'une exception requests peut contenir l'URL complète,
                # donc apiKey. Ne jamais le recopier dans notre message.
                status = getattr(exc.response, "status_code", None)
                detail = f"statut HTTP {status}" if status else type(exc).__name__
                raise RuntimeError(
                    f"[{table_name}] page {page_number}, étape HTTP : {detail}"
                ) from exc
            try:
                payload = response.json()
            except ValueError as exc:
                raise RuntimeError(
                    f"[{table_name}] page {page_number}, étape décodage JSON : "
                    "réponse JSON invalide."
                ) from exc

            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                raise RuntimeError(
                    f"[{table_name}] page {page_number}, étape validation : "
                    "le champ data doit être une liste."
                )
            has_next_page = payload.get("hasNextPage") is True
            if has_next_page:
                next_cursor = payload.get("paramsNextPageQuery")
                if not isinstance(next_cursor, dict) or not next_cursor:
                    raise PaginationError(
                        f"[{table_name}] page {page_number}, étape pagination : "
                        "hasNextPage vaut true mais paramsNextPageQuery est absent ou vide."
                    )
                safe_cursor = {
                    key: value for key, value in next_cursor.items() if key != "apiKey"
                }
                if not safe_cursor:
                    raise PaginationError(
                        f"[{table_name}] page {page_number}, étape pagination : "
                        "paramsNextPageQuery ne contient aucun curseur exploitable."
                    )
                signature = tuple(
                    sorted((str(key), repr(value)) for key, value in safe_cursor.items())
                )
                if signature in seen_cursors:
                    raise PaginationError(
                        f"[{table_name}] page {page_number}, étape pagination : pagination "
                        f"bloquée, paramsNextPageQuery répété : {safe_cursor!r}"
                    )
                seen_cursors.add(signature)

            yield payload["data"]
            if not has_next_page:
                return
            cursor = safe_cursor
            page_number += 1

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "ProvinceSudClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
