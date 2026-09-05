from types import SimpleNamespace

from app.services.visual_analysis_service import VisualAnalysisService


def test_quality_score_is_bounded_and_low_for_small_blurry_images():
    score = VisualAnalysisService._quality_score(120, 120, 2.0, 0.0)
    assert 0 <= score <= 1
    assert score < 0.60


def test_visibility_requires_normalized_ocr_region():
    declaration = SimpleNamespace(id="d1", ocr_confidence=0.95, confidence=0.95)
    result = VisualAnalysisService._visibility(None, declaration, 1000, 1000, 1.0)
    assert result["uncertain"] is True
    assert result["visible"] is False


def test_visibility_preserves_bbox_and_confidence_evidence():
    region = SimpleNamespace(bbox_x=10, bbox_y=20, bbox_width=100, bbox_height=40)
    declaration = SimpleNamespace(id="d1", ocr_confidence=0.95, confidence=0.95)
    result = VisualAnalysisService._visibility(region, declaration, 1000, 1000, 1.0)
    assert result["visible"] is True
    assert result["bbox"] == {"x": 10, "y": 20, "width": 100, "height": 40}


def test_calibration_can_be_derived_from_reference():
    request = SimpleNamespace(
        calibration=SimpleNamespace(
            model_dump=lambda exclude_none: {
                "reference_length_mm": 20,
                "reference_pixels": 100,
            }
        )
    )
    result = VisualAnalysisService._calibration(request)
    assert result["pixels_per_mm"] == 5
