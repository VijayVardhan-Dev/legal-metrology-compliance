import json
import logging
import re
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiNutritionService:
    """Optional ingredient explanation layer; it cannot create nutrition values."""

    def analyze_ingredients(self, ingredients: list[dict[str, Any]], raw_text: str) -> dict[str, Any]:
        if not settings.GEMINI_API_KEY:
            return {"status": "NOT_CONFIGURED", "provider": "Gemini", "ingredients": []}
        if not ingredients:
            return {"status": "NO_INGREDIENTS", "provider": "Gemini", "ingredients": []}

        names = [item["name"] for item in ingredients]
        prompt = (
            "You are an ingredient education assistant. Return JSON only. "
            "Explain only the exact ingredient names in the allowed list. Never add ingredients, "
            "nutrition values, medical diagnoses, or claims that an ingredient is universally safe or harmful. "
            "For each allowed ingredient return name, category, purpose, consumer_explanation, "
            "assessment (common, moderation, allergen, additive, or insufficient_information), and reason. "
            f"Allowed ingredient names: {json.dumps(names)}. OCR source: {raw_text[:4000]}"
        )
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent"
        )
        try:
            response = httpx.post(
                url,
                params={"key": settings.GEMINI_API_KEY},
                json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}},
                headers={"Content-Type": "application/json"},
                timeout=httpx.Timeout(12.0, connect=4.0),
            )
            response.raise_for_status()
            payload = response.json()
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            parsed = _parse_json(text)
            enriched = _validate_ingredients(parsed, names)
            return {"status": "COMPLETED", "provider": "Gemini", "model": settings.GEMINI_MODEL, "ingredients": enriched}
        except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError) as exc:
            logger.warning("Gemini nutrition enrichment unavailable: %s", exc)
            return {"status": "UNAVAILABLE", "provider": "Gemini", "ingredients": [], "message": "Gemini ingredient explanations are unavailable; deterministic explanations are shown."}


def _parse_json(text: str) -> Any:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    return json.loads(cleaned)


def _validate_ingredients(payload: Any, allowed_names: list[str]) -> list[dict[str, Any]]:
    rows = payload.get("ingredients", []) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return []
    allowed = {name.casefold(): name for name in allowed_names}
    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = allowed.get(str(row.get("name", "")).casefold())
        if not name:
            continue
        result.append({
            "name": name,
            "category": str(row.get("category") or "Other"),
            "purpose": str(row.get("purpose") or "Function not confidently identified"),
            "consumer_explanation": str(row.get("consumer_explanation") or "Information insufficient for a reliable assessment."),
            "assessment": str(row.get("assessment") or "insufficient_information"),
            "reason": str(row.get("reason") or "Information insufficient for a reliable assessment."),
        })
    return result
