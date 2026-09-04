from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_returns_200():
    response = client.get("/")
    assert response.status_code == 200


def test_root_response_body():
    response = client.get("/")
    data = response.json()
    assert data["message"] == "Legal Metrology Compliance API"
    assert "version" in data


def test_health_returns_200():
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_response_body():
    response = client.get("/api/v1/health")
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "legal-metrology-compliance-api"
