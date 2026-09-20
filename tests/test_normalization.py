import pytest

from src.extraction.normalization import (
    normalize_campagne,
    normalize_capture,
    normalize_navire,
    normalize_pecheur,
)


def test_navire_produces_two_motors_and_removes_json_from_parent() -> None:
    result = normalize_navire({
        "navire_id": "NAV1",
        "moteurs": [
            {"id": "M1", "usage": "Principale", "marque": "YAMAHA", "carburant": "ESSENCE"},
            {"id": "M2", "usage": "De secours", "marque": "SUZUKI", "carburant": "ESSENCE"},
        ],
    })
    assert result.parent["navire_id"] == "NAV1"
    assert "moteurs" not in result.parent
    assert [motor["moteur_id"] for motor in result.children] == ["M1", "M2"]
    assert all(motor["navire_id"] == "NAV1" for motor in result.children)


def test_pecheur_produces_three_specific_fisheries() -> None:
    details = [{"code": code, "nom": code} for code in ("TRO", "VIV", "CRAB")]
    result = normalize_pecheur({
        "carte_id": "CARTE1", "carte_pecherie_specifique_details": details
    })
    assert len(result.children) == 3
    assert all(child["carte_id"] == "CARTE1" for child in result.children)
    assert "carte_pecherie_specifique_details" not in result.parent


def test_campagne_preserves_zero_values() -> None:
    result = normalize_campagne({
        "campagne_id": "C1",
        "campagne_frais_details": [{"mat": 0, "carburant": 12350}],
    })
    assert result.children == [
        {"campagne_id": "C1", "frais_id": "mat", "montant": 0},
        {"campagne_id": "C1", "frais_id": "carburant", "montant": 12350},
    ]
    assert "campagne_frais_details" not in result.parent


def test_campagne_rejects_multiple_fee_objects_to_prevent_data_loss() -> None:
    with pytest.raises(ValueError, match="plusieurs objets"):
        normalize_campagne({"campagne_id": "C1", "campagne_frais_details": [{}, {}]})


def test_capture_produces_multiple_zones() -> None:
    result = normalize_capture({
        "capture_id": "CAP1",
        "capture_zone_details": [
            {"zone_peche_id": "Z1", "label": "Zone 1"},
            {"zone_peche_id": "Z2", "label": "Zone 2"},
        ],
    })
    assert len(result.children) == 2
    assert all(child["capture_id"] == "CAP1" for child in result.children)
    assert "capture_zone_details" not in result.parent


@pytest.mark.parametrize("field_value", [None, []])
@pytest.mark.parametrize(
    ("normalizer", "id_field", "detail_field"),
    [
        (normalize_navire, "navire_id", "moteurs"),
        (normalize_pecheur, "carte_id", "carte_pecherie_specifique_details"),
        (normalize_campagne, "campagne_id", "campagne_frais_details"),
        (normalize_capture, "capture_id", "capture_zone_details"),
    ],
)
def test_null_and_empty_details_create_no_child(
    normalizer, id_field: str, detail_field: str, field_value
) -> None:
    result = normalizer({id_field: "ID1", detail_field: field_value})
    assert result.children == []


@pytest.mark.parametrize(
    ("normalizer", "id_field"),
    [
        (normalize_navire, "navire_id"),
        (normalize_pecheur, "carte_id"),
        (normalize_campagne, "campagne_id"),
        (normalize_capture, "capture_id"),
    ],
)
def test_absent_optional_detail_field_creates_no_child(normalizer, id_field: str) -> None:
    assert normalizer({id_field: "ID1"}).children == []
