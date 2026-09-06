from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.inspection import Inspection
from app.models.nutrition_analysis import NutritionAnalysis
from app.models.ocr_result import OCRResult
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
        sections = detect_sections(text)
        nutrition, nutrition_confidence = parse_nutrition(text, ocr.average_confidence)
        ingredients, ingredient_text, ingredient_confidence = parse_ingredients(text, ocr.average_confidence)
        allergens = detect_allergens(text, ingredients, ocr.average_confidence)
        warnings = []
        if not sections["nutrition_detected"]:
            warnings.append("Nutrition information could not be reliably detected from this image. Please upload a clearer image of the nutrition label.")
        if not sections["ingredients_detected"]:
            warnings.append("Ingredient information could not be reliably detected from this image.")
        if min(nutrition_confidence, ingredient_confidence or 0) < 0.6:
            warnings.append("Please verify this information against the original package.")

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
        result.error_message = None
        self.db.commit()
        self.db.refresh(result)
        return NutritionAnalysisResponse.from_orm_model(result)

    def get_for_inspection(self, inspection_id: str) -> NutritionAnalysisResponse:
        result = self.db.query(NutritionAnalysis).filter(NutritionAnalysis.inspection_id == inspection_id).first()
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nutrition analysis not found")
        return NutritionAnalysisResponse.from_orm_model(result)
