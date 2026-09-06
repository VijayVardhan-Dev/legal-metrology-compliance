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

MAX_NUTRIENT_VALUES = {
    "Energy": 10000,
    "Protein": 100,
    "Total Fat": 100,
    "Saturated Fat": 100,
    "Trans Fat": 100,
    "Carbohydrates": 100,
    "Total Sugars": 100,
    "Added Sugars": 100,
    "Dietary Fibre": 100,
    "Salt": 100,
    "Sodium": 10000,
}

OCR_LABEL_ALIASES = {
    "energy": r"energy|enerqy|energv",
    "calories": r"calories|calorles",
    "protein": r"protein|pr0tein",
    "total fat": r"total\s+fat|t0tal\s+fat",
    "fat": r"fat",
    "saturated fat": r"saturated\s+fat|saturatcd\s+fat",
    "trans fat": r"trans\s+fat|trans\s+fat",
    "carbohydrate": r"carbohydrate[s]?|carbohvdrate[s]?",
    "carbohydrates": r"carbohydrate[s]?|carbohvdrate[s]?",
    "total sugars": r"total\s+sugars?|t0tal\s+sugars?",
    "sugars": r"sugars?|sugarl",
    "added sugars": r"added\s+sugars?",
    "dietary fibre": r"dietary\s+fibr(?:e|a)|dietary\s+fiber",
    "dietary fiber": r"dietary\s+fibr(?:e|a)|dietary\s+fiber",
    "fibre": r"fibr(?:e|a)",
    "fiber": r"fiber",
    "sodium": r"sodium|sodlum",
    "salt": r"salt|sait",
}

ALLERGENS = {
    "milk": "Milk", "whey": "Milk", "casein": "Milk", "lactose": "Milk",
    "wheat": "Wheat/gluten", "gluten": "Wheat/gluten", "barley": "Wheat/gluten", "rye": "Wheat/gluten",
    "soy": "Soy", "soya": "Soy", "peanut": "Peanuts", "groundnut": "Peanuts",
    "almond": "Tree nuts", "cashew": "Tree nuts", "walnut": "Tree nuts", "hazelnut": "Tree nuts",
    "sesame": "Sesame", "egg": "Egg", "fish": "Fish", "crustacean": "Crustaceans", "shellfish": "Crustaceans",
}


def _lines(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", line).strip() for line in text.replace("|", "\n").splitlines() if line.strip()]


def detect_sections(text: str) -> dict[str, Any]:
    lines = _lines(text)
    lowered = [line.lower() for line in lines]
    nutrition_indexes = [i for i, line in enumerate(lowered) if any(
        marker in line for marker in (
            "nutrition information", "nutrition facts", "nutritional information",
            "nutritional info", "nutrition info", "per 100 g", "per 100g", "per 100 ml", "per 100ml",
        )
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
    if nutrition_start is not None:
        nutrition_lines = lines[nutrition_start:nutrition_end]
    else:
        # OCR often omits the panel heading. Use the text before the ingredient
        # section only when it contains at least one recognizable nutrient label.
        ingredient_boundary = ingredient_start if ingredient_start is not None else len(lines)
        candidate_lines = lines[:ingredient_boundary]
        if ingredient_start == 0:
            inline_ingredients = re.split(r"\bingredients?\s*[:\-]?", lines[0], maxsplit=1, flags=re.I)
            candidate_lines = [inline_ingredients[0].strip()] if inline_ingredients[0].strip() else []
        candidate_text = " ".join(candidate_lines).lower()
        has_nutrient_label = any(
            re.search(rf"\b{re.escape(label)}\b", candidate_text)
            for label in KNOWN_NUTRIENTS
        )
        nutrition_lines = candidate_lines if has_nutrient_label else []
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
    label_pattern = OCR_LABEL_ALIASES.get(label, re.escape(label))
    return re.search(
        rf"\b(?:{label_pattern})\b\s*(?:\((kcal|kj|kJ|g|mg|µg|ug|ml|%)\))?\s*[:\-]?\s*(?:(?:per|for)\s+(?:100\s*(?:g|ml)|serving|package)\s*)?(?:=\s*)?(\d+(?:[.,]\d+)?)\s*(kcal|kj|kJ|g|mg|µg|ug|ml|%)?",
        text,
        re.I,
    )


def _is_plausible(label: str, value: str, unit: str) -> bool:
    try:
        numeric_value = float(value.replace(",", "."))
    except ValueError:
        return False
    maximum = MAX_NUTRIENT_VALUES.get(label)
    if maximum is None or numeric_value <= maximum:
        return numeric_value >= 0
    # Values over 100 g per 100 g are invalid for gram-based nutrients. A
    # larger sodium value can be valid when explicitly expressed in mg.
    if label == "Sodium" and unit.lower() == "mg":
        return numeric_value <= 10000
    return False


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
            unit = match.group(3) or match.group(1) or "Not detected"
            value = match.group(2).replace(",", ".")
            if not _is_plausible(label, value, unit):
                continue
            nutrition[label] = {
                "value": value,
                "unit": unit,
                "basis": _basis(source),
                "confidence": round(min(1.0, (ocr_confidence or 0.5) * 0.95), 3),
            }
            found += 1
    for label in NUTRIENT_ORDER:
        nutrition.setdefault(label, {
            "value": "Not detected", "unit": "", "basis": "Not detected", "confidence": 0.0,
        })
    # Completeness is separate from extraction confidence: a label may not
    # declare every optional nutrient, so missing rows must not lower the
    # confidence of values that were actually read.
    confidence = round((ocr_confidence or 0.5) * (0.75 + min(found / 4, 1) * 0.25), 3) if found else 0.0
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
