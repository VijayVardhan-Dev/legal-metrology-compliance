from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.declaration import Declaration
from app.models.inspection import Inspection
from app.models.rule import Rule
from app.models.rule_result import RuleResult
from app.models.product_category import ProductCategory
from app.rules.base import RuleDefinition
from app.rules.registry import MVP_RULES
from app.schemas.compliance import ComplianceResponse, RuleResultResponse


@dataclass
class Evaluation:
    rule: RuleDefinition
    status: str
    reason: str
    declarations: list[Any]


class ComplianceEngine:
    """Deterministic Phase 6 evaluator; it never calls an external model."""

    def evaluate(self, inspection, declarations):
        by_type: dict[str, list[Any]] = {}
        for declaration in declarations:
            by_type.setdefault(declaration.declaration_type, []).append(declaration)
        return [
            self._evaluate_rule(rule, inspection, by_type)
            for rule in MVP_RULES
        ]

    def _evaluate_rule(self, rule, inspection, by_type):
        if rule.rule_id == "LM-PC-001":
            applicability = self._lmpc_applicability(inspection, by_type)
            if applicability == "APPLICABLE":
                return Evaluation(
                    rule, "COMPLIANT",
                    "Retail package context was supplied; LMPC rules are applicable.",
                    [],
                )
            if applicability == "EXEMPT":
                return Evaluation(
                    rule, "COMPLIANT",
                    "Industrial/institutional package context was supplied; Rule 3 exemption applies for this evaluation.",
                    [],
                )
            return Evaluation(
                rule,
                "REVIEW_REQUIRED",
                "Package quantity/unit and industrial or institutional-use context are unavailable; Rule 3 applicability cannot be determined.",
                [],
            )

        if rule.rule_id == "LM-PC-010":
            return self._origin_rule(rule, by_type)

        if rule.rule_family == "LMPC":
            applicability = self._lmpc_applicability(inspection, by_type)
            if applicability == "UNKNOWN":
                return Evaluation(
                    rule, "REVIEW_REQUIRED",
                    "LMPC applicability cannot be determined because package quantity/unit and use context are unavailable.",
                    self._related_declarations(rule, by_type),
                )
            if applicability == "EXEMPT":
                return Evaluation(
                    rule, "COMPLIANT",
                    "This LMPC requirement was not evaluated because the supplied context is industrial/institutional and covered by the Rule 3 gateway.",
                    [],
                )

        food = self._food_status(inspection)
        if rule.rule_family == "FSSAI":
            if food is None:
                return Evaluation(
                    rule, "REVIEW_REQUIRED",
                    "The product category is not sufficient to determine whether the food-specific rule applies.",
                    [],
                )
            if food is False:
                return Evaluation(
                    rule, "COMPLIANT",
                    "The product is classified as non-food, so this food-specific rule is not applicable.",
                    [],
                )

        if rule.rule_id == "LM-PC-002":
            return self._presence_rule(
                rule, by_type, ("MANUFACTURER", "PACKER", "IMPORTER"),
                "No manufacturer, packer, or importer identity declaration was extracted.",
            )
        if rule.rule_id == "LM-PC-003":
            return self._generic_name(rule, by_type)
        if rule.rule_id == "LM-PC-004":
            return self._presence_rule(
                rule, by_type, ("NET_QUANTITY",),
                "No net quantity declaration was extracted.",
            )
        if rule.rule_id == "LM-PC-005":
            return self._presence_rule(
                rule, by_type, ("MRP",),
                "No retail sale price / MRP declaration was extracted.",
            )
        if rule.rule_id == "LM-PC-008":
            return self._presence_rule(
                rule, by_type, ("CONSUMER_CARE",),
                "Consumer-care information was not detected, but the available OCR/extraction evidence is insufficient to establish that it is absent.",
            )
        if rule.rule_id == "LM-PC-009":
            unit_sale = self._usable(by_type.get("UNIT_SALE_PRICE", []))
            quantity = self._usable(by_type.get("NET_QUANTITY", []))
            if unit_sale and quantity:
                return Evaluation(
                    rule, "REVIEW_REQUIRED",
                    "A unit-sale-price label was detected, but its legal basis and format require rule-specific verification.",
                    [*unit_sale, *quantity],
                )
            return Evaluation(
                rule, "REVIEW_REQUIRED",
                "Unit-sale-price applicability and required unit basis cannot be determined from the available package/context data.",
                quantity,
            )
        if rule.rule_id == "LM-PC-010":
            return self._origin_rule(rule, by_type)
        if rule.rule_id == "FSSAI-001":
            return self._date_rule(
                rule, by_type, ("MANUFACTURING_DATE", "PACKING_DATE"),
                "No manufacture or packaging date declaration was extracted.",
            )
        if rule.rule_id == "FSSAI-002":
            use_by = self._usable(by_type.get("USE_BY", []))
            if use_by:
                return Evaluation(rule, "COMPLIANT", "An expiry/use-by date was detected.", use_by)
            best_before = self._usable(by_type.get("BEST_BEFORE", []))
            if best_before:
                return Evaluation(
                    rule, "REVIEW_REQUIRED",
                    "BEST_BEFORE was detected, but it is not treated as equivalent to USE_BY/expiry by this engine.",
                    best_before,
                )
            if by_type.get("USE_BY"):
                return Evaluation(
                    rule, "REVIEW_REQUIRED",
                    "An expiry/use-by label was detected but its value is incomplete or unreadable.",
                    by_type["USE_BY"],
                )
            return Evaluation(rule, "NON_COMPLIANT", "No expiry/use-by date declaration was extracted.", [])
        if rule.rule_id == "FSSAI-003":
            return self._presence_rule(
                rule, by_type, ("BATCH_LOT_NUMBER",),
                "No batch, lot, or code declaration was extracted.",
            )
        return Evaluation(rule, "REVIEW_REQUIRED", "Rule evaluator is not configured.", [])

    @staticmethod
    def _food_status(inspection):
        classification = getattr(inspection, "product_category", None)
        if classification is not None:
            if classification.status != "FOUND" or classification.category == "UNKNOWN":
                return None
            return classification.category == "FOOD"
        category = (
            getattr(getattr(inspection, "product", None), "category", "") or ""
        ).lower()
        if not category or category in {"unknown", "uncategorized"}:
            return None
        if category in {"food", "foods"}:
            return True
        if category in {"cosmetics", "personal care", "electronics", "clothing"}:
            return False
        return None

    @staticmethod
    def _lmpc_applicability(inspection, by_type):
        context = (getattr(inspection, "notes", "") or "").lower()
        if any(value in context for value in ("industrial", "institutional")):
            return "EXEMPT"
        quantity = ComplianceEngine._usable(by_type.get("NET_QUANTITY", []))
        if quantity:
            return "APPLICABLE"
        if any(value in context for value in ("retail", "consumer")):
            return "APPLICABLE"
        return "UNKNOWN"

    @staticmethod
    def _usable(items):
        return [item for item in items if item.value and item.status == "FOUND"]

    @staticmethod
    def _related_declarations(rule, by_type):
        if rule.rule_id == "LM-PC-002":
            types = ("MANUFACTURER", "PACKER", "IMPORTER")
        elif rule.rule_id == "FSSAI-001":
            types = ("MANUFACTURING_DATE", "PACKING_DATE")
        else:
            types = (rule.required_declaration,) if rule.required_declaration else ()
        return [
            item for declaration_type in types
            for item in by_type.get(declaration_type, [])
        ]

    def _presence_rule(self, rule, by_type, types, missing_reason):
        matching = [
            item for declaration_type in types
            for item in by_type.get(declaration_type, [])
        ]
        usable = self._usable(matching)
        if rule.rule_id == "LM-PC-008" and usable:
            contact = [
                item for item in usable
                if "@" in (item.value or "") or any(
                    character.isdigit() for character in (item.value or "")
                )
            ]
            usable = contact[:1] or usable[:1]
        if usable:
            return Evaluation(rule, "COMPLIANT", f"{rule.requirement} was detected.", usable)
        if matching:
            return Evaluation(
                rule, "REVIEW_REQUIRED",
                f"{rule.requirement} was detected, but the value is incomplete or unreadable.",
                matching,
            )
        if rule.rule_id == "LM-PC-008":
            return Evaluation(rule, "REVIEW_REQUIRED", missing_reason, [])
        return Evaluation(rule, "NON_COMPLIANT", missing_reason, [])

    def _date_rule(self, rule, by_type, types, missing_reason):
        matching = [
            item for declaration_type in types
            for item in by_type.get(declaration_type, [])
        ]
        usable = self._usable(matching)
        if usable:
            return Evaluation(rule, "COMPLIANT", "A manufacture or packaging date was detected.", usable)
        if matching:
            return Evaluation(
                rule, "REVIEW_REQUIRED",
                "A manufacture or packaging date label was detected, but its value is incomplete or unreadable.",
                matching,
            )
        return Evaluation(rule, "NON_COMPLIANT", missing_reason, [])

    def _generic_name(self, rule, by_type):
        product = self._usable(by_type.get("PRODUCT_NAME", []))
        if not product:
            return Evaluation(
                rule, "REVIEW_REQUIRED",
                "No confident commodity-name declaration was extracted.",
                by_type.get("PRODUCT_NAME", []),
            )
        if len(product[0].value.strip().split()) < 2:
            return Evaluation(
                rule, "REVIEW_REQUIRED",
                "The extracted product text is insufficient to distinguish a generic commodity name from a brand name.",
                product,
            )
        return Evaluation(rule, "COMPLIANT", "A multi-word commodity declaration was detected.", product)

    def _origin_rule(self, rule, by_type):
        importer = self._usable(by_type.get("IMPORTER", []))
        manufacturer = self._usable(by_type.get("MANUFACTURER", []))
        packer = self._usable(by_type.get("PACKER", []))
        if importer:
            origin = self._usable(by_type.get("COUNTRY_OF_ORIGIN", []))
            if origin:
                return Evaluation(
                    rule, "COMPLIANT",
                    "The commodity is treated as imported and a country-of-origin declaration was detected.",
                    [*importer, *origin],
                )
            if by_type.get("COUNTRY_OF_ORIGIN"):
                return Evaluation(
                    rule, "REVIEW_REQUIRED",
                    "The commodity is treated as imported, but the country-of-origin value is incomplete or unreadable.",
                    [*importer, *by_type["COUNTRY_OF_ORIGIN"]],
                )
            return Evaluation(
                rule, "NON_COMPLIANT",
                "The commodity is treated as imported and no country-of-origin declaration was extracted.",
                importer,
            )
        if manufacturer or packer:
            return Evaluation(
                rule, "COMPLIANT",
                "The available identity declarations indicate domestic manufacture/packing; country of origin is not required by this rule.",
                [*manufacturer, *packer],
            )
        return Evaluation(
            rule, "REVIEW_REQUIRED",
            "Import status cannot be determined from the available declarations.",
            [],
        )


