import logging
import traceback
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status

from app.models.inspection import Inspection
from app.models.evidence import Evidence
from app.models.ocr_result import OCRResult
from app.models.ocr_text_region import OCRTextRegion
from app.schemas.ocr import OCRResultResponse

from ai.ocr.preprocess import preprocess_image
from ai.ocr.engine import extract_text_from_image
from ai.ocr.parser import parse_ocr_results

logger = logging.getLogger(__name__)


class OCRService:
    def __init__(self, db: Session):
        self.db = db

    def process_inspection_ocr(self, inspection_id: str) -> OCRResultResponse:
        """
        Coordinates the entire OCR pipeline for a given inspection.

        Status flow:
            PENDING → PROCESSING → COMPLETED
                                 → FAILED

        A FAILED OCR must never cause the Inspection to be marked NON_COMPLIANT.
        """
        # 1. Fetch Inspection and Primary Evidence
        inspection = self.db.query(Inspection).filter(Inspection.id == inspection_id).first()
        if not inspection:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

        evidence = self.db.query(Evidence).filter(
            Evidence.inspection_id == inspection_id,
            Evidence.violation_id.is_(None)
        ).first()

        if not evidence:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No primary image evidence found for this inspection."
            )

        # 2. Check for existing OCR Result or Create New (PENDING)
        ocr_result = self.db.query(OCRResult).filter(OCRResult.inspection_id == inspection_id).first()
        if not ocr_result:
            ocr_result = OCRResult(inspection_id=inspection_id, status="PENDING")
            self.db.add(ocr_result)
        else:
            # Clear old text regions if re-running
            self.db.query(OCRTextRegion).filter(OCRTextRegion.ocr_result_id == ocr_result.id).delete()
            ocr_result.status = "PENDING"
            ocr_result.error_message = None

        self.db.commit()
        self.db.refresh(ocr_result)

        # 3. Transition to PROCESSING
        ocr_result.status = "PROCESSING"
        self.db.commit()
        self.db.refresh(ocr_result)

        try:
            # 4. Preprocess Image — now returns dimensions too
            logger.info(f"Preprocessing image for OCR: {evidence.file_path}")
            image_array, image_height, image_width = preprocess_image(evidence.file_path)

            # 5. Run OCR Engine
            logger.info(f"Running OCR Engine for inspection {inspection_id}")
            engine_output = extract_text_from_image(image_array)
            raw_result = engine_output["raw_result"]
            processing_time = engine_output["processing_time_ms"]

            # 6. Parse Results — now includes normalized bbox per region
            logger.info("Parsing OCR results...")
            regions, full_text, avg_conf = parse_ocr_results(raw_result, ocr_result.id)

            # 7. Save text regions (with normalized bbox)
            for region in regions:
                db_region = OCRTextRegion(
                    ocr_result_id=region.ocr_result_id,
                    text=region.text,
                    confidence=region.confidence,
                    bounding_box=region.bounding_box,
                    bbox_x=region.bbox_x,
                    bbox_y=region.bbox_y,
                    bbox_width=region.bbox_width,
                    bbox_height=region.bbox_height,
                )
                self.db.add(db_region)

            # 8. Update OCRResult → COMPLETED with all metadata
            ocr_result.status = "COMPLETED"
            ocr_result.raw_full_text = full_text
            ocr_result.average_confidence = avg_conf
            ocr_result.processing_time_ms = processing_time
            ocr_result.image_width = image_width
            ocr_result.image_height = image_height
            ocr_result.metadata_json = {
                "engine": "PaddleOCR",
                "image_width": image_width,
                "image_height": image_height,
                "processing_time_ms": processing_time,
                "average_confidence": round(avg_conf, 4),
                "total_regions": len(regions),
            }

            self.db.commit()
            self.db.refresh(ocr_result)
            logger.info(f"OCR successfully completed for inspection {inspection_id}")
            return OCRResultResponse.from_orm_model(ocr_result)

        except Exception as e:
            self.db.rollback()
            logger.error(f"OCR failed for inspection {inspection_id}: {str(e)}\n{traceback.format_exc()}")

            # Re-fetch ocr_result in a new transaction context since rollback detached it
            ocr_result = self.db.query(OCRResult).filter(OCRResult.inspection_id == inspection_id).first()
            if ocr_result:
                ocr_result.status = "FAILED"
                ocr_result.error_message = str(e)
                self.db.commit()
                self.db.refresh(ocr_result)

                # ─── SAFETY GUARD ───────────────────────────────────────────
                # A failed OCR must NEVER cause the inspection to be set to
                # NON_COMPLIANT.  Re-fetch inspection and ensure its status
                # is not inadvertently changed by a downstream handler.
                inspection = self.db.query(Inspection).filter(Inspection.id == inspection_id).first()
                if inspection and inspection.status == "NON_COMPLIANT":
                    logger.warning(
                        f"Inspection {inspection_id} was set to NON_COMPLIANT after OCR failure — "
                        f"reverting to PENDING. A failed OCR must not determine compliance."
                    )
                    inspection.status = "PENDING"
                    self.db.commit()

                return OCRResultResponse.from_orm_model(ocr_result)

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OCR processing failed"
            )

    def get_ocr_result(self, inspection_id: str) -> OCRResultResponse:
        """Retrieve the persisted OCR result for an inspection."""
        result = self.db.query(OCRResult).filter(OCRResult.inspection_id == inspection_id).first()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OCR result not found for this inspection"
            )
        return OCRResultResponse.from_orm_model(result)
