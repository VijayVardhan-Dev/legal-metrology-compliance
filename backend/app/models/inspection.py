import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id"), nullable=False, index=True
    )
    inspector_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDING"
    )  # PENDING | PROCESSING | COMPLIANT | NON_COMPLIANT | REVIEW_REQUIRED
    compliance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    product = relationship("Product", back_populates="inspections")
    inspector = relationship("User", back_populates="inspections")
    declarations = relationship("Declaration", back_populates="inspection")
    violations = relationship("Violation", back_populates="inspection")
    evidence_items = relationship("Evidence", back_populates="inspection")
    reports = relationship("Report", back_populates="inspection")
    ocr_result = relationship("OCRResult", back_populates="inspection", uselist=False)
    rule_results = relationship(
        "RuleResult", back_populates="inspection", cascade="all, delete-orphan"
    )
    product_category = relationship(
        "ProductCategory", back_populates="inspection", uselist=False,
        cascade="all, delete-orphan",
    )
    visual_analysis = relationship(
        "VisualAnalysis", back_populates="inspection", uselist=False,
        cascade="all, delete-orphan",
    )
    compliance_run = relationship(
        "ComplianceRun", back_populates="inspection", uselist=False,
        cascade="all, delete-orphan",
    )
