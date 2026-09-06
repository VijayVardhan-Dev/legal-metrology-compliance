from app.nutrition.parser import parse_nutrition


def test_parses_flattened_ocr_without_nutrition_heading():
    text = "Energy 450 kcal Protein 6.5 g Total Fat 18 g Carbohydrates 62 g Total Sugars 25 g Sodium 120 mg Ingredients: wheat flour, sugar"

    nutrition, confidence = parse_nutrition(text, 0.92)

    assert nutrition["Energy"]["value"] == "450"
    assert nutrition["Energy"]["unit"] == "kcal"
    assert nutrition["Protein"]["value"] == "6.5"
    assert nutrition["Total Fat"]["value"] == "18"
    assert nutrition["Sodium"]["value"] == "120"
    assert confidence > 0


def test_parses_common_heading_variant_and_does_not_guess_missing_unit():
    text = "Nutritional Info per 100ml\nEnergy 210\nProtein 3 g\nIngredients: milk, sugar"

    nutrition, confidence = parse_nutrition(text, 0.9)

    assert nutrition["Energy"]["value"] == "210"
    assert nutrition["Energy"]["unit"] == "Not detected"
    assert nutrition["Energy"]["basis"] == "per 100ml"
    assert confidence > 0


def test_parses_parenthesized_nutrient_unit():
    nutrition, confidence = parse_nutrition("Nutrition Facts per 100 g\nEnergy (kcal) 450", 0.9)

    assert nutrition["Energy"]["value"] == "450"
    assert nutrition["Energy"]["unit"] == "kcal"
    assert confidence > 0


def test_handles_ocr_label_variants_and_basis_between_label_and_value():
    nutrition, confidence = parse_nutrition(
        "Nutrition Information\nEnerqy per 100 g 450 kcal\nSodlum 120 mg\nPr0tein 6 g",
        0.9,
    )

    assert nutrition["Energy"]["value"] == "450"
    assert nutrition["Energy"]["basis"] == "per 100 g"
    assert nutrition["Sodium"]["value"] == "120"
    assert nutrition["Protein"]["value"] == "6"
    assert confidence >= 0.8


def test_rejects_implausible_neighbor_number_for_dietary_fibre():
    nutrition, _ = parse_nutrition(
        "Nutrition Information\nDietary Fibre 259\nProtein 6 g",
        0.9,
    )

    assert nutrition["Dietary Fibre"]["value"] == "Not detected"
    assert nutrition["Dietary Fibre"]["unit"] == ""
