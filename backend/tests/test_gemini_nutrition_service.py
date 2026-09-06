from unittest.mock import Mock, patch

from app.services.gemini_nutrition_service import GeminiNutritionService


def test_gemini_is_optional_without_key(monkeypatch):
    monkeypatch.setattr("app.services.gemini_nutrition_service.settings.GEMINI_API_KEY", None)
    result = GeminiNutritionService().analyze_ingredients([{"name": "Sugar"}], "Ingredients: Sugar")
    assert result["status"] == "NOT_CONFIGURED"


def test_gemini_only_returns_allowed_ingredients(monkeypatch):
    monkeypatch.setattr("app.services.gemini_nutrition_service.settings.GEMINI_API_KEY", "test-key")
    response = Mock()
    response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": '{"ingredients": [{"name":"Sugar","category":"Sugar/sweetener","purpose":"Adds sweetness","consumer_explanation":"Added sugar contributes sweetness.","assessment":"moderation","reason":"Quantity matters."},{"name":"Invented ingredient","category":"Other"}]}' }]}}]
    }
    response.raise_for_status.return_value = None
    with patch("app.services.gemini_nutrition_service.httpx.post", return_value=response):
        result = GeminiNutritionService().analyze_ingredients([{"name": "Sugar"}], "Ingredients: Sugar")
    assert result["status"] == "COMPLETED"
    assert [item["name"] for item in result["ingredients"]] == ["Sugar"]
