from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.inspection import Inspection
from app.models.nutrition_analysis import NutritionAnalysis
from app.models.ocr_result import OCRResult
from app.models.evidence import Evidence
from app.services.barcode_service import detect_barcode
from app.services.open_food_facts_service import lookup_product
from app.services.gemini_nutrition_service import GeminiNutritionService
from app.nutrition.parser import (
    build_insights,
    detect_allergens,
    detect_sections,
    parse_ingredients,
    parse_nutrition,
)
from app.schemas.nutrition import NutritionAnalysisResponse


class NutritionAnalysisService:
    def __init__(self, db: Session):
        self.db = db

    def analyze_for_inspection(self, inspection_id: str) -> NutritionAnalysisResponse:
        inspection = self.db.query(Inspection).filter(Inspection.id == inspection_id).first()
        if not inspection:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
        ocr = self.db.query(OCRResult).filter(OCRResult.inspection_id == inspection_id).first()
        if not ocr or ocr.status != "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Nutrition analysis requires completed OCR results.",
            )

        text = ocr.raw_full_text or ""
        evidence = self.db.query(Evidence).filter(
            Evidence.inspection_id == inspection_id,
            Evidence.violation_id.is_(None),
        ).first()
        barcode = detect_barcode(evidence.file_path) if evidence else None
        product_database = lookup_product(barcode)
        sections = detect_sections(text)
        nutrition, nutrition_confidence = parse_nutrition(text, ocr.average_confidence)
        ingredients, ingredient_text, ingredient_confidence = parse_ingredients(text, ocr.average_confidence)
        nlp_analysis = GeminiNutritionService().analyze_ingredients(ingredients, ingredient_text)
        nlp_by_name = {item["name"].casefold(): item for item in nlp_analysis.get("ingredients", [])}
        for ingredient in ingredients:
            enrichment = nlp_by_name.get(ingredient["name"].casefold())
            if enrichment:
                ingredient.update({
                    "category": enrichment["category"],
                    "purpose": enrichment["purpose"],
                    "assessment": enrichment["assessment"],
                    "reason": enrichment["reason"],
                    "consumer_explanation": enrichment["consumer_explanation"],
                    "nlp_source": "Gemini",
                })
        allergens = detect_allergens(text, ingredients, ocr.average_confidence)
        source_comparison = _compare_sources(nutrition, product_database.get("nutrition", {}))
        suitability = _assess_suitability(nutrition, allergens, product_database)
        warnings = []
        if not sections["nutrition_detected"]:
            warnings.append("Nutrition information could not be reliably detected from this image. Please upload a clearer image of the nutrition label.")
        if not sections["ingredients_detected"]:
            warnings.append("Ingredient information could not be reliably detected from this image.")
        if min(nutrition_confidence, ingredient_confidence or 0) < 0.6:
            warnings.append("Please verify this information against the original package.")
        if product_database.get("status") in {"NOT_DETECTED", "NOT_FOUND", "UNAVAILABLE", "INVALID"}:
            warnings.append(product_database["message"])
        if source_comparison:
            warnings.append("The label and product database contain differences. The uploaded label remains the primary source.")

        result = self.db.query(NutritionAnalysis).filter(NutritionAnalysis.inspection_id == inspection_id).first()
        if not result:
            result = NutritionAnalysis(inspection_id=inspection_id)
            self.db.add(result)
        result.ocr_result_id = ocr.id
        result.status = "COMPLETED"
        result.nutrition_confidence = nutrition_confidence
        result.ingredient_confidence = ingredient_confidence
        result.source_text = text
        result.ingredient_text = ingredient_text
        result.nutrition = nutrition
        result.ingredients = ingredients
        result.allergens = allergens
        result.insights = build_insights(nutrition)
        result.sections = sections
        result.warnings = warnings
        result.barcode = barcode
        result.product_database = product_database
        result.source_comparison = source_comparison
        result.suitability = suitability
        result.nlp_analysis = nlp_analysis
        result.error_message = None
        self.db.commit()
        self.db.refresh(result)
        return NutritionAnalysisResponse.from_orm_model(result)

    def get_for_inspection(self, inspection_id: str) -> NutritionAnalysisResponse:
        result = self.db.query(NutritionAnalysis).filter(NutritionAnalysis.inspection_id == inspection_id).first()
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nutrition analysis not found")
        return NutritionAnalysisResponse.from_orm_model(result)


def _number(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _compare_sources(ocr: dict[str, dict[str, Any]], database: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    differences = []
    for nutrient, db_value in database.items():
        ocr_value = ocr.get(nutrient, {})
        left = _number(ocr_value.get("value"))
        right = _number(db_value.get("value"))
        if left is not None and right is not None and abs(left - right) > 0.01:
            differences.append({"field": nutrient, "label_value": ocr_value, "database_value": db_value})
    return differences


def _assess_suitability(nutrition: dict[str, dict[str, Any]], allergens: list[dict[str, Any]], database: dict[str, Any]) -> dict[str, Any]:
    if not nutrition and not database.get("nutrition"):
        return {"status": "INSUFFICIENT_INFORMATION", "reason": "Insufficient nutrition information was detected."}
    sugar = _number(nutrition.get("Total Sugars", {}).get("value"))
    sodium = _number(nutrition.get("Sodium", {}).get("value"))
    if allergens:
        return {"status": "ATTENTION_REQUIRED", "reason": "Declared allergens may be unsuitable for people with the relevant allergy."}
    if (sugar is not None and sugar >= 22.5) or (sodium is not None and sodium >= 600):
        return {"status": "CONSUME_IN_MODERATION", "reason": "The label values meet configurable high sugar or sodium thresholds."}
    return {"status": "BETTER_CHOICE", "reason": "No configured high sugar or sodium signal was detected; this is not a universal safety claim."}
