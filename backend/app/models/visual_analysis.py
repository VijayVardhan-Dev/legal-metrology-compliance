import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class VisualAnalysis(Base):
    """Persisted, reproducible visual quality and declaration visibility analysis."""

    __tablename__ = "visual_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    inspection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inspections.id"), nullable=False, unique=True, index=True
    )
    evidence_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("evidence.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="REVIEW_REQUIRED")
    processing_status: Mapped[str] = mapped_column(String(30), nullable=False, default="COMPLETED")
    quality_status: Mapped[str] = mapped_column(String(30), nullable=False, default="REVIEW_REQUIRED")
    image_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    metrics: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    visibility_flags: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    findings: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    warnings: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    declarations: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    calibration: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    evidence: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    inspection = relationship("Inspection", back_populates="visual_analysis")
    evidence_item = relationship("Evidence")


# A descriptive alias for consumers that call the persisted result a result.
VisualAnalysisResult = VisualAnalysis
