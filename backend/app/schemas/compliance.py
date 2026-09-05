from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RuleResultResponse(BaseModel):
    id: str
    inspection_id: str
    rule_id: str
    rule_name: str = ""
    status: str
    severity: str
    reason: str
    legal_reference: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    declaration_ids: list[str] = Field(default_factory=list)
    applicability_status: str = "APPLICABLE"
    confidence: float | None = None
    ocr_region_ids: list[str] = Field(default_factory=list)
    visual_finding_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("evidence", "declaration_ids", "ocr_region_ids", "visual_finding_ids", "warnings", mode="before")
    @classmethod
    def empty_collection_for_null(cls, value):
        return value if value is not None else []


class ComplianceResponse(BaseModel):
    inspection_id: str
    overall_status: str
    total_rules: int = 0
    compliant_rules: int = 0
    non_compliant_rules: int = 0
    review_required_rules: int = 0
    applicable_rules: int = 0
    not_applicable_rules: int = 0
    overall_confidence: float | None = None
    evaluated_at: datetime | None = None
    rule_engine_version: str | None = None
    classification_version: str | None = None
    ocr_result_id: str | None = None
    visual_analysis_id: str | None = None
    results: list[RuleResultResponse]
