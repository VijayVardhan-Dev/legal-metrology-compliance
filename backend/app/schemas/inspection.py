from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List
from .product import ProductResponse
from .evidence import EvidenceResponse

class InspectionBase(BaseModel):
    status: str
    compliance_score: Optional[float] = None
    notes: Optional[str] = None

class InspectionResponse(InspectionBase):
    id: str
    product_id: str
    inspector_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class InspectionDetailResponse(InspectionResponse):
    product: ProductResponse
    evidence_items: List[EvidenceResponse] = []

class ImageUploadResponse(BaseModel):
    filename: str
    content_type: str

class InspectionUploadResponse(BaseModel):
    inspection_id: str
    product_id: str
    status: str
    image: ImageUploadResponse
    message: str
