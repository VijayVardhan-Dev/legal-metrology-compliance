from types import SimpleNamespace
from unittest.mock import patch
import io
import uuid

from fastapi.testclient import TestClient
from PIL import Image

from ai.declaration.extractor import DeclarationExtractor
from app.main import app


client = TestClient(app)


def regions(*texts):
    return [
        SimpleNamespace(id=str(index), text=text, confidence=0.8 + index / 100)
        for index, text in enumerate(texts)
    ]


def by_type(items, declaration_type):
    return next(item for item in items if item.declaration_type == declaration_type)


def test_mrp_formats_and_missing_value():
    extractor = DeclarationExtractor()
    for text in ("MRP ₹120", "MRP: Rs. 120", "M.R.P. ₹120.00"):
        declaration = by_type(extractor.extract_regions(regions(text)), "MRP")
        assert declaration.value == "120" or declaration.value == "120.00"
        assert declaration.normalized_value in (120, 120.0)
        assert declaration.unit == "INR"

    incomplete = by_type(extractor.extract_regions(regions("MRP:")), "MRP")
    assert incomplete.value is None
    assert incomplete.status == "INCOMPLETE"


def test_quantity_formats_and_units():
    extractor = DeclarationExtractor()
    cases = {
        "NetWt.:500gm": ("500", "g"),
        "Net Qty: 1 kg": ("1", "kg"),
        "Net Quantity 500 g": ("500", "g"),
        "500 ml": ("500", "ml"),
    }
    for text, expected in cases.items():
        declaration = by_type(extractor.extract_regions(regions(text)), "NET_QUANTITY")
        assert (declaration.value, declaration.unit) == expected


def test_manufacturer_dates_batch_and_consumer_care():
    extracted = DeclarationExtractor().extract_regions(
        regions(
            "Manufactured by ABC Pvt Ltd",
            "MFG: 08/2026",
            "PKD: 08-2026",
            "BESTBEFORE:12MONTHSFROMTHEDATEOFPACKING",
            "LOT No. A123",
            "ConsumerCare DeptPhone No.7032901785/Email:info@example.com",
        )
    )
    assert by_type(extracted, "MANUFACTURER").value == "ABC Pvt Ltd"
    assert by_type(extracted, "MANUFACTURING_DATE").value == "08/2026"
    assert by_type(extracted, "PACKING_DATE").value == "08-2026"
    assert (
        by_type(extracted, "BEST_BEFORE").value
        == "12MONTHSFROMTHEDATEOFPACKING"
    )
    assert by_type(extracted, "BATCH_LOT_NUMBER").value == "A123"
    assert (
        by_type(extracted, "CONSUMER_CARE").value
        == "7032901785 / info@example.com"
    )


def test_consumer_care_ignores_noisy_fragment():
    extracted = DeclarationExtractor().extract_regions(
        regions(
            "ConsumerCare DeptPhone No.7032901785/Email:info@example.com",
            ",queries orcomplaints-Contactrelationship officerat",
        )
    )
    consumer_care = [
        item for item in extracted if item.declaration_type == "CONSUMER_CARE"
    ]
    assert len(consumer_care) == 1
    assert consumer_care[0].value == "7032901785 / info@example.com"


def test_product_name_removes_repeated_quantity_suffix_and_normalized_quotes():
    extracted = DeclarationExtractor().extract_regions(
        regions("SURYA MUSTARD WHOLE 500gm", "NetWt.:500gm", 'BEST BEFORE: "12 MONTHS"')
    )
    product_name = by_type(extracted, "PRODUCT_NAME")
    assert product_name.value == "SURYA MUSTARD WHOLE"
    assert product_name.source_text == "SURYA MUSTARD WHOLE 500gm"
    assert '"' not in by_type(extracted, "BEST_BEFORE").normalized_value


def spatial_regions(*items):
    return [
        SimpleNamespace(
            id=str(index),
            text=text,
            confidence=confidence,
            bbox_x=x,
            bbox_y=y,
            bbox_width=width,
            bbox_height=height,
        )
        for index, (text, x, y, width, height, confidence) in enumerate(items)
    ]


