import re
from typing import Any


KNOWN_NUTRIENTS = {
    "energy": ("Energy", "kcal"),
    "calories": ("Energy", "kcal"),
    "protein": ("Protein", "g"),
    "total fat": ("Total Fat", "g"),
    "fat": ("Total Fat", "g"),
    "saturated fat": ("Saturated Fat", "g"),
    "trans fat": ("Trans Fat", "g"),
    "carbohydrate": ("Carbohydrates", "g"),
    "carbohydrates": ("Carbohydrates", "g"),
    "total sugars": ("Total Sugars", "g"),
    "sugars": ("Total Sugars", "g"),
    "added sugars": ("Added Sugars", "g"),
    "dietary fibre": ("Dietary Fibre", "g"),
    "dietary fiber": ("Dietary Fibre", "g"),
    "fibre": ("Dietary Fibre", "g"),
    "fiber": ("Dietary Fibre", "g"),
    "sodium": ("Sodium", "mg"),
    "salt": ("Salt", "g"),
}

NUTRIENT_ORDER = [
    "Energy", "Protein", "Total Fat", "Saturated Fat", "Trans Fat",
    "Carbohydrates", "Total Sugars", "Added Sugars", "Dietary Fibre", "Sodium", "Salt",
]

ALLERGENS = {
    "milk": "Milk", "whey": "Milk", "casein": "Milk", "lactose": "Milk",
    "wheat": "Wheat/gluten", "gluten": "Wheat/gluten", "barley": "Wheat/gluten", "rye": "Wheat/gluten",
    "soy": "Soy", "soya": "Soy", "peanut": "Peanuts", "groundnut": "Peanuts",
    "almond": "Tree nuts", "cashew": "Tree nuts", "walnut": "Tree nuts", "hazelnut": "Tree nuts",
    "sesame": "Sesame", "egg": "Egg", "fish": "Fish", "crustacean": "Crustaceans", "shellfish": "Crustaceans",
}


def _lines(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]


def detect_sections(text: str) -> dict[str, Any]:
    lines = _lines(text)
    lowered = [line.lower() for line in lines]
    nutrition_indexes = [i for i, line in enumerate(lowered) if any(
        marker in line for marker in ("nutrition information", "nutrition facts", "nutritional information", "per 100")
    )]
    ingredient_indexes = [i for i, line in enumerate(lowered) if re.search(r"\bingredients?\b", line)]
    allergen_indexes = [i for i, line in enumerate(lowered) if any(
        marker in line for marker in ("contains:", "allergen", "may contain")
    )]
    nutrition_start = nutrition_indexes[0] if nutrition_indexes else None
    ingredient_start = ingredient_indexes[0] if ingredient_indexes else None
    ingredient_end = min(
        [index for index in allergen_indexes if ingredient_start is not None and index > ingredient_start] or [len(lines)]
    )
    nutrition_end = min(
        [index for index in ingredient_indexes + allergen_indexes if nutrition_start is not None and index > nutrition_start] or [len(lines)]
    )
    nutrition_lines = lines[nutrition_start:nutrition_end] if nutrition_start is not None else []
    ingredient_lines = lines[ingredient_start:ingredient_end] if ingredient_start is not None else []
    return {
        "nutrition_text": " ".join(nutrition_lines),
        "ingredient_text": " ".join(ingredient_lines),
        "allergen_text": " ".join(lines[index] for index in allergen_indexes),
        "nutrition_detected": bool(nutrition_lines),
        "ingredients_detected": bool(ingredient_lines),
        "allergens_declared": bool(allergen_indexes),
    }


def _basis(text: str) -> str:
    match = re.search(r"(?:per|for)\s+(100\s*(?:g|ml)|serving|package)", text, re.I)
    return f"per {match.group(1).lower()}" if match else "Not detected"


def _value_match(text: str, label: str) -> re.Match[str] | None:
    return re.search(
        rf"\b{re.escape(label)}\b\s*[:\-]?\s*(\d+(?:[.,]\d+)?)\s*(kcal|kj|g|mg|µg|ug|ml|%)?",
        text,
        re.I,
    )


def parse_nutrition(text: str, ocr_confidence: float | None) -> tuple[dict[str, dict[str, Any]], float]:
    sections = detect_sections(text)
    source = sections["nutrition_text"]
    nutrition: dict[str, dict[str, Any]] = {}
    found = 0
    for key, (label, default_unit) in KNOWN_NUTRIENTS.items():
        if label in nutrition:
            continue
        match = _value_match(source, key)
        if match:
            unit = match.group(2) or default_unit
            nutrition[label] = {
                "value": match.group(1).replace(",", "."),
                "unit": unit,
                "basis": _basis(source),
                "confidence": round(min(1.0, (ocr_confidence or 0.5) * 0.95), 3),
            }
            found += 1
    for label in NUTRIENT_ORDER:
        nutrition.setdefault(label, {
            "value": "Not detected", "unit": "", "basis": "Not detected", "confidence": 0.0,
        })
    confidence = round((found / len(NUTRIENT_ORDER)) * (ocr_confidence or 0.5), 3) if source else 0.0
    return nutrition, confidence


