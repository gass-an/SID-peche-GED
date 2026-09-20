from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from src.database.schema import CHILD_TABLES, FRAIS, TABLE_COLUMNS


@dataclass(frozen=True)
class NormalizedRows:
    parent: dict[str, Any]
    children: list[dict[str, Any]]


def _parent(row: dict[str, Any], table_name: str) -> dict[str, Any]:
    return {column: row.get(column) for column in TABLE_COLUMNS[table_name]}


def _children(row: dict[str, Any], field: str) -> list[dict[str, Any]]:
    value = row.get(field)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field} doit être une liste ou null")
    if not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{field} contient un élément qui n'est pas un objet")
    return value


def normalize_navire(row: dict[str, Any]) -> NormalizedRows:
    navire_id = row.get("navire_id")
    children = [
        {"moteur_id": item.get("id"), "navire_id": navire_id,
         "usage": item.get("usage"), "marque": item.get("marque"),
         "carburant": item.get("carburant")}
        for item in _children(row, "moteurs")
    ]
    return NormalizedRows(_parent(row, "navire_peche_anonymise"), children)


def normalize_pecheur(row: dict[str, Any]) -> NormalizedRows:
    carte_id = row.get("carte_id")
    children = [
        {"carte_id": carte_id, "code": item.get("code"), "nom": item.get("nom"),
         "zone": item.get("zone"), "taille": item.get("taille"),
         "periode": item.get("periode"), "quantite": item.get("quantite"),
         "description": item.get("description")}
        for item in _children(row, "carte_pecherie_specifique_details")
    ]
    return NormalizedRows(_parent(row, "pecheur_anonymise"), children)


def normalize_campagne(row: dict[str, Any]) -> NormalizedRows:
    details = _children(row, "campagne_frais_details")
    if len(details) > 1:
        raise ValueError(
            "campagne_frais_details contient plusieurs objets; "
            "arrêt pour éviter toute perte de données"
        )
    children = []
    if details:
        children = [
            {
                "campagne_id": row.get("campagne_id"),
                "frais_id": frais_id,
                "montant": details[0].get(frais_id),
            }
            for frais_id in FRAIS
            if details[0].get(frais_id) is not None
        ]
    return NormalizedRows(_parent(row, "campagne_peche"), children)


def normalize_capture(row: dict[str, Any]) -> NormalizedRows:
    capture_id = row.get("capture_id")
    children = [
        {"capture_id": capture_id, "zone_peche_id": item.get("zone_peche_id"),
         "label": item.get("label")}
        for item in _children(row, "capture_zone_details")
    ]
    return NormalizedRows(_parent(row, "capture_peche"), children)


NORMALIZERS: dict[str, Callable[[dict[str, Any]], NormalizedRows]] = {
    "navire_peche_anonymise": normalize_navire,
    "pecheur_anonymise": normalize_pecheur,
    "campagne_peche": normalize_campagne,
    "capture_peche": normalize_capture,
}


def normalize_page(
    table_name: str, rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], str | None, list[dict[str, Any]]]:
    normalizer = NORMALIZERS.get(table_name)
    if normalizer is None:
        return [_parent(row, table_name) for row in rows], None, []
    normalized = [normalizer(row) for row in rows]
    return (
        [item.parent for item in normalized],
        CHILD_TABLES[table_name],
        [child for item in normalized for child in item.children],
    )
