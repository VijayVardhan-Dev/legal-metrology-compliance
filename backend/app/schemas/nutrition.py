from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class NutritionAnalysisResponse(BaseModel):
    id: str
    inspection_id: str
    ocr_result_id: str | None = None
    status: str
    nutrition_confidence: float | None = None
    ingredient_confidence: float | None = None
    source_text: str | None = None
    ingredient_text: str | None = None
    nutrition: dict[str, dict[str, Any]] = {}
    ingredients: list[dict[str, Any]] = []
    allergens: list[dict[str, Any]] = []
    insights: list[str] = []
    sections: dict[str, Any] = {}
    warnings: list[str] = []
    barcode: str | None = None
    product_database: dict[str, Any] = {}
    source_comparison: list[dict[str, Any]] = []
    suitability: dict[str, Any] = {}
    nlp_analysis: dict[str, Any] = {}
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, obj: Any) -> "NutritionAnalysisResponse":
        return cls(
            id=obj.id,
            inspection_id=obj.inspection_id,
            ocr_result_id=obj.ocr_result_id,
            status=obj.status,
            nutrition_confidence=obj.nutrition_confidence,
            ingredient_confidence=obj.ingredient_confidence,
            source_text=obj.source_text,
            ingredient_text=obj.ingredient_text,
            nutrition=obj.nutrition or {},
            ingredients=obj.ingredients or [],
            allergens=obj.allergens or [],
            insights=obj.insights or [],
            sections=obj.sections or {},
            warnings=obj.warnings or [],
            barcode=obj.barcode,
            product_database=obj.product_database or {},
            source_comparison=obj.source_comparison or [],
            suitability=obj.suitability or {},
            nlp_analysis=obj.nlp_analysis or {},
            error_message=obj.error_message,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
