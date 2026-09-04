from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ai.declaration.extractor import DeclarationExtractor
from app.models.declaration import Declaration
from app.models.inspection import Inspection
from app.models.ocr_result import OCRResult
from app.schemas.declaration import DeclarationListResponse


class DeclarationService:
    def __init__(self, db: Session):
        self.db = db
        self.extractor = DeclarationExtractor()

    def extract_for_inspection(self, inspection_id: str) -> DeclarationListResponse:
        inspection = (
            self.db.query(Inspection).filter(Inspection.id == inspection_id).first()
        )
        if not inspection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inspection not found",
            )

        ocr_result = (
            self.db.query(OCRResult)
            .filter(OCRResult.inspection_id == inspection_id)
            .first()
        )
        if not ocr_result:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="OCR has not been completed for this inspection",
            )
        if ocr_result.status != "COMPLETED":
            detail = (
                "OCR failed; declarations are unavailable"
                if ocr_result.status == "FAILED"
                else "OCR has not been completed for this inspection"
            )
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

        self.db.query(Declaration).filter(
            Declaration.inspection_id == inspection_id
        ).delete(synchronize_session=False)

        extracted = self.extractor.extract(ocr_result)
        for item in extracted:
            self.db.add(
                Declaration(
                    inspection_id=inspection_id,
                    field_name=item.declaration_type.lower(),
                    declaration_type=item.declaration_type,
                    value=item.value,
                    normalized_value=item.normalized_value,
                    unit=item.unit,
                    source_text=item.source_text,
                    confidence=item.confidence,
                    ocr_confidence=item.ocr_confidence,
                    extraction_method=item.extraction_method,
                    status=item.status,
                    ocr_text_region_id=item.ocr_text_region_id,
                )
            )
        self.db.commit()
        declarations = (
            self.db.query(Declaration)
            .filter(Declaration.inspection_id == inspection_id)
            .order_by(Declaration.created_at, Declaration.id)
            .all()
        )
        return DeclarationListResponse(
            inspection_id=inspection_id,
            declarations=[
                declaration_to_response(declaration) for declaration in declarations
            ],
        )

    def get_for_inspection(self, inspection_id: str) -> DeclarationListResponse:
        inspection = (
            self.db.query(Inspection).filter(Inspection.id == inspection_id).first()
        )
        if not inspection:
            raise HTTPException(status_code=404, detail="Inspection not found")
        declarations = (
            self.db.query(Declaration)
            .filter(Declaration.inspection_id == inspection_id)
            .order_by(Declaration.created_at, Declaration.id)
            .all()
        )
        return DeclarationListResponse(
            inspection_id=inspection_id,
            declarations=[
                declaration_to_response(declaration) for declaration in declarations
            ],
        )


def declaration_to_response(declaration: Declaration):
    from app.schemas.declaration import DeclarationResponse

    return DeclarationResponse.model_validate(declaration)
