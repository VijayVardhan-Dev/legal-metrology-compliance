from types import SimpleNamespace

from app.rules.registry import MVP_RULES
from app.services.compliance_service import ComplianceEngine, ComplianceService
from app.services.category_service import ProductCategoryClassifier


def declaration(
    declaration_type,
    value,
    status="FOUND",
    declaration_id="d1",
    region_id="r1",
):
    return SimpleNamespace(
        id=declaration_id,
        declaration_type=declaration_type,
        value=value,
        status=status,
        source_text=value or declaration_type,
        ocr_text_region_id=region_id,
        ocr_confidence=0.91,
    )


def inspection(category="food", context="retail"):
    return SimpleNamespace(
        product=SimpleNamespace(category=category),
        notes=context,
    )


def persisted_category(category, status="FOUND", subcategory=None):
    return SimpleNamespace(
        category=category,
        subcategory=subcategory,
        status=status,
    )


def results_for(declarations, category="food", context="retail"):
    return {
        item.rule.rule_id: item
        for item in ComplianceEngine().evaluate(
            inspection(category, context), declarations
        )
    }


def test_clearly_compliant_net_quantity_preserves_evidence():
    result = results_for([declaration("NET_QUANTITY", "500", "FOUND")])["LM-PC-004"]
    assert result.status == "COMPLIANT"
    assert result.declarations[0].value == "500"


def test_missing_required_mrp_is_non_compliant():
    assert results_for([])["LM-PC-005"].status == "NON_COMPLIANT"


def test_incomplete_ocr_is_review_required():
    result = results_for(
        [declaration("MRP", None, "INCOMPLETE")]
    )["LM-PC-005"]
    assert result.status == "REVIEW_REQUIRED"
    assert result.declarations[0].value is None


def test_consumer_care_present_is_compliant():
    result = results_for(
        [declaration("CONSUMER_CARE", "1800-123-456 / help@example.com")]
    )["LM-PC-008"]
    assert result.status == "COMPLIANT"
    assert result.declarations[0].value == "1800-123-456 / help@example.com"


def test_consumer_care_not_detected_is_review_required():
    result = results_for([])["LM-PC-008"]
    assert result.status == "REVIEW_REQUIRED"
    assert result.declarations == []
    assert "insufficient" in result.reason


def test_explicit_mrp_violation_remains_non_compliant():
    result = results_for([])["LM-PC-005"]
    assert result.status == "NON_COMPLIANT"


def test_unknown_applicability_is_review_required():
    assert results_for([], category="unknown")["FSSAI-001"].status == "REVIEW_REQUIRED"


def test_rule_three_is_an_applicability_gateway():
    result = results_for(
        [], context=None
    )["LM-PC-001"]
    assert result.status == "REVIEW_REQUIRED"
    assert "cannot be determined" in result.reason


def test_quantity_establishes_retail_lmpc_applicability_without_use_context():
    results = results_for(
        [
            declaration("NET_QUANTITY", "500"),
            declaration("MANUFACTURER", "Domestic Foods"),
            declaration("CONSUMER_CARE", "1800-123-456"),
        ],
        context=None,
    )
    assert results["LM-PC-001"].status == "COMPLIANT"
    assert results["LM-PC-002"].status == "COMPLIANT"
    assert results["LM-PC-004"].status == "COMPLIANT"
    assert results["LM-PC-008"].status == "COMPLIANT"
    assert results["LM-PC-005"].status == "NON_COMPLIANT"


def test_rule_three_exemption_gateway_does_not_enforce_lmpc_rules():
    results = results_for(
        [], context="industrial institutional package"
    )
    assert results["LM-PC-001"].status == "COMPLIANT"
    assert results["LM-PC-005"].status == "COMPLIANT"


def test_imported_and_domestic_origin_behavior():
    imported = results_for([declaration("IMPORTER", "Importer Ltd")])["LM-PC-010"]
    assert imported.status == "NON_COMPLIANT"

    domestic = results_for([declaration("MANUFACTURER", "Domestic Foods")])["LM-PC-010"]
    assert domestic.status == "COMPLIANT"


