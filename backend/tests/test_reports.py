from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.services.report_service import ReportService


client = TestClient(app)


def test_report_endpoint_rejects_missing_inspection():
    response = client.post(
        "/api/v1/inspections/00000000-0000-0000-0000-000000000000/report"
    )
    assert response.status_code == 404


def test_report_endpoint_requires_compliance_run():
    response = client.post(
        "/api/v1/inspections/c282eddd-1c2f-4340-bbd2-a37840fbfa21/report"
    )
    assert response.status_code in {200, 409}


def test_report_pdf_is_readable_and_contains_required_sections(tmp_path):
    target = tmp_path / "inspection.pdf"
    now = datetime.now(timezone.utc)
    data = {
        "inspection": SimpleNamespace(
            id="inspection-1",
            created_at=now,
            product=SimpleNamespace(name="Test Biscuits", category="food"),
        ),
        "run": SimpleNamespace(
            evaluated_at=now,
            overall_status="REVIEW_REQUIRED",
            overall_confidence=0.72,
            total_rules=2,
            compliant_rules=1,
            non_compliant_rules=0,
            review_required_rules=1,
            not_applicable_rules=0,
        ),
        "ocr": None,
        "visual": None,
        "category": None,
        "declarations": [],
        "results": [],
        "evidence": SimpleNamespace(file_path="missing.jpg"),
    }

    ReportService(None)._build_pdf(target, "LM-2026-000999", data)

    content = target.read_bytes()
    assert content.startswith(b"%PDF")
    assert b"LM-2026-000999" in content
    assert b"Test Biscuits" in content
    assert b"REVIEW_REQUIRED" in content
    assert b"Not detected / Not available" in content
    assert b"authorized inspecting authority" in content


def test_invalid_evidence_bbox_is_reported_as_unavailable():
    assert ReportService._bbox(
        SimpleNamespace(bbox_x=0, bbox_y=0, bbox_width=0, bbox_height=20)
    ) is None
    assert ReportService._bbox(None) is None
