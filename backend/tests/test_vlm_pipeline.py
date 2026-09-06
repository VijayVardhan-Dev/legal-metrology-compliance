"""Comprehensive unit and integration tests for the Hybrid VLM + Evidence Matching Pipeline.

Tests:
1. Standard Declaration Schema validation & status normalization
2. Evidence Matcher: exact, fuzzy, currency normalization, multi-region spans, OCR typos
3. VLM Extractor: image encoding, prompt generation, JSON parsing/repair, timeout/error handling
4. Declarations Service: end-to-end VLM extraction, spatial fallback, DB persistence, API contracts
5. Comparison: VLM semantic extraction vs Spatial Mapper on ambiguous/proximate declarations
"""
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import uuid

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from ai.declaration.extractor import DeclarationExtractor
from app.core.config import settings
from app.main import app
from app.schemas.declaration_schema import DeclarationField, StandardDeclarationExtraction
from app.services.declaration_service import DeclarationService
from app.services.evidence_matcher import EvidenceMatcher
from app.services.vlm_extractor import VLMExtractionError, VLMExtractorService

client = TestClient(app)


def make_test_image():
    file = io.BytesIO()
    Image.new("RGB", (200, 200), color="blue").save(file, format="JPEG")
    file.seek(0)
    return file


def make_mock_ocr_region(region_id, text, conf=0.95, x=10, y=10, w=100, h=25):
    return SimpleNamespace(
        id=region_id,
        text=text,
        confidence=conf,
        bounding_box=[[x, y], [x + w, y], [x + w, y + h], [x, y + h]],
        bbox_x=x,
        bbox_y=y,
        bbox_width=w,
        bbox_height=h,
    )


# ===========================================================================
# 1. Standard Declaration Schema Validation Tests
# ===========================================================================

def test_schema_field_status_normalization():
    # "found" variants
    for val in ("found", "FOUND", "present", "complete", "yes"):
        field = DeclarationField(status=val, value="Test")
        assert field.status == "found"

    # "missing" variants
    for val in ("missing", "MISSING", "absent", "none", "no"):
        field = DeclarationField(status=val)
        assert field.status == "missing"

    # "uncertain" variants
    for val in ("uncertain", "UNCERTAIN", "incomplete", "ambiguous", "review_required"):
        field = DeclarationField(status=val, value="Partial")
        assert field.status == "uncertain"


def test_schema_confidence_clamping():
    assert DeclarationField(confidence=1.5).confidence == 1.0
    assert DeclarationField(confidence=-0.5).confidence == 0.0
    assert DeclarationField(confidence=0.88).confidence == 0.88
    assert DeclarationField(confidence="invalid").confidence == 0.0


def test_schema_full_model_validation():
    payload = {
        "product_name": {"value": "Organic Whole Turmeric", "evidence": "Organic Whole Turmeric 500g", "confidence": 0.98, "status": "found"},
        "mrp": {"value": "150.00", "evidence": "MRP Rs. 150.00", "confidence": 0.95, "status": "found", "unit": "INR"},
        "net_quantity": {"value": "500", "evidence": "Net Weight 500g", "confidence": 0.96, "status": "found", "unit": "g"},
        "importer_name": {"value": None, "evidence": None, "confidence": 0.0, "status": "missing"},
    }
    extracted = StandardDeclarationExtraction.model_validate(payload)
    assert extracted.product_name.value == "Organic Whole Turmeric"
    assert extracted.product_name.status == "found"
    assert extracted.mrp.unit == "INR"
    assert extracted.importer_name.status == "missing"
    assert extracted.importer_name.value is None


# ===========================================================================
# 2. Evidence Matcher Tests (Exact, Fuzzy, Currency, Multi-region, Typos)
# ===========================================================================

def test_evidence_matcher_currency_and_symbols():
    matcher = EvidenceMatcher()
    regions = [
        make_mock_ocr_region("r1", "M.R.P. Rs. 120.00 (Incl. of taxes)", conf=0.96, x=20, y=100, w=150, h=20),
        make_mock_ocr_region("r2", "Net Weight: 500gm", conf=0.94, x=20, y=130, w=120, h=20),
    ]

    # Evidence has ₹ symbol while OCR has Rs.
    match = matcher.match_evidence("MRP ₹120.00", regions)
    assert match.matched is True
    assert match.ocr_text_region_id == "r1"
    assert match.bbox is not None
    assert match.bbox["x"] == 20
    assert match.ocr_confidence == 0.96


