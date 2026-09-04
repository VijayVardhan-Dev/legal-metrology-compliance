import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Text, JSON, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    rule_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )  # e.g. MRP-001, NETQTY-001
    rule_id: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    rule_family: Mapped[str | None] = mapped_column(String(50), nullable=True)
    legal_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requirement: Mapped[str | None] = mapped_column(Text, nullable=True)
    applicability_conditions: Mapped[object | None] = mapped_column(JSON, nullable=True)
    exemptions: Mapped[object | None] = mapped_column(JSON, nullable=True)
    required_declaration: Mapped[str | None] = mapped_column(String(50), nullable=True)
    validation_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    effective_from: Mapped[object | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[object | None] = mapped_column(Date, nullable=True)
    rule_version: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. mrp, net_quantity, manufacturer, date
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="HIGH"
    )  # HIGH | MEDIUM | LOW
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    violations = relationship("Violation", back_populates="rule")
    results = relationship("RuleResult", back_populates="rule_definition")
