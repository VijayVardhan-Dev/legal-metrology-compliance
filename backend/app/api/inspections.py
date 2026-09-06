from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from app.core.database import get_db
from app.schemas.inspection import InspectionUploadResponse, InspectionDetailResponse
from app.services.inspection_service import inspection_service
from app.services.storage_service import storage_service
from app.models.inspection import Inspection
from app.models.evidence import Evidence
from app.schemas.ocr import OCRResultResponse
from app.services.ocr_service import OCRService
from app.services.declaration_service import DeclarationService
from app.schemas.declaration import DeclarationListResponse
from app.schemas.compliance import ComplianceResponse
from app.schemas.evidence import ComplianceEvidenceResponse
from app.services.compliance_service import ComplianceService
from app.schemas.product_category import ProductCategoryResponse
from app.services.category_service import ProductCategoryService
from app.schemas.history import InspectionHistoryResponse
from app.services.dashboard_service import DashboardService
from app.schemas.nutrition import NutritionAnalysisResponse
from app.services.nutrition_service import NutritionAnalysisService

router = APIRouter()

@router.get("", response_model=InspectionHistoryResponse)
def list_inspections(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    compliance_status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    subcategory: str | None = Query(default=None),
    product_name: str | None = Query(default=None),
    report_number: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None, description="Inclusive ISO 8601 timestamp"),
    date_to: datetime | None = Query(default=None, description="Inclusive ISO 8601 timestamp"),
    minimum_confidence: float | None = Query(default=None, ge=0, le=1),
    maximum_confidence: float | None = Query(default=None, ge=0, le=1),
    search: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    db: Session = Depends(get_db),
):
    return DashboardService(db).history(
        page=page, page_size=page_size, status=status,
        compliance_status=compliance_status, category=category,
        subcategory=subcategory, product_name=product_name,
        report_number=report_number, date_from=date_from, date_to=date_to,
        minimum_confidence=minimum_confidence, maximum_confidence=maximum_confidence,
        search=search, sort_by=sort_by, sort_order=sort_order,
    )

@router.post("", response_model=InspectionUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_inspection_image(
    image: UploadFile = File(...),
    product_name: str = Form(default="Unknown Product"),
    category: str = Form(default="unknown"),
    brand: str = Form(default=None),
    db: Session = Depends(get_db)
):
    """
    Upload a product image and create a new pending inspection.
    """
    return await inspection_service.create_inspection_from_upload(
        db=db,
        image=image,
        product_name=product_name,
        category=category,
        brand=brand
    )

@router.get("/{inspection_id}", response_model=InspectionDetailResponse)
def get_inspection(inspection_id: str, db: Session = Depends(get_db)):
    """
    Retrieve inspection details by ID.
    """
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return inspection

@router.get("/{inspection_id}/image")
def get_inspection_image(inspection_id: str, db: Session = Depends(get_db)):
    """
    Retrieve the original uploaded image for an inspection.
    """
    evidence = db.query(Evidence).filter(
        Evidence.inspection_id == inspection_id,
        Evidence.violation_id.is_(None) # Original image has no violation_id
    ).first()
    
    if not evidence:
        raise HTTPException(status_code=404, detail="Image not found for this inspection")
        
    filename = os.path.basename(evidence.file_path)
    file_path = storage_service.get_upload_path(filename)
    
    return FileResponse(path=file_path)

@router.post("/{inspection_id}/ocr", response_model=OCRResultResponse)
def trigger_ocr(inspection_id: str, db: Session = Depends(get_db)):
    """
    Trigger OCR processing for the uploaded inspection image.
    Status flow: PENDING → PROCESSING → COMPLETED | FAILED
    """
    ocr_service = OCRService(db)
    return ocr_service.process_inspection_ocr(inspection_id)

@router.get("/{inspection_id}/ocr", response_model=OCRResultResponse)
def get_ocr_results(inspection_id: str, db: Session = Depends(get_db)):
    """
    Retrieve OCR results for a specific inspection.
    """
    ocr_service = OCRService(db)
    return ocr_service.get_ocr_result(inspection_id)


@router.post("/{inspection_id}/nutrition-analysis", response_model=NutritionAnalysisResponse)
def analyze_nutrition(inspection_id: str, db: Session = Depends(get_db)):
    """Analyze nutrition, ingredients, allergens, and label insights from completed OCR."""
    return NutritionAnalysisService(db).analyze_for_inspection(inspection_id)


@router.get("/{inspection_id}/nutrition-analysis", response_model=NutritionAnalysisResponse)
def get_nutrition_analysis(inspection_id: str, db: Session = Depends(get_db)):
    return NutritionAnalysisService(db).get_for_inspection(inspection_id)


@router.post("/{inspection_id}/declarations", response_model=DeclarationListResponse)
def extract_declarations(inspection_id: str, db: Session = Depends(get_db)):
    """Extract and persist declarations from a completed OCR result."""
    return DeclarationService(db).extract_for_inspection(inspection_id)


@router.get("/{inspection_id}/declarations", response_model=DeclarationListResponse)
def get_declarations(inspection_id: str, db: Session = Depends(get_db)):
    """Retrieve declarations previously extracted for an inspection."""
    return DeclarationService(db).get_for_inspection(inspection_id)


@router.post("/{inspection_id}/compliance", response_model=ComplianceResponse)
def evaluate_compliance(inspection_id: str, db: Session = Depends(get_db)):
    return ComplianceService(db).evaluate_for_inspection(inspection_id)


@router.get("/{inspection_id}/compliance", response_model=ComplianceResponse)
def get_compliance(inspection_id: str, db: Session = Depends(get_db)):
    return ComplianceService(db).get_for_inspection(inspection_id)


@router.get("/{inspection_id}/evidence", response_model=list[ComplianceEvidenceResponse])
def get_compliance_evidence(
    inspection_id: str,
    rule: str | None = None,
    declaration: str | None = None,
    evidence_type: str | None = None,
    db: Session = Depends(get_db),
):
    return ComplianceService(db).evidence_for_inspection(
        inspection_id, rule=rule, declaration=declaration, evidence_type=evidence_type
    )


@router.post("/{inspection_id}/category", response_model=ProductCategoryResponse)
def classify_category(inspection_id: str, db: Session = Depends(get_db)):
    return ProductCategoryService(db).classify_for_inspection(inspection_id)


@router.get("/{inspection_id}/category", response_model=ProductCategoryResponse)
def get_category(inspection_id: str, db: Session = Depends(get_db)):
    return ProductCategoryService(db).get_for_inspection(inspection_id)
