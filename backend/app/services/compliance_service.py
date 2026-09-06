from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.declaration import Declaration
from app.models.inspection import Inspection
from app.models.rule import Rule
from app.models.rule_result import RuleResult
from app.models.product_category import ProductCategory
from app.models.visual_analysis import VisualAnalysis
from app.models.compliance_run import ComplianceRun
from app.models.ocr_result import OCRResult
from app.models.ocr_text_region import OCRTextRegion
from app.rules.base import RuleDefinition
from app.rules.registry import MVP_RULES
from app.schemas.compliance import ComplianceResponse, RuleResultResponse


@dataclass
class Evaluation:
    rule: RuleDefinition
    status: str
    reason: str
    declarations: list[Any]
    applicability_status: str = "APPLICABLE"


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
                    "NOT_APPLICABLE",
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
                    "NOT_APPLICABLE",
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
        if rule.rule_id == "LM-PC-010":
            return self._origin_rule(rule, by_type)
        if rule.rule_id == "FSSAI-001":
            return self._date_rule(
                rule, by_type, ("MANUFACTURING_DATE", "PACKING_DATE"),
                "No manufacture or packaging date declaration was extracted.",
            )
        if rule.rule_id == "FSSAI-002":
            expiry_candidates = [
                i for decl_type in ("USE_BY", "BEST_BEFORE")
                for i in by_type.get(decl_type, [])
                if getattr(i, "status", None) != "MISSING"
            ]
            usable_expiry = self._usable(expiry_candidates)
            if usable_expiry:
                return Evaluation(
                    rule, "COMPLIANT",
                    "An expiry, use-by, or best-before date was detected.",
                    usable_expiry,
                )
            if expiry_candidates:
                return Evaluation(
                    rule, "REVIEW_REQUIRED",
                    "An expiry, use-by, or best-before date was detected, but its value is incomplete or unreadable.",
                    expiry_candidates,
                )
            return Evaluation(
                rule, "NON_COMPLIANT",
                "No expiry, use-by, or best-before date declaration was extracted.",
                [],
            )
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
        return [
            item for item in items
            if item.value and item.value != "—" and item.status == "FOUND"
        ]

    @staticmethod
    def _related_declarations(rule, by_type):
        if rule.rule_id == "LM-PC-002":
            types = ("MANUFACTURER", "PACKER", "IMPORTER")
        elif rule.rule_id == "FSSAI-001":
            types = ("MANUFACTURING_DATE", "PACKING_DATE")
        elif rule.rule_id == "FSSAI-002":
            types = ("USE_BY", "BEST_BEFORE")
        else:
            types = (rule.required_declaration,) if rule.required_declaration else ()
        return [
            item for declaration_type in types
            for item in by_type.get(declaration_type, [])
            if getattr(item, "status", None) != "MISSING"
        ]

    def _presence_rule(self, rule, by_type, types, missing_reason):
        matching = [
            item for declaration_type in types
            for item in by_type.get(declaration_type, [])
            if getattr(item, "status", None) != "MISSING"
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
            if getattr(item, "status", None) != "MISSING"
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
        product_matching = [
            i for i in by_type.get("PRODUCT_NAME", [])
            if getattr(i, "status", None) != "MISSING"
        ]
        product = self._usable(product_matching)
        if not product:
            return Evaluation(
                rule, "REVIEW_REQUIRED",
                "No confident commodity-name declaration was extracted.",
                product_matching,
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
            country_matching = [
                i for i in by_type.get("COUNTRY_OF_ORIGIN", [])
                if getattr(i, "status", None) != "MISSING"
            ]
            if country_matching:
                return Evaluation(
                    rule, "REVIEW_REQUIRED",
                    "The commodity is treated as imported, but the country-of-origin value is incomplete or unreadable.",
                    [*importer, *country_matching],
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
    RULE_ENGINE_VERSION = "phase8-v1"
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
            status_value = evaluation.status
            warnings = []
            if status_value == "NON_COMPLIANT" and not evaluation.declarations:
                status_value = "REVIEW_REQUIRED"
                warnings.append(
                    "A non-compliant result was downgraded because supporting declaration evidence was unavailable."
                )
                evaluation.reason = (
                    f"{evaluation.reason} Supporting evidence is unavailable, so this requires review."
                )
            stored_rule = stored_rules.get(evaluation.rule.rule_id)
            visual_finding_ids = self._visual_finding_ids(inspection_id, evaluation.declarations)
            evidence = [
                self._evidence(item, visual_finding_ids=visual_finding_ids)
                for item in evaluation.declarations
            ]
            confidence = self._rule_confidence(evaluation.declarations, visual_finding_ids)
            persisted.append(
                RuleResult(
                    inspection_id=inspection_id,
                    rule_id=evaluation.rule.rule_id,
                    rule_name=evaluation.rule.title,
                    rule_definition_id=stored_rule.id if stored_rule else None,
                    status=status_value,
                    severity=evaluation.rule.severity,
                    reason=evaluation.reason,
                    legal_reference=evaluation.rule.legal_reference,
                    evidence=evidence,
                    declaration_ids=[
                        item.id for item in evaluation.declarations
                        if getattr(item, "id", None)
                    ],
                    applicability_status=evaluation.applicability_status,
                    confidence=confidence,
                    ocr_region_ids=list({
                        item.ocr_text_region_id for item in evaluation.declarations
                        if getattr(item, "ocr_text_region_id", None)
                    }),
                    visual_finding_ids=visual_finding_ids,
                    warnings=warnings,
                )
            )
        self.db.add_all(persisted)
        visual = self.db.query(VisualAnalysis).filter(
            VisualAnalysis.inspection_id == inspection_id
        ).first()
        overall_status = self._overall_status([item.status for item in persisted])
        # Visual analysis is advisory: it can require human review, but must
        # never hide or downgrade an existing legal-rule non-compliance.
        if visual and visual.status == "REVIEW_REQUIRED" and overall_status == "COMPLIANT":
            overall_status = "REVIEW_REQUIRED"
        summary = self._summary(persisted, overall_status)
        ocr = self.db.query(OCRResult).filter(OCRResult.inspection_id == inspection_id).first()
        run = self.db.query(ComplianceRun).filter(
            ComplianceRun.inspection_id == inspection_id
        ).first()
        if not run:
            run = ComplianceRun(inspection_id=inspection_id)
            self.db.add(run)
        run.overall_status = overall_status
        run.total_rules = summary["total_rules"]
        run.compliant_rules = summary["compliant_rules"]
        run.non_compliant_rules = summary["non_compliant_rules"]
        run.review_required_rules = summary["review_required_rules"]
        run.applicable_rules = summary["applicable_rules"]
        run.not_applicable_rules = summary["not_applicable_rules"]
        run.overall_confidence = self._overall_confidence(persisted, visual)
        run.evaluated_at = datetime.now(timezone.utc)
        run.rule_engine_version = self.RULE_ENGINE_VERSION
        run.classification_version = getattr(inspection.product_category, "classification_method", None)
        run.ocr_result_id = getattr(ocr, "id", None)
        run.visual_analysis_id = getattr(visual, "id", None)
        inspection.status = overall_status
        self.db.commit()
        results = self.db.query(RuleResult).filter(
            RuleResult.inspection_id == inspection_id
        ).order_by(RuleResult.rule_id).all()
        return self._response(inspection_id, overall_status, results, run)

    def get_for_inspection(self, inspection_id: str) -> ComplianceResponse:
        if not self.db.query(Inspection).filter(
            Inspection.id == inspection_id
        ).first():
            raise HTTPException(status_code=404, detail="Inspection not found")
        results = self.db.query(RuleResult).filter(
            RuleResult.inspection_id == inspection_id
        ).order_by(RuleResult.rule_id).all()
        visual = self.db.query(VisualAnalysis).filter(
            VisualAnalysis.inspection_id == inspection_id
        ).first()
        overall_status = self._overall_status([item.status for item in results])
        if visual and visual.status == "REVIEW_REQUIRED" and overall_status == "COMPLIANT":
            overall_status = "REVIEW_REQUIRED"
        run = self.db.query(ComplianceRun).filter(
            ComplianceRun.inspection_id == inspection_id
        ).first()
        if run and run.overall_status != overall_status:
            run.overall_status = overall_status
            self.db.commit()
        return self._response(inspection_id, overall_status, results, run)

    def evidence_for_inspection(self, inspection_id, rule=None, declaration=None, evidence_type=None):
        if not self.db.query(Inspection).filter(Inspection.id == inspection_id).first():
            raise HTTPException(status_code=404, detail="Inspection not found")
        results = self.db.query(RuleResult).filter(
            RuleResult.inspection_id == inspection_id
        ).order_by(RuleResult.rule_id).all()
        if rule:
            results = [item for item in results if item.rule_id == rule]
        visual = self.db.query(VisualAnalysis).filter(
            VisualAnalysis.inspection_id == inspection_id
        ).first()
        ocr = self.db.query(OCRResult).filter(
            OCRResult.inspection_id == inspection_id
        ).first()
        image_width = getattr(ocr, "image_width", None) or getattr(visual, "image_width", None)
        image_height = getattr(ocr, "image_height", None) or getattr(visual, "image_height", None)
        declarations = {
            item.id: item
            for item in self.db.query(Declaration).filter(
                Declaration.inspection_id == inspection_id
            ).all()
        }
        output = []
        for result in results:
            for item in result.evidence or []:
                declaration_id = item.get("declaration_id")
                if declaration and declaration_id != declaration:
                    continue
                if evidence_type and evidence_type not in {"declaration", "ocr_region", "ocr", "rule"}:
                    continue
                declaration_item = declarations.get(declaration_id)
                region_ids = item.get("ocr_region_ids") or (
                    [item.get("ocr_text_region_id")] if item.get("ocr_text_region_id") else []
                )
                for region_id in region_ids:
                    region = self.db.query(OCRTextRegion).filter(
                        OCRTextRegion.id == region_id
                    ).first()
                    if not region:
                        continue
                    output.append({
                        "evidence_id": result.id,
                        "declaration_id": declaration_id,
                        "rule_id": result.rule_id,
                        "evidence_type": "ocr_region",
                        "ocr_region_id": region.id,
                        "bbox": {
                            "x": region.bbox_x, "y": region.bbox_y,
                            "width": region.bbox_width, "height": region.bbox_height,
                        },
                        "source_text": getattr(declaration_item, "source_text", None) or region.text,
                        "value": getattr(declaration_item, "value", None),
                        "confidence": result.confidence,
                        "ocr_confidence": getattr(declaration_item, "ocr_confidence", None) or region.confidence,
                        "visual_status": self._visual_status(visual, declaration_id),
                        "visual_finding_ids": result.visual_finding_ids or [],
                        "image_width": image_width,
                        "image_height": image_height,
                        "declaration_type": getattr(declaration_item, "declaration_type", None),
                        "legal_reference": result.legal_reference,
                        "reason": result.reason,
                        "warnings": result.warnings or [],
                    })
        return output

    @staticmethod
    def _visual_status(visual, declaration_id):
        if not visual:
            return None
        for item in visual.declarations or []:
            if item.get("declaration_id") == declaration_id:
                return item.get("status")
        return None

    @staticmethod
    def _evidence(declaration, visual_finding_ids=None):
        region_ids = getattr(declaration, "ocr_text_region_ids", None)
        if region_ids is None and getattr(declaration, "ocr_text_region_id", None):
            region_ids = [declaration.ocr_text_region_id]
        return {
            "declaration_id": declaration.id,
            "declaration_type": declaration.declaration_type,
            "source_text": declaration.source_text,
            "ocr_text_region_id": getattr(declaration, "ocr_text_region_id", None),
            "ocr_region_ids": region_ids or [],
            "ocr_confidence": getattr(declaration, "ocr_confidence", None),
            "value": getattr(declaration, "value", None),
            "confidence": getattr(declaration, "confidence", None),
            "visual_finding_ids": visual_finding_ids or [],
        }

    def _visual_finding_ids(self, inspection_id, declarations):
        visual = self.db.query(VisualAnalysis).filter(
            VisualAnalysis.inspection_id == inspection_id
        ).first()
        if not visual or not visual.declarations:
            return []
        declaration_ids = {item.id for item in declarations}
        return [
            f"{visual.id}:{index}"
            for index, item in enumerate(visual.declarations)
            if item.get("declaration_id") in declaration_ids and item.get("status") != "CLEAR"
        ]

    @staticmethod
    def _rule_confidence(declarations, visual_finding_ids):
        if not declarations:
            return 0.0
        values = []
        for item in declarations:
            declaration_confidence = item.confidence
            ocr_confidence = item.ocr_confidence
            if declaration_confidence is not None and ocr_confidence is not None:
                values.append(min(declaration_confidence, ocr_confidence))
            elif declaration_confidence is not None or ocr_confidence is not None:
                values.append(declaration_confidence if declaration_confidence is not None else ocr_confidence)
        confidence = min(values) if values else 0.0
        return round(confidence * (0.75 if visual_finding_ids else 1.0), 4)

    @staticmethod
    def _summary(results, overall_status):
        return {
            "total_rules": len(results),
            "compliant_rules": sum(item.status == "COMPLIANT" and item.applicability_status != "NOT_APPLICABLE" for item in results),
            "non_compliant_rules": sum(item.status == "NON_COMPLIANT" for item in results),
            "review_required_rules": sum(item.status == "REVIEW_REQUIRED" for item in results),
            "applicable_rules": sum(item.applicability_status == "APPLICABLE" for item in results),
            "not_applicable_rules": sum(item.applicability_status == "NOT_APPLICABLE" for item in results),
        }

    def _overall_confidence(self, results, visual):
        confidences = [item.confidence for item in results if item.confidence is not None]
        if not confidences:
            return 0.0
        value = sum(confidences) / len(confidences)
        if visual is None or visual.processing_status != "COMPLETED":
            value *= 0.75
        if visual and visual.status == "REVIEW_REQUIRED":
            value *= 0.75
        if any(item.status == "REVIEW_REQUIRED" for item in results):
            value *= 0.75
        return round(value, 4)

    def _response(self, inspection_id, overall_status, results, run):
        summary = self._summary(results, overall_status)
        return ComplianceResponse(
            inspection_id=inspection_id,
            overall_status=overall_status,
            **summary,
            overall_confidence=run.overall_confidence if run else self._overall_confidence(results, None),
            evaluated_at=run.evaluated_at if run else None,
            rule_engine_version=run.rule_engine_version if run else None,
            classification_version=run.classification_version if run else None,
            ocr_result_id=run.ocr_result_id if run else None,
            visual_analysis_id=run.visual_analysis_id if run else None,
            results=[RuleResultResponse.model_validate(result) for result in results],
        )

    @staticmethod
    def _overall_status(statuses):
        if "NON_COMPLIANT" in statuses:
            return "NON_COMPLIANT"
        if "REVIEW_REQUIRED" in statuses or not statuses:
            return "REVIEW_REQUIRED"
        return "COMPLIANT"
