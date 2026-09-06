from app.nutrition.parser import (
    build_insights,
    detect_allergens,
    parse_ingredients,
    parse_nutrition,
)


def test_parses_nutrition_basis_units_and_insights():
    text = """Nutrition Information per 100 g
Energy 520 kcal
Protein 7 g
Total Fat 12 g
Total Sugars 24 g
Sodium 650 mg"""

    nutrition, confidence = parse_nutrition(text, 0.98)

    assert nutrition["Energy"] == {
        "value": "520",
        "unit": "kcal",
        "basis": "per 100 g",
        "confidence": 0.931,
    }
    assert nutrition["Dietary Fibre"]["value"] == "Not detected"
    assert confidence > 0
    assert "High sugar" in build_insights(nutrition)[0]
    assert any("High sodium" in insight for insight in build_insights(nutrition))


def test_classifies_ingredients_and_detects_declared_allergens():
    text = "Ingredients: Wheat flour, Sugar, Milk powder, Soy lecithin, Preservative. Contains milk and soy."

    ingredients, raw, confidence = parse_ingredients(text, 0.95)
    allergens = detect_allergens(text, ingredients, 0.95)

    assert raw.startswith("Ingredients:")
    assert [item["name"] for item in ingredients] == [
        "Wheat flour", "Sugar", "Milk powder", "Soy lecithin", "Preservative"
    ]
    assert ingredients[1]["category"] == "Sugar/sweetener"
    assert ingredients[1]["assessment"] == "moderation"
    assert {item["name"] for item in allergens} == {"Milk", "Wheat/gluten", "Soy"}
    assert confidence > 0


def test_missing_nutrition_is_not_guessed_and_low_confidence_is_flagged_by_service_contract():
    nutrition, confidence = parse_nutrition("Ingredients: rice flour, salt", 0.4)

    assert all(item["value"] == "Not detected" for item in nutrition.values())
    assert confidence == 0
