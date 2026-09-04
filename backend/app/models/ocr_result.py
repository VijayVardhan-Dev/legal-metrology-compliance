import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import String, DateTime, ForeignKey, Float, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OCRResult(Base):
    __tablename__ = "ocr_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    inspection_id: Mapped[str] = mapped_column(String(36), ForeignKey("inspections.id"), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_full_text: Mapped[str | None] = mapped_column(String, nullable=True)
    average_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)  # E.g., resolution, language, engine version

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    inspection = relationship("Inspection", back_populates="ocr_result", uselist=False)
    text_regions = relationship("OCRTextRegion", back_populates="ocr_result", cascade="all, delete-orphan")
