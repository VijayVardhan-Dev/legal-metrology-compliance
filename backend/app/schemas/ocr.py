from pydantic import BaseModel, ConfigDict, computed_field
from typing import List, Optional, Any
from datetime import datetime


# ---------------------------------------------------------------------------
# Bounding Box — normalized {x, y, width, height} format
# ---------------------------------------------------------------------------
class BoundingBox(BaseModel):
    """Axis-aligned bounding rectangle derived from the OCR polygon."""
    x: int
    y: int
    width: int
    height: int


# ---------------------------------------------------------------------------
# OCR Text Region schemas
# ---------------------------------------------------------------------------
class OCRTextRegionBase(BaseModel):
    text: str
    confidence: float
    bounding_box: Any  # Raw PaddleOCR polygon [[x1,y1], ...]


class OCRTextRegionCreate(OCRTextRegionBase):
    ocr_result_id: str
    bbox_x: Optional[int] = None
    bbox_y: Optional[int] = None
    bbox_width: Optional[int] = None
    bbox_height: Optional[int] = None


class OCRTextRegionResponse(BaseModel):
    """Public-facing response for a single text region."""
    id: str
    ocr_result_id: str
    text: str
    confidence: float
    bbox: BoundingBox
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, obj: Any) -> "OCRTextRegionResponse":
        """Build from the SQLAlchemy model, mapping bbox_x/y/width/height → nested BoundingBox."""
        return cls(
            id=obj.id,
            ocr_result_id=obj.ocr_result_id,
            text=obj.text,
            confidence=obj.confidence,
            bbox=BoundingBox(
                x=obj.bbox_x or 0,
                y=obj.bbox_y or 0,
                width=obj.bbox_width or 0,
                height=obj.bbox_height or 0,
            ),
            created_at=obj.created_at,
        )


# Keep backward-compatible alias used by __init__.py imports
OCRTextRegion = OCRTextRegionResponse


# ---------------------------------------------------------------------------
# OCR Result schemas
# ---------------------------------------------------------------------------
class OCRResultBase(BaseModel):
    status: str  # PENDING | PROCESSING | COMPLETED | FAILED
    error_message: Optional[str] = None
    raw_full_text: Optional[str] = None
    average_confidence: Optional[float] = None
    processing_time_ms: Optional[int] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    metadata_json: Optional[Any] = None


class OCRResultCreate(OCRResultBase):
    inspection_id: str


class OCRResultResponse(BaseModel):
    """Public-facing response for an OCR result with all nested text regions."""
    id: str
    inspection_id: str
    status: str
    error_message: Optional[str] = None
    raw_full_text: Optional[str] = None
    average_confidence: Optional[float] = None
    processing_time_ms: Optional[int] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    metadata_json: Optional[Any] = None
    created_at: datetime
    updated_at: datetime
    text_regions: List[OCRTextRegionResponse] = []

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, obj: Any) -> "OCRResultResponse":
        """Build from the SQLAlchemy OCRResult model, converting each region via from_orm_model."""
        return cls(
            id=obj.id,
            inspection_id=obj.inspection_id,
            status=obj.status,
            error_message=obj.error_message,
            raw_full_text=obj.raw_full_text,
            average_confidence=obj.average_confidence,
            processing_time_ms=obj.processing_time_ms,
            image_width=obj.image_width,
            image_height=obj.image_height,
            metadata_json=obj.metadata_json,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            text_regions=[
                OCRTextRegionResponse.from_orm_model(r)
                for r in (obj.text_regions or [])
            ],
        )


# Keep backward-compatible alias used by __init__.py and API routes
OCRResult = OCRResultResponse
