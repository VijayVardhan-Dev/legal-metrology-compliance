from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RuleResultResponse(BaseModel):
    id: str
    inspection_id: str
    rule_id: str
    status: str
    severity: str
    reason: str
    legal_reference: str
    evidence: list[dict[str, Any]] = []
    declaration_ids: list[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplianceResponse(BaseModel):
    inspection_id: str
    overall_status: str
    results: list[RuleResultResponse]