def test_unknown_import_status_only_affects_country_of_origin():
    results = results_for(
        [
            declaration("NET_QUANTITY", "500"),
            declaration("MANUFACTURER", "Domestic Foods"),
        ],
        context=None,
    )
    assert results["LM-PC-004"].status == "COMPLIANT"
    assert results["LM-PC-005"].status == "NON_COMPLIANT"
    assert results["LM-PC-010"].status == "COMPLIANT"


def test_unknown_food_classification_is_not_compliant_by_default():
    results = results_for(
        [declaration("NET_QUANTITY", "500")],
        category="chips",
        context=None,
    )
    assert results["FSSAI-001"].status == "REVIEW_REQUIRED"
    assert results["FSSAI-002"].status == "REVIEW_REQUIRED"
    assert results["FSSAI-003"].status == "REVIEW_REQUIRED"


def test_500_gram_quantity_and_unit_sale_price_are_separate():
    results = results_for([declaration("NET_QUANTITY", "500")])
    assert results["LM-PC-004"].status == "COMPLIANT"
    assert results["LM-PC-009"].status == "NOT_APPLICABLE"
    assert "MRP is evaluated under LM-PC-005" in results["LM-PC-009"].reason
    assert results["LM-PC-009"].declarations == []


def test_unit_sale_price_review_uses_only_unit_sale_evidence():
    results = results_for([
        declaration("NET_QUANTITY", "500"),
        declaration("UNIT_SALE_PRICE", "20 per 100g"),
    ])
    assert [item.declaration_type for item in results["LM-PC-009"].declarations] == [
        "UNIT_SALE_PRICE"
    ]


def test_best_before_is_not_treated_as_use_by():
    result = results_for([declaration("BEST_BEFORE", "12 MONTHS FROM PACKING")])["FSSAI-002"]
    assert result.status == "COMPLIANT"
    assert "accepted as the package expiry date" in result.reason


def test_overall_status_precedence():
    assert ComplianceService._overall_status(["COMPLIANT", "REVIEW_REQUIRED"]) == "REVIEW_REQUIRED"
    assert ComplianceService._overall_status(["REVIEW_REQUIRED", "NON_COMPLIANT"]) == "NON_COMPLIANT"
    assert ComplianceService._overall_status(["COMPLIANT"]) == "COMPLIANT"


def test_evidence_and_declaration_linkage():
    result = results_for(
        [declaration("NET_QUANTITY", "500", declaration_id="decl-1", region_id="region-1")]
    )["LM-PC-004"]
    assert result.declarations[0].id == "decl-1"
    assert result.declarations[0].ocr_text_region_id == "region-1"


def test_no_fabricated_values():
    result = results_for([declaration("MRP", None, "INCOMPLETE")])["LM-PC-005"]
    assert result.declarations[0].value is None
    assert result.status == "REVIEW_REQUIRED"


def test_seed_contains_all_mvp_rules():
    assert {rule.rule_id for rule in MVP_RULES} == {
        "LM-PC-001", "LM-PC-002", "LM-PC-003", "LM-PC-004",
        "LM-PC-005", "LM-PC-008", "LM-PC-009", "LM-PC-010",
        "FSSAI-001", "FSSAI-002", "FSSAI-003",
    }


def test_mustard_package_classifies_as_food_spices():
    result = ProductCategoryClassifier().classify(
        inspection("unknown", None),
        [declaration("PRODUCT_NAME", "Surya Mustard Whole")],
    )
    assert result.category == "FOOD"
    assert result.subcategory == "SPICES"
    assert result.status == "FOUND"


def test_biscuit_package_classifies_as_food_bakery():
    result = ProductCategoryClassifier().classify(
        inspection("unknown", None),
        [declaration("PRODUCT_NAME", "Parle-G Biscuits")],
    )
    assert result.category == "FOOD"
    assert result.subcategory == "BISCUITS_BAKERY"
    assert result.status == "FOUND"