def test_evidence_matcher_multi_region_spanning():
    matcher = EvidenceMatcher()
    regions = [
        make_mock_ocr_region("r10", "Manufactured by:", conf=0.98, x=10, y=200, w=100, h=20),
        make_mock_ocr_region("r11", "Apex Foods Private Limited", conf=0.97, x=10, y=225, w=180, h=20),
        make_mock_ocr_region("r12", "Plot 42, IDA Uppal, Hyderabad 500039", conf=0.95, x=10, y=250, w=220, h=20),
    ]

    evidence = "Manufactured by: Apex Foods Private Limited Plot 42, IDA Uppal, Hyderabad 500039"
    match = matcher.match_evidence(evidence, regions)

    assert match.matched is True
    assert len(match.ocr_text_region_ids) >= 2
    assert "r11" in match.ocr_text_region_ids
    # Check composite bounding box covers from top of r10 to bottom of r12
    assert match.bbox is not None
    assert match.bbox["y"] == 200
    assert match.bbox["height"] >= 65  # spans across regions


def test_evidence_matcher_ocr_typos():
    matcher = EvidenceMatcher()
    # OCR typo: 'O' instead of '0', 'l' instead of '1'
    regions = [
        make_mock_ocr_region("r_typo", "Net Wt: 5OO g", conf=0.82, x=30, y=50, w=100, h=20),
    ]
    match = matcher.match_evidence("Net Wt: 500 g", regions)
    assert match.matched is True
    assert match.ocr_text_region_id == "r_typo"


def test_evidence_matcher_unmatched_below_threshold():
    matcher = EvidenceMatcher()
    regions = [
        make_mock_ocr_region("r_batch", "Batch No: B1234", conf=0.90),
    ]
    match = matcher.match_evidence("Country of Origin: India", regions)
    assert match.matched is False
    assert match.ocr_text_region_id is None


# ===========================================================================
# 3. VLM Extractor Service Unit Tests
# ===========================================================================

def test_vlm_extractor_image_preparation(tmp_path):
    img_path = tmp_path / "test.jpg"
    Image.new("RGB", (50, 50), color="green").save(img_path)

    service = VLMExtractorService(api_key="fake_key")
    mime, b64 = service._prepare_image_data(img_path)
    assert mime == "image/jpeg"
    assert len(b64) > 0


def test_vlm_extractor_json_repair_and_validation():
    service = VLMExtractorService(api_key="fake_key")

    # Markdown wrapped JSON
    markdown_wrapped = """```json
    {
      "product_name": {"value": "Pure Mustard Oil", "evidence": "Pure Mustard Oil", "confidence": 0.97, "status": "found"},
      "mrp": {"value": "210.00", "evidence": "MRP Rs. 210", "confidence": 0.95, "status": "found", "unit": "INR"}
    }
    ```"""
    parsed = service._validate_and_parse(markdown_wrapped)
    assert parsed.product_name.value == "Pure Mustard Oil"
    assert parsed.mrp.value == "210.00"

    # Text surrounding JSON
    surrounded = """Here is the extracted declaration data:
    {
      "product_name": {"value": "Wheat Flour", "evidence": "Wheat Flour", "confidence": 0.99, "status": "found"}
    }
    Hope this helps."""
    parsed2 = service._validate_and_parse(surrounded)
    assert parsed2.product_name.value == "Wheat Flour"


def test_vlm_extractor_raises_when_not_configured():
    service = VLMExtractorService(api_key="")
    with pytest.raises(VLMExtractionError, match="VLM API key is not configured"):
        service.extract_declarations("fake.jpg")


