import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class NutritionAnalysis(Base):
    __tablename__ = "nutrition_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    inspection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inspections.id"), nullable=False, unique=True, index=True
    )
    ocr_result_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("ocr_results.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="COMPLETED")
    nutrition_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ingredient_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingredient_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    nutrition: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    ingredients: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    allergens: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    insights: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    sections: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    warnings: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    product_database: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    source_comparison: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    suitability: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    nlp_analysis: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    inspection = relationship("Inspection", back_populates="nutrition_analysis")
    ocr_result = relationship("OCRResult")
