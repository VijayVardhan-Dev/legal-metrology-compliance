import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RuleResult(Base):
    __tablename__ = "rule_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    inspection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inspections.id"), nullable=False, index=True
    )
    rule_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    rule_definition_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("rules.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    legal_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    evidence: Mapped[object | None] = mapped_column(JSON, nullable=True)
    declaration_ids: Mapped[object | None] = mapped_column(JSON, nullable=True)
    applicability_status: Mapped[str] = mapped_column(String(30), nullable=False, default="APPLICABLE")
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    ocr_region_ids: Mapped[object | None] = mapped_column(JSON, nullable=True)
    visual_finding_ids: Mapped[object | None] = mapped_column(JSON, nullable=True)
    warnings: Mapped[object | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    inspection = relationship("Inspection", back_populates="rule_results")
    rule_definition = relationship("Rule", back_populates="results")
