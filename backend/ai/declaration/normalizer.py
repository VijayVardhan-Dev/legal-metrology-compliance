import re
from typing import Any


def compact_text(value: str) -> str:
    """Create a comparison form without changing the preserved OCR text."""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def normalize_label_spacing(value: str) -> str:
    """Normalize whitespace and punctuation spacing for matching and display."""
    return re.sub(r"\s+", " ", value).strip()


def normalize_unit(unit: str | None) -> str | None:
    if not unit:
        return None
    normalized = unit.lower().replace(".", "").strip()
    return {
        "gm": "g",
        "gram": "g",
        "grams": "g",
        "g": "g",
        "kg": "kg",
        "ml": "ml",
        "millilitre": "ml",
        "milliliter": "ml",
        "l": "L",
        "lt": "L",
        "ltr": "L",
        "litre": "L",
        "liter": "L",
        "litres": "L",
        "liters": "L",
    }.get(normalized, unit.strip())


def normalize_numeric(value: str | None) -> int | float | None:
    if value is None:
        return None
    cleaned = value.replace(",", "").strip()
    try:
        number = float(cleaned)
    except ValueError:
        return None
    return int(number) if number.is_integer() else number


def normalize_value(value: Any) -> str | int | float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    normalized = normalize_label_spacing(str(value))
    return normalized.strip("\"'")
