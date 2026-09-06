import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)
OPEN_FOOD_FACTS_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
_CACHE: dict[str, dict[str, Any]] = {}


def _nutrition(product: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values = product.get("nutriments") or {}
    mapping = {
        "Energy": ("energy-kcal_100g", "kcal"),
        "Protein": ("proteins_100g", "g"),
        "Total Fat": ("fat_100g", "g"),
        "Saturated Fat": ("saturated-fat_100g", "g"),
        "Carbohydrates": ("carbohydrates_100g", "g"),
        "Total Sugars": ("sugars_100g", "g"),
        "Added Sugars": ("added-sugars_100g", "g"),
        "Dietary Fibre": ("fiber_100g", "g"),
        "Sodium": ("sodium_100g", "g"),
        "Salt": ("salt_100g", "g"),
    }
    result = {}
    for label, (key, unit) in mapping.items():
        value = values.get(key)
        if value is not None:
            result[label] = {"value": str(value), "unit": unit, "basis": "per 100 g", "source": "Open Food Facts"}
    return result


def lookup_product(barcode: str | None) -> dict[str, Any]:
    if not barcode:
        return {"status": "NOT_DETECTED", "message": "Barcode not detected. Nutrition analysis is based on the information extracted from the product label."}
    if barcode in _CACHE:
        return _CACHE[barcode]
    if not barcode.isdigit() or not 8 <= len(barcode) <= 14:
        return {"status": "INVALID", "barcode": barcode, "message": "The detected barcode is invalid."}
    try:
        response = httpx.get(
            OPEN_FOOD_FACTS_URL.format(barcode=barcode),
            timeout=httpx.Timeout(8.0, connect=3.0),
            headers={"User-Agent": "LegalMetrologyCompliance/1.0"},
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Open Food Facts lookup failed for %s: %s", barcode, exc)
        return {"status": "UNAVAILABLE", "barcode": barcode, "message": "Product database unavailable. Continuing analysis using the uploaded product label."}

    if payload.get("status") != 1 or not payload.get("product"):
        result = {"status": "NOT_FOUND", "barcode": barcode, "message": "Product not found in Open Food Facts. Continuing analysis using the uploaded product label."}
        _CACHE[barcode] = result
        return result

    product = payload["product"]
    result = {
        "status": "FOUND",
        "barcode": barcode,
        "source": "Open Food Facts",
        "product_name": product.get("product_name") or product.get("product_name_en"),
        "brands": product.get("brands"),
        "ingredients_text": product.get("ingredients_text") or product.get("ingredients_text_en"),
        "allergens": product.get("allergens_tags") or [],
        "additives": product.get("additives_tags") or [],
        "serving_size": product.get("serving_size"),
        "quantity": product.get("quantity"),
        "nutri_score": product.get("nutriscore_grade"),
        "nova_group": product.get("nova_group"),
        "nutrition": _nutrition(product),
    }
    _CACHE[barcode] = result
    return result
