import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    inspection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inspections.id"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    report_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    report_status: Mapped[str] = mapped_column(String(30), nullable=False, default="COMPLETED")
    overall_compliance_status: Mapped[str] = mapped_column(String(30), nullable=False)
    overall_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    compliance_run_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("compliance_runs.id"), nullable=True, index=True)
    rule_engine_version: Mapped[str | None] = mapped_column(String(30), nullable=True)
    classification_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ocr_result_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ocr_results.id"), nullable=True, index=True)
    visual_analysis_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("visual_analyses.id"), nullable=True, index=True)
    report_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pdf"
    )  # pdf | docx
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    inspection = relationship("Inspection", back_populates="reports")