class ComplianceService:
    def __init__(self, db: Session):
        self.db = db
        self.engine = ComplianceEngine()

    def evaluate_for_inspection(self, inspection_id: str) -> ComplianceResponse:
        inspection = self.db.query(Inspection).filter(
            Inspection.id == inspection_id
        ).first()
        if not inspection:
            raise HTTPException(status_code=404, detail="Inspection not found")
        declarations = self.db.query(Declaration).filter(
            Declaration.inspection_id == inspection_id
        ).order_by(Declaration.created_at, Declaration.id).all()
        if not declarations:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Declarations have not been extracted for this inspection",
            )
        inspection.product_category = self.db.query(ProductCategory).filter(
            ProductCategory.inspection_id == inspection_id
        ).first()

        stored_rules = {
            rule.rule_id: rule
            for rule in self.db.query(Rule).filter(
                Rule.rule_id.in_([rule.rule_id for rule in MVP_RULES])
            ).all()
        }
        self.db.query(RuleResult).filter(
            RuleResult.inspection_id == inspection_id
        ).delete(synchronize_session=False)
        persisted = []
        for evaluation in self.engine.evaluate(inspection, declarations):
            stored_rule = stored_rules.get(evaluation.rule.rule_id)
            evidence = [self._evidence(item) for item in evaluation.declarations]
            persisted.append(
                RuleResult(
                    inspection_id=inspection_id,
                    rule_id=evaluation.rule.rule_id,
                    rule_definition_id=stored_rule.id if stored_rule else None,
                    status=evaluation.status,
                    severity=evaluation.rule.severity,
                    reason=evaluation.reason,
                    legal_reference=evaluation.rule.legal_reference,
                    evidence=evidence,
                    declaration_ids=[
                        item.id for item in evaluation.declarations
                        if getattr(item, "id", None)
                    ],
                )
            )
        self.db.add_all(persisted)
        overall_status = self._overall_status([item.status for item in persisted])
        inspection.status = overall_status
        self.db.commit()
        results = self.db.query(RuleResult).filter(
            RuleResult.inspection_id == inspection_id
        ).order_by(RuleResult.rule_id).all()
        return ComplianceResponse(
            inspection_id=inspection_id,
            overall_status=overall_status,
            results=[RuleResultResponse.model_validate(result) for result in results],
        )

    def get_for_inspection(self, inspection_id: str) -> ComplianceResponse:
        if not self.db.query(Inspection).filter(
            Inspection.id == inspection_id
        ).first():
            raise HTTPException(status_code=404, detail="Inspection not found")
        results = self.db.query(RuleResult).filter(
            RuleResult.inspection_id == inspection_id
        ).order_by(RuleResult.rule_id).all()
        return ComplianceResponse(
            inspection_id=inspection_id,
            overall_status=self._overall_status([item.status for item in results]),
            results=[RuleResultResponse.model_validate(result) for result in results],
        )

    @staticmethod
    def _evidence(declaration):
        return {
            "declaration_id": declaration.id,
            "declaration_type": declaration.declaration_type,
            "source_text": declaration.source_text,
            "ocr_text_region_id": declaration.ocr_text_region_id,
            "ocr_confidence": declaration.ocr_confidence,
        }

    @staticmethod
    def _overall_status(statuses):
        if "NON_COMPLIANT" in statuses:
            return "NON_COMPLIANT"
        if "REVIEW_REQUIRED" in statuses or not statuses:
            return "REVIEW_REQUIRED"
        return "COMPLIANT"
