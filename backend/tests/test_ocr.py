import pytest
import io
from PIL import Image
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def create_test_image(format="JPEG", size=(100, 100)):
    file = io.BytesIO()
    image = Image.new("RGB", size, color="red")
    image.save(file, format=format)
    file.seek(0)
    return file

def test_trigger_ocr_success():
    """
    Test the OCR processing pipeline using mocked AI engine.
    First upload an image to get an inspection, then run OCR.
    """
    # 1. Upload image to create inspection
    img = create_test_image("JPEG")
    upload_resp = client.post(
        "/api/v1/inspections",
        data={"product_name": "OCR Test Product", "category": "food", "brand": "TestBrand"},
        files={"image": ("test_product.jpg", img, "image/jpeg")}
    )
    
    assert upload_resp.status_code == 201
    inspection_id = upload_resp.json()["inspection_id"]
    
    # 2. Trigger OCR with mocked engine
    mock_ocr_result = [
        [
            [[10.0, 10.0], [100.0, 10.0], [100.0, 30.0], [10.0, 30.0]], 
            ("MRP Rs. 50.00", 0.98)
        ],
        [
            [[10.0, 40.0], [80.0, 40.0], [80.0, 60.0], [10.0, 60.0]], 
            ("Net Qty: 100g", 0.95)
        ]
    ]
    
    with patch("app.services.ocr_service.preprocess_image") as mock_preprocess:
        with patch("app.services.ocr_service.extract_text_from_image") as mock_extract:
            
            # preprocess_image now returns (image_array, image_height, image_width)
            mock_preprocess.return_value = ("fake_image_array", 100, 100)
            mock_extract.return_value = {
                "raw_result": mock_ocr_result,
                "processing_time_ms": 120
            }
            
            ocr_resp = client.post(f"/api/v1/inspections/{inspection_id}/ocr")
            
    assert ocr_resp.status_code == 200
    data = ocr_resp.json()
    
    assert data["status"] == "COMPLETED"
    assert "MRP Rs. 50.00" in data["raw_full_text"]
    assert data["processing_time_ms"] == 120
    assert data["image_width"] == 100
    assert data["image_height"] == 100
    assert len(data["text_regions"]) == 2
    assert data["text_regions"][0]["text"] == "MRP Rs. 50.00"
    assert data["text_regions"][0]["confidence"] == 0.98
    # Verify normalized bbox format {x, y, width, height}
    bbox = data["text_regions"][0]["bbox"]
    assert bbox["x"] == 10
    assert bbox["y"] == 10
    assert bbox["width"] == 90
    assert bbox["height"] == 20

def test_get_ocr_results_not_found():
    """
    Test fetching OCR results for an invalid inspection or one without OCR.
    """
    import uuid
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/inspections/{fake_id}/ocr")
    assert resp.status_code == 404
