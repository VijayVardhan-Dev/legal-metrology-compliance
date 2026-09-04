import pytest
from fastapi.testclient import TestClient
import io
from PIL import Image

from app.main import app

client = TestClient(app)

def create_test_image(format="JPEG", size=(100, 100)):
    file = io.BytesIO()
    image = Image.new("RGB", size, color="red")
    image.save(file, format=format)
    file.seek(0)
    return file

def test_upload_valid_image_jpeg():
    img = create_test_image("JPEG")
    response = client.post(
        "/api/v1/inspections",
        files={"image": ("test.jpg", img, "image/jpeg")},
        data={"product_name": "Test Biscuits", "category": "food"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "PENDING"
    assert "inspection_id" in data
    assert data["image"]["content_type"] == "image/jpeg"

    # Test retrieval
    inspection_id = data["inspection_id"]
    get_response = client.get(f"/api/v1/inspections/{inspection_id}")
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["id"] == inspection_id
    assert get_data["status"] == "PENDING"
    assert get_data["product"]["name"] == "Test Biscuits"
    assert get_data["product"]["category"] == "food"

    # Test image retrieval
    img_response = client.get(f"/api/v1/inspections/{inspection_id}/image")
    assert img_response.status_code == 200
    assert img_response.headers["content-type"] == "image/jpeg"

def test_upload_invalid_format():
    # Create fake PDF bytes
    file = io.BytesIO(b"%PDF-1.4...")
    response = client.post(
        "/api/v1/inspections",
        files={"image": ("test.pdf", file, "application/pdf")},
        data={"product_name": "Test Product", "category": "unknown"}
    )
    assert response.status_code == 400
    assert "Invalid image file" in response.json()["detail"] or "Unsupported" in response.json()["detail"]

def test_upload_empty_file():
    file = io.BytesIO(b"")
    response = client.post(
        "/api/v1/inspections",
        files={"image": ("empty.jpg", file, "image/jpeg")},
        data={"product_name": "Test Product", "category": "unknown"}
    )
    assert response.status_code == 400
    assert "Empty" in response.json()["detail"]

def test_get_nonexistent_inspection():
    response = client.get("/api/v1/inspections/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
