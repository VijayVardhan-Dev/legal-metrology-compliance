from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CalibrationInput(BaseModel):
    reference_length_mm: float | None = Field(default=None, gt=0)
    reference_pixels: float | None = Field(default=None, gt=0)
    pixels_per_mm: float | None = Field(default=None, gt=0)


class VisualAnalysisRequest(BaseModel):
    calibration: CalibrationInput | None = None


class VisualFinding(BaseModel):
    finding_type: str
    status: str
    message: str
    declaration_id: str | None = None
    declaration_type: str | None = None
    evidence: dict[str, Any] | None = None


class VisualAnalysisResponse(BaseModel):
    id: str
    inspection_id: str
    evidence_id: str | None = None
    status: str
    processing_status: str
    quality_status: str = "REVIEW_REQUIRED"
    image_width: int | None = None
    image_height: int | None = None
    quality_score: float | None = None
    metrics: dict[str, Any] = {}
    visibility_flags: dict[str, Any] = {}
    findings: list[dict[str, Any]] = []
    warnings: list[str] = []
    declarations: list[dict[str, Any]] = []
    calibration: dict[str, Any] | None = None
    evidence: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


VisualAnalysisResultResponse = VisualAnalysisResponse
