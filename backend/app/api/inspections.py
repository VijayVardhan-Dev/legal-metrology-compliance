from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
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

router = APIRouter()

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

