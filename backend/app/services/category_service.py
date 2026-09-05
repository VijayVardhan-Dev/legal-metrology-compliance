from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.declaration import Declaration
from app.models.inspection import Inspection
from app.models.ocr_result import OCRResult
from app.models.product_category import ProductCategory
from app.schemas.product_category import ProductCategoryResponse


FOOD_SUBCATEGORIES = {
    "spices": "SPICES",
    "mustard": "SPICES",
    "masala": "SPICES",
    "seasoning": "SPICES",
    "biscuit": "BISCUITS_BAKERY",
    "cookie": "BISCUITS_BAKERY",
    "bakery": "BISCUITS_BAKERY",
    "cereal": "CEREALS_GRAINS",
    "grain": "CEREALS_GRAINS",
    "rice": "CEREALS_GRAINS",
    "wheat": "CEREALS_GRAINS",
    "pulse": "PULSES",
    "dal": "PULSES",
    "lentil": "PULSES",
    "oil": "EDIBLE_OIL",
    "beverage": "BEVERAGE",
    "juice": "BEVERAGE",
    "drink": "BEVERAGE",
    "snack": "SNACKS",
    "chips": "SNACKS",
    "chocolate": "CONFECTIONERY",
    "candy": "CONFECTIONERY",
    "confection": "CONFECTIONERY",
}

STRONG_CATEGORY_TERMS = {
    "FOOD": {"food", "edible", "ingredient", "ingredients", "nutrition", "biscuits", "biscuit"},
    "NON_FOOD": {
        "electronic", "electronics", "detergent", "cleaner", "household",
        "device", "plastic", "container", "hardware",
    },
    "COSMETIC": {"cosmetic", "shampoo", "soap", "lotion", "cream", "makeup"},
    "DRUG": {"tablet", "capsule", "medicine", "drug", "pharma", "syrup"},
    "HOUSEHOLD": {"detergent", "cleaner", "dishwash", "toilet", "household"},
    "ELECTRONIC": {"electronic", "electronics", "charger", "battery", "adapter", "voltage"},
}


@dataclass
class CategoryResult:
    category: str
    subcategory: str | None
    confidence: float
    evidence: list[dict[str, Any]]
    source_text: str
    classification_method: str
    status: str


class ProductCategoryClassifier:
    def classify(self, inspection, declarations, ocr_result=None) -> CategoryResult:
        candidates: dict[str, float] = {}
        evidence: list[dict[str, Any]] = []
        subcategory_scores: dict[str, float] = {}

        product_names = [
            item for item in declarations
            if item.declaration_type == "PRODUCT_NAME" and item.value
        ]
        for item in product_names:
            self._score_text(
                str(item.value), 1.0, "PRODUCT_NAME", item, candidates,
                subcategory_scores, evidence,
            )

        ocr_text = self._ocr_text(ocr_result)
        if ocr_text:
            self._score_text(
                ocr_text, 0.35, "OCR_TEXT", None, candidates,
                subcategory_scores, evidence,
            )

        description = getattr(getattr(inspection, "product", None), "description", None)
        if description:
            self._score_text(
                str(description), 0.5, "PRODUCT_DESCRIPTION", None, candidates,
                subcategory_scores, evidence,
            )

        if not candidates:
            return CategoryResult(
                "UNKNOWN", None, 0.0, [], ocr_text, "RULE_BASED", "REVIEW_REQUIRED"
            )

        ranked = sorted(candidates.items(), key=lambda item: item[1], reverse=True)
        top_category, top_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        total = sum(candidates.values()) or 1.0
        confidence = min(0.99, top_score / total)
        conflict = len(ranked) > 1 and (top_score - second_score) < 0.45
        status = "FOUND" if confidence >= 0.68 and not conflict else "REVIEW_REQUIRED"
        if status != "FOUND":
            top_category = "UNKNOWN"
            subcategory = None
        else:
            subcategory = max(
                subcategory_scores,
                key=subcategory_scores.get,
                default=None,
            )
            if top_category != "FOOD":
                subcategory = None

        return CategoryResult(
            top_category,
            subcategory,
            round(confidence, 4),
            evidence,
            ocr_text,
            "RULE_BASED",
            status,
        )

    def _score_text(
        self,
        text,
        weight,
        source_type,
        declaration,
        candidates,
        subcategory_scores,
        evidence,
    ):
        normalized = " ".join(str(text).lower().replace("-", " ").split())
        tokens = set(normalized.split())
        matched = []
        for category, terms in STRONG_CATEGORY_TERMS.items():
            hits = [term for term in terms if term in tokens or term in normalized]
            if hits:
                score = weight * (1.0 + min(0.4, 0.1 * len(hits)))
                candidates[category] = candidates.get(category, 0.0) + score
                matched.extend(hits)
        for term, subcategory in FOOD_SUBCATEGORIES.items():
            if term in normalized:
                score = weight * 1.2
                candidates["FOOD"] = candidates.get("FOOD", 0.0) + score
                subcategory_scores[subcategory] = subcategory_scores.get(subcategory, 0.0) + score
                matched.append(term)
        if matched:
            evidence.append({
                "source": source_type,
                "text": str(text),
                "matched_terms": sorted(set(matched)),
                "declaration_id": getattr(declaration, "id", None),
                "ocr_text_region_id": getattr(declaration, "ocr_text_region_id", None),
            })

    @staticmethod
    def _ocr_text(ocr_result):
        if not ocr_result:
            return ""
        raw_text = getattr(ocr_result, "raw_full_text", None)
        if raw_text:
            return str(raw_text)
        return " ".join(str(region.text) for region in (getattr(ocr_result, "text_regions", None) or []))


class ProductCategoryService:
    def __init__(self, db: Session):
        self.db = db
        self.classifier = ProductCategoryClassifier()

    def classify_for_inspection(self, inspection_id: str) -> ProductCategoryResponse:
        inspection = self.db.query(Inspection).filter(Inspection.id == inspection_id).first()
        if not inspection:
            raise HTTPException(status_code=404, detail="Inspection not found")
        declarations = self.db.query(Declaration).filter(
            Declaration.inspection_id == inspection_id
        ).all()
        if not declarations:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Declarations have not been extracted for this inspection",
            )
        ocr_result = self.db.query(OCRResult).filter(
            OCRResult.inspection_id == inspection_id
        ).first()
        result = self.classifier.classify(inspection, declarations, ocr_result)
        classification = self.db.query(ProductCategory).filter(
            ProductCategory.inspection_id == inspection_id
        ).first()
        if not classification:
            classification = ProductCategory(
                inspection_id=inspection_id,
                product_id=inspection.product_id,
            )
            self.db.add(classification)
        classification.category = result.category
        classification.subcategory = result.subcategory
        classification.confidence = result.confidence
        classification.evidence = result.evidence
        classification.source_text = result.source_text
        classification.classification_method = result.classification_method
        classification.status = result.status
        self.db.commit()
        self.db.refresh(classification)
        return ProductCategoryResponse.model_validate(classification)

    def get_for_inspection(self, inspection_id: str) -> ProductCategoryResponse:
        if not self.db.query(Inspection).filter(Inspection.id == inspection_id).first():
            raise HTTPException(status_code=404, detail="Inspection not found")
        classification = self.db.query(ProductCategory).filter(
            ProductCategory.inspection_id == inspection_id
        ).first()
        if not classification:
            raise HTTPException(status_code=404, detail="Product category not classified")
        return ProductCategoryResponse.model_validate(classification)
