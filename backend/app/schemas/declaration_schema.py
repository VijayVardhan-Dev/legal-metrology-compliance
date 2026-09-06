from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


class DeclarationField(BaseModel):
    value: str | None = None
    evidence: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    status: Literal["found", "missing", "uncertain"] = "missing"
    unit: str | None = None
    normalized_value: Any = None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: Any) -> str:
        if isinstance(value, str):
            val = value.strip().lower()
            if val in {"found", "present", "complete", "yes", "true"}:
                return "found"
            if val in {"missing", "absent", "none", "no", "false"}:
                return "missing"
            if val in {"uncertain", "incomplete", "ambiguous", "review_required"}:
                return "uncertain"
        return "missing"

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, value: Any) -> float:
        try:
            val = float(value)
            return max(0.0, min(1.0, val))
        except (ValueError, TypeError):
            return 0.0


class StandardDeclarationExtraction(BaseModel):
    product_name: DeclarationField = Field(default_factory=DeclarationField)
    brand: DeclarationField = Field(default_factory=DeclarationField)
    net_quantity: DeclarationField = Field(default_factory=DeclarationField)
    mrp: DeclarationField = Field(default_factory=DeclarationField)
    manufacturer_name: DeclarationField = Field(default_factory=DeclarationField)
    manufacturer_address: DeclarationField = Field(default_factory=DeclarationField)
    packer_name: DeclarationField = Field(default_factory=DeclarationField)
    packer_address: DeclarationField = Field(default_factory=DeclarationField)
    importer_name: DeclarationField = Field(default_factory=DeclarationField)
    importer_address: DeclarationField = Field(default_factory=DeclarationField)
    date_of_manufacture: DeclarationField = Field(default_factory=DeclarationField)
    date_of_packing: DeclarationField = Field(default_factory=DeclarationField)
    best_before: DeclarationField = Field(default_factory=DeclarationField)
    use_by: DeclarationField = Field(default_factory=DeclarationField)
    consumer_care_details: DeclarationField = Field(default_factory=DeclarationField)
    batch_lot_number: DeclarationField = Field(default_factory=DeclarationField)
    country_of_origin: DeclarationField = Field(default_factory=DeclarationField)

    def to_canonical_dict(self) -> dict[str, dict[str, Any]]:
        """Returns standard serialized dictionary format."""
        return self.model_dump()