def test_split_ocr_regions_are_grouped_without_cross_assigning_values():
    extracted = DeclarationExtractor().extract_regions(
        spatial_regions(
            ("Surya", 10, 10, 45, 20, 0.98),
            ("Mustard", 62, 10, 65, 20, 0.97),
            ("Whole", 134, 10, 45, 20, 0.96),
            ("Net", 10, 60, 25, 18, 0.95),
            ("Wt.", 40, 60, 25, 18, 0.94),
            ("500", 72, 60, 30, 18, 0.93),
            ("g", 108, 60, 12, 18, 0.92),
            ("MRP", 10, 110, 35, 18, 0.98),
            ("100.00", 52, 110, 48, 18, 0.97),
            ("Batch", 10, 160, 42, 18, 0.98),
            ("No.", 58, 160, 25, 18, 0.97),
            ("SMW/0924", 90, 160, 75, 18, 0.96),
            ("Mfg.", 10, 210, 35, 18, 0.98),
            ("Date", 52, 210, 35, 18, 0.97),
            ("15", 94, 210, 18, 18, 0.96),
            ("SEP", 118, 210, 30, 18, 0.95),
            ("2024", 154, 210, 42, 18, 0.94),
            ("Best", 10, 260, 35, 18, 0.98),
            ("Before", 52, 260, 50, 18, 0.97),
            ("14", 110, 260, 18, 18, 0.96),
            ("SEP", 134, 260, 30, 18, 0.95),
            ("2026", 170, 260, 42, 18, 0.94),
            ("Manufactured", 10, 320, 85, 18, 0.98),
            ("by", 102, 320, 18, 18, 0.97),
            ("M/S.", 10, 345, 35, 18, 0.96),
            ("Hyderabad", 48, 345, 75, 18, 0.95),
            ("Food", 126, 345, 35, 18, 0.94),
            ("Products", 164, 345, 60, 18, 0.93),
            ("Pvt.", 10, 370, 30, 18, 0.92),
            ("Ltd.", 44, 370, 28, 18, 0.91),
            ("Phone", 10, 430, 45, 18, 0.98),
            ("No.", 62, 430, 25, 18, 0.97),
            ("7032901785", 94, 430, 80, 18, 0.96),
            ("Email:", 10, 455, 45, 18, 0.95),
            ("info@suryamasale.com", 62, 455, 150, 18, 0.94),
            ("PRODUCT", 10, 500, 70, 18, 0.98),
            ("OF", 88, 500, 20, 18, 0.97),
            ("INDIA", 116, 500, 45, 18, 0.96),
            ("999", 500, 500, 30, 18, 0.99),
        )
    )
    assert by_type(extracted, "PRODUCT_NAME").value == "Surya Mustard Whole"
    assert by_type(extracted, "NET_QUANTITY").unit == "g"
    assert by_type(extracted, "NET_QUANTITY").value == "500"
    assert by_type(extracted, "MRP").value == "100.00"
    assert by_type(extracted, "MRP").normalized_value == "100.00"
    assert by_type(extracted, "BATCH_LOT_NUMBER").value == "SMW/0924"
    assert by_type(extracted, "MANUFACTURING_DATE").value == "15 SEP 2024"
    assert by_type(extracted, "BEST_BEFORE").value == "14 SEP 2026"
    assert by_type(extracted, "MANUFACTURER").value.startswith(
        "M/S. Hyderabad Food Products Pvt. Ltd."
    )
    assert by_type(extracted, "COUNTRY_OF_ORIGIN").value == "INDIA"
    assert by_type(extracted, "CONSUMER_CARE").value == "7032901785 / info@suryamasale.com"
    assert by_type(extracted, "MRP").ocr_text_region_ids
    assert by_type(extracted, "MRP").confidence == 0.97


def create_test_image():
    file = io.BytesIO()
    Image.new("RGB", (100, 100), color="red").save(file, format="JPEG")
    file.seek(0)
    return file


def test_declaration_api_extract_get_and_repeat():
    upload = client.post(
        "/api/v1/inspections",
        data={"product_name": "Declaration Test", "category": "food"},
        files={"image": ("declaration.jpg", create_test_image(), "image/jpeg")},
    )
    assert upload.status_code == 201
    inspection_id = upload.json()["inspection_id"]
    raw_result = [
        [[[1, 1], [10, 1], [10, 10], [1, 10]], ("MRP ₹120", 0.91)],
        [[[1, 20], [10, 20], [10, 30], [1, 30]], ("NetWt.:500gm", 0.87)],
    ]
    with patch("app.services.ocr_service.preprocess_image") as preprocess:
        with patch("app.services.ocr_service.extract_text_from_image") as extract:
            preprocess.return_value = ("image", 100, 100)
            extract.return_value = {"raw_result": raw_result, "processing_time_ms": 1}
            assert client.post(f"/api/v1/inspections/{inspection_id}/ocr").status_code == 200

    first = client.post(f"/api/v1/inspections/{inspection_id}/declarations")
    second = client.post(f"/api/v1/inspections/{inspection_id}/declarations")
    assert first.status_code == second.status_code == 200
    assert len(first.json()["declarations"]) == len(second.json()["declarations"])
    assert client.get(f"/api/v1/inspections/{inspection_id}/declarations").status_code == 200


def test_declaration_api_states():
    nonexistent = client.post(f"/api/v1/inspections/{uuid.uuid4()}/declarations")
    assert nonexistent.status_code == 404

    upload = client.post(
        "/api/v1/inspections",
        data={"product_name": "No OCR", "category": "food"},
        files={"image": ("no-ocr.jpg", create_test_image(), "image/jpeg")},
    )
    inspection_id = upload.json()["inspection_id"]
    response = client.post(f"/api/v1/inspections/{inspection_id}/declarations")
    assert response.status_code == 409