def test_clearly_non_food_package_classifies_as_non_food():
    result = ProductCategoryClassifier().classify(
        inspection("unknown", None),
        [declaration("PRODUCT_NAME", "Plastic Storage Container")],
    )
    assert result.category == "NON_FOOD"
    assert result.subcategory is None
    assert result.status == "FOUND"


def test_ambiguous_product_requires_review():
    result = ProductCategoryClassifier().classify(
        inspection("unknown", None),
        [declaration("PRODUCT_NAME", "Daily Essentials")],
    )
    assert result.category == "UNKNOWN"
    assert result.status == "REVIEW_REQUIRED"


def test_conflicting_category_evidence_requires_review():
    result = ProductCategoryClassifier().classify(
        inspection("unknown", None),
        [declaration("PRODUCT_NAME", "Mustard Shampoo")],
    )
    assert result.category == "UNKNOWN"
    assert result.status == "REVIEW_REQUIRED"


def test_persisted_food_category_allows_fssai_evaluation():
    product_inspection = inspection("unknown", None)
    product_inspection.product_category = persisted_category("FOOD", subcategory="SPICES")
    results = {
        item.rule.rule_id: item
        for item in ComplianceEngine().evaluate(
            product_inspection,
            [declaration("BEST_BEFORE", "12 MONTHS FROM PACKING")],
        )
    }
    assert results["FSSAI-001"].reason != (
        "The product category is not sufficient to determine whether the food-specific rule applies."
    )
    assert results["FSSAI-002"].status == "COMPLIANT"


def test_persisted_non_food_category_makes_fssai_rules_not_applicable():
    product_inspection = inspection("unknown", None)
    product_inspection.product_category = persisted_category("NON_FOOD")
    results = {
        item.rule.rule_id: item
        for item in ComplianceEngine().evaluate(product_inspection, [])
    }
    assert results["FSSAI-001"].status == "COMPLIANT"
    assert "non-food" in results["FSSAI-001"].reason


def test_persisted_unknown_category_keeps_fssai_review_required():
    product_inspection = inspection("food", "retail")
    product_inspection.product_category = persisted_category(
        "UNKNOWN", status="REVIEW_REQUIRED"
    )
    results = {
        item.rule.rule_id: item
        for item in ComplianceEngine().evaluate(product_inspection, [])
    }
    assert results["FSSAI-001"].status == "REVIEW_REQUIRED"


def test_category_classification_failure_keeps_fssai_review_required():
    result = ProductCategoryClassifier().classify(
        inspection("unknown", None),
        [],
    )
    assert result.category == "UNKNOWN"
    assert result.status == "REVIEW_REQUIRED"


def test_phase8_rule_confidence_uses_the_lower_declaration_or_ocr_confidence():
    item = declaration("MRP", "100", declaration_id="decl-8", region_id="region-8")
    item.confidence = 0.88
    item.ocr_confidence = 0.96

    assert ComplianceService._rule_confidence([item], []) == 0.88


def test_phase8_summary_separates_applicability_counts():
    results = [
        SimpleNamespace(status="COMPLIANT", applicability_status="APPLICABLE"),
        SimpleNamespace(status="COMPLIANT", applicability_status="NOT_APPLICABLE"),
        SimpleNamespace(status="REVIEW_REQUIRED", applicability_status="APPLICABLE"),
        SimpleNamespace(status="NON_COMPLIANT", applicability_status="APPLICABLE"),
    ]

    assert ComplianceService._summary(results, "NON_COMPLIANT") == {
        "total_rules": 4,
        "compliant_rules": 1,
        "non_compliant_rules": 1,
        "review_required_rules": 1,
        "applicable_rules": 3,
        "not_applicable_rules": 1,
    }


def test_phase8_evidence_supports_multiple_ocr_regions():
    item = declaration("MRP", "100", declaration_id="decl-8", region_id="region-1")
    item.ocr_text_region_ids = ["region-1", "region-2"]

    evidence = ComplianceService._evidence(item)

    assert evidence["ocr_region_ids"] == ["region-1", "region-2"]
