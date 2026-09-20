from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

TABLES = [
    "navire_peche_anonymise",
    "pecheur_anonymise",
    "campagne_peche",
    "carroyage_peche",
    "capture_peche",
]
API_BASE_URL = "https://www.province-sud.nc/drhouseweb/api/UNC_WEB/env_mer"


@dataclass(frozen=True)
class Settings:
    api_key: str
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str
    http_timeout: float
    raw_data_dir: Path

    @property
    def postgres_kwargs(self) -> dict[str, object]:
        """Retourne les paramètres de connexion attendus par psycopg."""
        return {
            "host": self.postgres_host,
            "port": self.postgres_port,
            "dbname": self.postgres_db,
            "user": self.postgres_user,
            "password": self.postgres_password,
        }


def load_settings(*, require_api_key: bool = True) -> Settings:
    """Charge et valide la configuration depuis les variables d'environnement."""
    load_dotenv()
    api_key = os.getenv("PROVINCE_SUD_API_KEY", "").strip()
    if require_api_key and not api_key:
        raise ValueError(
            "PROVINCE_SUD_API_KEY est absente. Renseignez-la dans le fichier .env."
        )
    try:
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        timeout = float(os.getenv("HTTP_TIMEOUT", "30"))
    except ValueError as exc:
        raise ValueError("POSTGRES_PORT et HTTP_TIMEOUT doivent être numériques.") from exc
    if timeout <= 0:
        raise ValueError("HTTP_TIMEOUT doit être strictement positif.")
    return Settings(
        api_key=api_key,
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=port,
        postgres_db=os.getenv("POSTGRES_DB", "peche_nc"),
        postgres_user=os.getenv("POSTGRES_USER", "admin"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", "admin"),
        http_timeout=timeout,
        raw_data_dir=Path(__file__).resolve().parent.parent / "data" / "raw",
    )


def validate_table_name(table_name: str) -> str:
    """Valide le nom d'une table source et le retourne inchangé."""
    if table_name not in TABLES:
        allowed = ", ".join(TABLES)
        raise ValueError(f"Table inconnue : {table_name}. Tables autorisées : {allowed}")
    return table_name
