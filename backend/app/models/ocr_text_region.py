import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import String, DateTime, ForeignKey, Float, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OCRTextRegion(Base):
    __tablename__ = "ocr_text_regions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ocr_result_id: Mapped[str] = mapped_column(String(36), ForeignKey("ocr_results.id"), nullable=False)

    text: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Raw bounding box from PaddleOCR: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    bounding_box: Mapped[Any] = mapped_column(JSON, nullable=False)

    # Normalized bounding box: {x, y, width, height} rectangle
    bbox_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox_height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    ocr_result = relationship("OCRResult", back_populates="text_regions")
    declarations = relationship("Declaration", back_populates="ocr_text_region")