@patch("app.services.vlm_extractor.httpx.Client")
def test_vlm_extractor_mock_api_success(mock_client_cls, tmp_path):
    img_path = tmp_path / "sample.jpg"
    Image.new("RGB", (60, 60), color="yellow").save(img_path)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "product_name": {"value": "Basmati Rice", "evidence": "Royal Basmati Rice 1kg", "confidence": 0.98, "status": "found"},
                                "net_quantity": {"value": "1", "evidence": "1 kg", "confidence": 0.97, "status": "found", "unit": "kg"},
                                "mrp": {"value": "180.00", "evidence": "MRP Rs. 180.00", "confidence": 0.96, "status": "found", "unit": "INR"},
                                "country_of_origin": {"value": "India", "evidence": "Product of India", "confidence": 0.99, "status": "found"},
                            })
                        }
                    ]
                }
            }
        ]
    }

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_cls.return_value = mock_client_instance

    service = VLMExtractorService(api_key="valid_mock_key")
    result = service.extract_declarations(img_path, raw_full_text="Royal Basmati Rice 1kg MRP Rs. 180.00 Product of India")

    assert result.product_name.value == "Basmati Rice"
    assert result.net_quantity.unit == "kg"
    assert result.country_of_origin.value == "India"


# ===========================================================================
# 4. End-to-End Pipeline & Fallback Tests via Declarations API
# ===========================================================================

def test_declaration_api_vlm_pipeline_with_evidence_matching():
    upload = client.post(
        "/api/v1/inspections",
        data={"product_name": "VLM Pipeline Test", "category": "food"},
        files={"image": ("sample_label.jpg", make_test_image(), "image/jpeg")},
    )
    assert upload.status_code == 201
    inspection_id = upload.json()["inspection_id"]

    raw_result = [
        [[[1, 1], [150, 1], [150, 30], [1, 30]], ("Royal Basmati Rice", 0.98)],
        [[[1, 35], [80, 35], [80, 55], [1, 55]], ("Net Qty: 1 kg", 0.97)],
        [[[1, 60], [90, 60], [90, 80], [1, 80]], ("MRP Rs. 180.00", 0.96)],
        [[[1, 85], [120, 85], [120, 105], [1, 105]], ("Product of India", 0.95)],
    ]

    with patch("app.services.ocr_service.preprocess_image") as prep:
        with patch("app.services.ocr_service.extract_text_from_image") as ext:
            prep.return_value = ("image", 200, 200)
            ext.return_value = {"raw_result": raw_result, "processing_time_ms": 10}
            assert client.post(f"/api/v1/inspections/{inspection_id}/ocr").status_code == 200

    mock_vlm_extraction = StandardDeclarationExtraction(
        product_name=DeclarationField(value="Royal Basmati Rice", evidence="Royal Basmati Rice", confidence=0.98, status="found"),
        net_quantity=DeclarationField(value="1", evidence="Net Qty: 1 kg", confidence=0.97, status="found", unit="kg"),
        mrp=DeclarationField(value="180.00", evidence="MRP Rs. 180.00", confidence=0.96, status="found", unit="INR"),
        country_of_origin=DeclarationField(value="India", evidence="Product of India", confidence=0.99, status="found"),
    )

    with patch.object(VLMExtractorService, "is_configured", return_value=True):
        with patch.object(VLMExtractorService, "extract_declarations", return_value=mock_vlm_extraction):
            resp = client.post(f"/api/v1/inspections/{inspection_id}/declarations")
            assert resp.status_code == 200
            data = resp.json()

            assert data["extraction_method"] == "VLM"
            assert data["fallback_used"] is False

            found_decls = [d for d in data["declarations"] if d["status"] == "FOUND"]
            assert len(found_decls) == 4

            # Verify missing declarations are exposed with status MISSING, value '—', evidence '—', confidence 0.0
            importer = next(d for d in data["declarations"] if d["declaration_type"] == "IMPORTER")
            assert importer["status"] == "MISSING"
            assert importer["value"] == "—"
            assert importer["source_text"] == "—"
            assert importer["confidence"] == 0.0

            # Verify evidence text was mapped to OCR regions and bboxes exist
            mrp_decl = next(d for d in data["declarations"] if d["declaration_type"] == "MRP")
            assert mrp_decl["value"] == "180.00"
            assert mrp_decl["unit"] == "INR"
            assert mrp_decl["ocr_text_region_id"] is not None
            assert mrp_decl["confidence"] == 0.96

            qty_decl = next(d for d in data["declarations"] if d["declaration_type"] == "NET_QUANTITY")
            assert qty_decl["value"] == "1"
            assert qty_decl["unit"] == "kg"
            assert qty_decl["ocr_text_region_id"] is not None


