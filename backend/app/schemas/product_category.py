from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ProductCategoryResponse(BaseModel):
    id: str
    inspection_id: str
    product_id: str
    category: str
    subcategory: str | None = None
    confidence: float | None = None
    evidence: list[Any] | None = None
    source_text: str | None = None
    classification_method: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
