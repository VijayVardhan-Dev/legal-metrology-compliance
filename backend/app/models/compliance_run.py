import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ComplianceRun(Base):
    __tablename__ = "compliance_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    inspection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inspections.id"), nullable=False, unique=True, index=True
    )
    overall_status: Mapped[str] = mapped_column(String(30), nullable=False)
    total_rules: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    compliant_rules: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    non_compliant_rules: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_required_rules: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    applicable_rules: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    not_applicable_rules: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overall_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    rule_engine_version: Mapped[str] = mapped_column(String(30), nullable=False)
    classification_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ocr_result_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    visual_analysis_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    inspection = relationship("Inspection", back_populates="compliance_run")