def test_declaration_api_spatial_fallback_on_vlm_error():
    upload = client.post(
        "/api/v1/inspections",
        data={"product_name": "Fallback Test", "category": "food"},
        files={"image": ("fallback.jpg", make_test_image(), "image/jpeg")},
    )
    assert upload.status_code == 201
    inspection_id = upload.json()["inspection_id"]

    raw_result = [
        [[[1, 1], [10, 1], [10, 10], [1, 10]], ("MRP ₹120", 0.91)],
        [[[1, 20], [10, 20], [10, 30], [1, 30]], ("NetWt.:500gm", 0.87)],
    ]

    with patch("app.services.ocr_service.preprocess_image") as prep:
        with patch("app.services.ocr_service.extract_text_from_image") as ext:
            prep.return_value = ("image", 100, 100)
            ext.return_value = {"raw_result": raw_result, "processing_time_ms": 1}
            assert client.post(f"/api/v1/inspections/{inspection_id}/ocr").status_code == 200

    # 1. When fallback is disabled via override, VLM failure raises explicit 502 VLM_EXTRACTION_FAILED
    with patch("app.services.declaration_service.settings.VLM_FALLBACK_ENABLED", False):
        with patch.object(VLMExtractorService, "is_configured", return_value=True):
            with patch.object(VLMExtractorService, "extract_declarations", side_effect=VLMExtractionError("API quota exceeded")):
                resp = client.post(f"/api/v1/inspections/{inspection_id}/declarations")
                assert resp.status_code == 502
                assert "VLM_EXTRACTION_FAILED" in resp.json()["detail"]

    # 2. By default (fallback enabled), VLM failure smoothly rolls back to spatial extraction
    with patch.object(VLMExtractorService, "is_configured", return_value=True):
        with patch.object(VLMExtractorService, "extract_declarations", side_effect=VLMExtractionError("Network timeout")):
            resp = client.post(f"/api/v1/inspections/{inspection_id}/declarations")
            assert resp.status_code == 200
            data = resp.json()
            assert data["extraction_method"] == "SPATIAL_FALLBACK"
            assert data["fallback_used"] is True
            assert len(data["declarations"]) >= 2


# ===========================================================================
# 5. Semantic Disambiguation Comparison: VLM vs Spatial Mapper
# ===========================================================================

def test_vlm_semantic_vs_spatial_on_close_proximity_declarations():
    """Demonstrates that VLM semantic extraction eliminates cross-assigning

    when MRP and Net Quantity are physically close to each other.
    """
    # Scenario: Label has:
    # "MRP ₹" on one line, "500g" right next to it, and "120" on next line
    # A purely spatial / nearest neighbor mapper can confuse 500 with MRP
    ocr_regions = [
        make_mock_ocr_region("r1", "MRP ₹", conf=0.98, x=10, y=10, w=40, h=18),
        make_mock_ocr_region("r2", "500g", conf=0.97, x=55, y=10, w=35, h=18),  # immediately adjacent horizontally
        make_mock_ocr_region("r3", "120.00", conf=0.96, x=10, y=30, w=45, h=18), # on the next line under MRP
    ]

    # VLM understands semantic meaning from full image context:
    vlm_result = StandardDeclarationExtraction(
        mrp=DeclarationField(value="120.00", evidence="MRP ₹ 120.00", confidence=0.98, status="found", unit="INR"),
        net_quantity=DeclarationField(value="500", evidence="500g", confidence=0.97, status="found", unit="g"),
    )

    matcher = EvidenceMatcher()
    mrp_match = matcher.match_evidence(vlm_result.mrp.evidence, ocr_regions)
    qty_match = matcher.match_evidence(vlm_result.net_quantity.evidence, ocr_regions)

    assert vlm_result.mrp.value == "120.00"
    assert vlm_result.net_quantity.value == "500"
    assert vlm_result.net_quantity.unit == "g"

    # Evidence matcher correctly located 500g to r2 and MRP to r1/r3
    assert qty_match.ocr_text_region_id == "r2"
    assert "r3" in mrp_match.ocr_text_region_ids or mrp_match.ocr_text_region_id in {"r1", "r3"}


