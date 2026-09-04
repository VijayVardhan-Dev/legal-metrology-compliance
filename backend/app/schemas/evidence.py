from pydantic import BaseModel, ConfigDict
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
