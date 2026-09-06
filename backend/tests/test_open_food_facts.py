from unittest.mock import Mock, patch

from app.services.open_food_facts_service import lookup_product


def test_product_found_is_normalized_without_api_key():
    payload = {
        "status": 1,
        "product": {
            "product_name": "Test Biscuit",
            "brands": "Test Brand",
            "ingredients_text": "wheat flour, sugar",
            "allergens_tags": ["en:gluten", "en:milk"],
            "additives_tags": ["en:e322"],
            "nutriments": {"energy-kcal_100g": 450, "sugars_100g": 20, "sodium_100g": 0.2},
            "nutriscore_grade": "c",
            "nova_group": 4,
        },
    }
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    with patch("app.services.open_food_facts_service.httpx.get", return_value=response):
        result = lookup_product("1234567890123")
    assert result["status"] == "FOUND"
    assert result["product_name"] == "Test Biscuit"
    assert result["nutrition"]["Energy"]["value"] == "450"


def test_product_not_found_does_not_raise():
    response = Mock()
    response.json.return_value = {"status": 0}
    response.raise_for_status.return_value = None
    with patch("app.services.open_food_facts_service.httpx.get", return_value=response):
        result = lookup_product("4006381333931")
    assert result["status"] == "NOT_FOUND"


def test_missing_barcode_is_non_fatal():
    result = lookup_product(None)
    assert result["status"] == "NOT_DETECTED"
