import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Violation(Base):
    __tablename__ = "violations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    inspection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inspections.id"), nullable=False, index=True
    )
    rule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rules.id"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # FAIL | REVIEW_REQUIRED
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="HIGH"
    )  # HIGH | MEDIUM | LOW
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    requires_review: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    inspection = relationship("Inspection", back_populates="violations")
    rule = relationship("Rule", back_populates="violations")
    evidence_items = relationship("Evidence", back_populates="violation")
