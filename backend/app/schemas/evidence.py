from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional

class EvidenceBase(BaseModel):
    file_path: str
    bbox_x: Optional[int] = None
    bbox_y: Optional[int] = None
    bbox_width: Optional[int] = None
    bbox_height: Optional[int] = None

class EvidenceCreate(EvidenceBase):
    inspection_id: str
    violation_id: Optional[str] = None

class EvidenceResponse(EvidenceBase):
    id: str
    inspection_id: str
    violation_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplianceEvidenceResponse(BaseModel):
    evidence_id: str
    declaration_id: str | None = None
    rule_id: str | None = None
    evidence_type: str
    ocr_region_id: str | None = None
    bbox: dict[str, int | None] | None = None
    source_text: str | None = None
    value: str | None = None
    confidence: float | None = None
    ocr_confidence: float | None = None
    visual_status: str | None = None
    visual_finding_ids: list[str] = Field(default_factory=list)
    image_width: int | None = None
    image_height: int | None = None
    declaration_type: str | None = None
    legal_reference: str | None = None
    reason: str | None = None
    warnings: list[str] = Field(default_factory=list)
