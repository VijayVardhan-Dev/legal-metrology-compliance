from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_empty_safe_shapes_and_history_pagination():
    history = client.get("/api/v1/inspections", params={"page": 1, "page_size": 1})
    assert history.status_code == 200
    body = history.json()
    assert {"items", "page", "page_size", "total", "total_pages"} <= body.keys()
    assert body["page"] == 1
    assert body["page_size"] == 1
    assert len(body["items"]) <= 1

    summary = client.get("/api/v1/dashboard/summary")
    assert summary.status_code == 200
    assert summary.json()["total_inspections"] >= 0

    for path in (
        "/api/v1/dashboard/compliance-distribution",
        "/api/v1/dashboard/category-distribution",
        "/api/v1/dashboard/rules",
        "/api/v1/dashboard/recent-inspections",
    ):
        response = client.get(path)
        assert response.status_code == 200


def test_history_filters_validate_and_search():
    assert client.get(
        "/api/v1/inspections", params={"compliance_status": "NOT_A_STATUS"}
    ).status_code == 422
    assert client.get(
        "/api/v1/inspections", params={"sort_by": "created_at;drop table inspections"}
    ).status_code == 422
    assert client.get(
        "/api/v1/inspections", params={"page_size": 101}
    ).status_code == 422
    assert client.get(
        "/api/v1/inspections",
        params={"minimum_confidence": 0.9, "maximum_confidence": 0.1},
    ).status_code == 422
    assert client.get(
        "/api/v1/inspections",
        params={"date_from": "2026-09-06T00:00:00+00:00", "date_to": "2026-09-05T00:00:00+00:00"},
    ).status_code == 422

    response = client.get(
        "/api/v1/inspections",
        params={"search": "unlikely-product-name", "sort_by": "product_name", "sort_order": "asc"},
    )
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_dashboard_category_and_rule_response_shapes():
    categories = client.get("/api/v1/dashboard/category-distribution").json()
    assert isinstance(categories["items"], list)
    if categories["items"]:
        assert {"category", "subcategory", "inspection_count"} <= categories["items"][0].keys()

    rules = client.get("/api/v1/dashboard/rules").json()
    assert isinstance(rules["items"], list)
    if rules["items"]:
        assert {
            "rule_id",
            "rule_name",
            "total_evaluations",
            "compliant_count",
            "non_compliant_count",
            "review_required_count",
            "not_applicable_count",
        } <= rules["items"][0].keys()
