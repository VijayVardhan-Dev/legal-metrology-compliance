from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DeclarationResponse(BaseModel):
    id: str
    inspection_id: str
    declaration_type: str
    field_name: str
    value: str | None = None
    normalized_value: Any = None
    unit: str | None = None
    source_text: str
    confidence: float | None = None
    ocr_confidence: float | None = None
    extraction_method: str
    status: str
    ocr_text_region_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeclarationListResponse(BaseModel):
    inspection_id: str
    declarations: list[DeclarationResponse]