def _ingredient_tokens(text: str) -> list[str]:
    if not text:
        return []
    value = re.sub(r"^.*?\bingredients?\s*[:\-]?", "", text, flags=re.I)
    value = re.split(r"\b(?:contains|allergen information|may contain)\b", value, maxsplit=1, flags=re.I)[0]
    return [token.strip(" .;:-") for token in re.split(r"[,;]", value) if token.strip(" .;:-")]


def classify_ingredient(name: str) -> dict[str, str]:
    lowered = name.lower()
    if any(token in lowered for token in ("sugar", "syrup", "jaggery", "maltodextrin", "sweetener")):
        return {"category": "Sugar/sweetener", "purpose": "Adds sweetness or bulk", "assessment": "moderation", "reason": "High intake of added sugars may be a nutritional concern; quantity was not inferred."}
    if any(token in lowered for token in ("oil", "fat", "butter", "shortening")):
        return {"category": "Oil/fat", "purpose": "Provides texture or carries flavour", "assessment": "moderation", "reason": "The label identifies a fat source; its overall dietary impact depends on the amount and type."}
    if any(token in lowered for token in ("flour", "wheat", "rice", "oat", "maize", "corn", "cereal")):
        return {"category": "Grain/cereal", "purpose": "Provides structure or carbohydrate", "assessment": "common", "reason": "Common food ingredient; wheat or gluten wording may indicate an allergen for some people."}
    if any(token in lowered for token in ("preservative", "sorbate", "benzoate", "nitrite")):
        return {"category": "Preservative", "purpose": "Helps maintain shelf life", "assessment": "additive", "reason": "A functional additive is declared; this is not a finding of harm."}
    if any(token in lowered for token in ("colour", "color", "caramel")):
        return {"category": "Food colour", "purpose": "Adds or restores colour", "assessment": "additive", "reason": "A colouring ingredient is declared for product appearance."}
    if any(token in lowered for token in ("flavour", "flavor")):
        return {"category": "Flavouring", "purpose": "Adds flavour", "assessment": "additive", "reason": "A flavouring ingredient is declared; the exact composition may require manufacturer information."}
    if any(token in lowered for token in ("emulsifier", "lecithin")):
        return {"category": "Emulsifier", "purpose": "Helps ingredients stay blended", "assessment": "additive", "reason": "A functional emulsifier is declared; this is not a finding of harm."}
    if any(token in lowered for token in ("stabilizer", "thickener", "gum", "pectin")):
        return {"category": "Stabilizer/thickener", "purpose": "Controls texture or consistency", "assessment": "additive", "reason": "A functional texture ingredient is declared; this is not a finding of harm."}
    if any(token in lowered for token in ("acid", "citrate", "phosphate", "bicarbonate", "raising")):
        return {"category": "Acidity regulator/raising agent", "purpose": "Controls acidity or helps the product rise", "assessment": "additive", "reason": "A functional ingredient is declared; this is not a finding of harm."}
    if any(token in lowered for token in ("vitamin", "mineral", "iron", "calcium", "zinc")):
        return {"category": "Vitamin/mineral", "purpose": "Adds a declared micronutrient", "assessment": "common", "reason": "A micronutrient is declared; the amount should be checked against the nutrition panel."}
    return {"category": "Other", "purpose": "Function not confidently identified", "assessment": "insufficient_information", "reason": "Information insufficient for a reliable assessment."}


def parse_ingredients(text: str, ocr_confidence: float | None) -> tuple[list[dict[str, Any]], str, float]:
    sections = detect_sections(text)
    raw = sections["ingredient_text"]
    tokens = _ingredient_tokens(raw)
    confidence = round((ocr_confidence or 0.5) * 0.9, 3) if tokens else 0.0
    ingredients = []
    for token in tokens:
        result = classify_ingredient(token)
        ingredients.append({"name": token, **result, "confidence": confidence})
    return ingredients, raw or "Not detected", confidence


def detect_allergens(text: str, ingredients: list[dict[str, Any]], ocr_confidence: float | None) -> list[dict[str, Any]]:
    sections = detect_sections(text)
    evidence = f"{sections['allergen_text']} {sections['ingredient_text']}".lower()
    found = []
    for token, display in ALLERGENS.items():
        if re.search(rf"\b{re.escape(token)}\b", evidence) and not any(item["name"] == display for item in found):
            found.append({"name": display, "confidence": round((ocr_confidence or 0.5) * 0.9, 3)})
    return found


def build_insights(nutrition: dict[str, dict[str, Any]]) -> list[str]:
    insights = []
    sugar = nutrition.get("Total Sugars", {})
    sodium = nutrition.get("Sodium", {})
    sat_fat = nutrition.get("Saturated Fat", {})
    if sugar.get("value") != "Not detected":
        value = float(sugar["value"])
        if value >= 22.5:
            insights.append("High sugar based on the configurable per-100 g threshold of 22.5 g.")
        elif value <= 5:
            insights.append("Low sugar based on the configurable per-100 g threshold of 5 g.")
        else:
            insights.append("Moderate sugar based on the configurable per-100 g thresholds.")
    if sodium.get("value") != "Not detected" and float(sodium["value"]) >= 600:
        insights.append("High sodium based on the configurable per-100 g threshold of 600 mg.")
    if sat_fat.get("value") != "Not detected" and float(sat_fat["value"]) >= 5:
        insights.append("High saturated fat based on the configurable per-100 g threshold of 5 g.")
    return insights or ["Unable to determine from the available label information."]
