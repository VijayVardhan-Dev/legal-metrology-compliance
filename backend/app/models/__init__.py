# Import all models so SQLAlchemy and Alembic can discover them
from app.models.user import User
from app.models.product import Product
from app.models.inspection import Inspection
from app.models.declaration import Declaration
from app.models.rule import Rule
from app.models.violation import Violation
from app.models.evidence import Evidence
from app.models.report import Report
from app.models.ocr_result import OCRResult
from app.models.ocr_text_region import OCRTextRegion
from app.models.rule_result import RuleResult
from app.models.product_category import ProductCategory

__all__ = [
    "User",
    "Product",
    "Inspection",
    "Declaration",
    "Rule",
    "Violation",
    "Evidence",
    "Report",
    "OCRResult",
    "OCRTextRegion",
    "RuleResult",
    "ProductCategory",
]