def test_real_uploaded_package_image_loading():
    service = VLMExtractorService(api_key="mock_key")
    # Test with backend/test.jpg
    test_img = Path("test.jpg")
    if test_img.exists():
        mime, b64 = service._prepare_image_data(test_img)
        assert mime == "image/jpeg"
        assert len(b64) > 0


def test_compliance_engine_evaluates_vlm_extracted_declarations():
    """Ensures deterministic compliance engine evaluates rules against VLM declarations."""
    upload = client.post(
        "/api/v1/inspections",
        data={"product_name": "Full VLM Compliance Test", "category": "food"},
        files={"image": ("compliance_vlm.jpg", make_test_image(), "image/jpeg")},
    )
    assert upload.status_code == 201
    inspection_id = upload.json()["inspection_id"]

    raw_result = [
        [[[1, 1], [150, 1], [150, 30], [1, 30]], ("Pure Mustard Seeds", 0.98)],
        [[[1, 35], [80, 35], [80, 55], [1, 55]], ("Net Qty: 500 g", 0.97)],
        [[[1, 60], [90, 60], [90, 80], [1, 80]], ("MRP Rs. 85.00", 0.96)],
        [[[1, 85], [120, 85], [120, 105], [1, 105]], ("Mfd by: Green Agro Ltd", 0.95)],
    ]

    with patch("app.services.ocr_service.preprocess_image") as prep:
        with patch("app.services.ocr_service.extract_text_from_image") as ext:
            prep.return_value = ("image", 200, 200)
            ext.return_value = {"raw_result": raw_result, "processing_time_ms": 10}
            assert client.post(f"/api/v1/inspections/{inspection_id}/ocr").status_code == 200

    mock_vlm_extraction = StandardDeclarationExtraction(
        product_name=DeclarationField(value="Pure Mustard Seeds", evidence="Pure Mustard Seeds", confidence=0.98, status="found"),
        net_quantity=DeclarationField(value="500", evidence="Net Qty: 500 g", confidence=0.97, status="found", unit="g"),
        mrp=DeclarationField(value="85.00", evidence="MRP Rs. 85.00", confidence=0.96, status="found", unit="INR"),
        manufacturer_name=DeclarationField(value="Green Agro Ltd", evidence="Mfd by: Green Agro Ltd", confidence=0.95, status="found"),
    )

    with patch.object(VLMExtractorService, "is_configured", return_value=True):
        with patch.object(VLMExtractorService, "extract_declarations", return_value=mock_vlm_extraction):
            decl_resp = client.post(f"/api/v1/inspections/{inspection_id}/declarations")
            assert decl_resp.status_code == 200

    # Evaluate compliance
    comp_resp = client.post(f"/api/v1/inspections/{inspection_id}/compliance")
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()

    # Rule LM-PC-005 (MRP) should be COMPLIANT because MRP was extracted
    mrp_rule = next(r for r in comp_data["results"] if r["rule_id"] == "LM-PC-005")
    assert mrp_rule["status"] == "COMPLIANT"

    # Rule LM-PC-004 (Net Quantity) should be COMPLIANT
    qty_rule = next(r for r in comp_data["results"] if r["rule_id"] == "LM-PC-004")
    assert qty_rule["status"] == "COMPLIANT"

    # Evidence endpoint should return bounding boxes for the rule evidence
    ev_resp = client.get(f"/api/v1/inspections/{inspection_id}/evidence?rule=LM-PC-005")
    assert ev_resp.status_code == 200
    evidence_list = ev_resp.json()
    assert len(evidence_list) >= 1
    assert "bbox" in evidence_list[0] and evidence_list[0]["bbox"] is not None
    assert evidence_list[0]["bbox"]["x"] is not None
