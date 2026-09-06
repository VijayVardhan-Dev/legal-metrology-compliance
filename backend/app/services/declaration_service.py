import logging
from pathlib import Path
import re
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ai.declaration.extractor import DeclarationExtractor, ExtractedDeclaration
from app.core.config import settings
from app.models.declaration import Declaration
from app.models.evidence import Evidence
from app.models.inspection import Inspection
from app.models.ocr_result import OCRResult
from app.schemas.declaration import DeclarationListResponse, DeclarationResponse
from app.schemas.declaration_schema import DeclarationField, StandardDeclarationExtraction
from app.services.evidence_matcher import EvidenceMatcher
from app.services.storage_service import storage_service
from app.services.vlm_extractor import VLMExtractionError, VLMExtractorService

logger = logging.getLogger(__name__)


class DeclarationService:
    def __init__(self, db: Session):
        self.db = db
        self.spatial_extractor = DeclarationExtractor()
        self.vlm_extractor = VLMExtractorService()
        self.evidence_matcher = EvidenceMatcher()

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

        mode = (settings.EXTRACTOR_MODE or "vlm").strip().lower()
        use_vlm = mode == "vlm"
        fallback_enabled = getattr(settings, "VLM_FALLBACK_ENABLED", False)
        extracted_items: list[ExtractedDeclaration] = []
        extraction_method = "VLM"
        fallback_used = False

        if use_vlm:
            logger.info("Declaration extraction: running VLM pipeline for inspection %s", inspection_id)
            image_path = self._resolve_image_path(inspection_id)

            if not image_path:
                logger.error(
                    "Declaration extraction: primary image not found for %s",
                    inspection_id,
                )
                if not fallback_enabled:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="VLM_EXTRACTION_FAILED: Primary package image not found for inspection",
                    )
                fallback_used = True
            elif not self.vlm_extractor.is_configured():
                logger.error(
                    "Declaration extraction: VLM_API_KEY is not configured"
                )
                if not fallback_enabled:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="VLM_EXTRACTION_FAILED: VLM_API_KEY is not configured",
                    )
                fallback_used = True
            else:
                try:
                    vlm_result = self.vlm_extractor.extract_declarations(
                        image_source=image_path,
                        raw_full_text=ocr_result.raw_full_text,
                        regions=ocr_result.text_regions,
                    )
                    extracted_items = self._map_vlm_to_declarations(
                        vlm_result,
                        ocr_result.text_regions or [],
                        ocr_result.raw_full_text,
                    )
                    extraction_method = "VLM"
                    fallback_used = False
                    logger.info(
                        "VLM declaration extraction succeeded for inspection %s with %d declarations",
                        inspection_id,
                        len(extracted_items),
                    )
                except (VLMExtractionError, Exception) as exc:
                    logger.error(
                        "VLM declaration extraction failed for inspection %s: %s",
                        inspection_id,
                        str(exc),
                    )
                    if not fallback_enabled:
                        raise HTTPException(
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"VLM_EXTRACTION_FAILED: {str(exc)}",
                        )
                    fallback_used = True

        if not use_vlm or fallback_used:
            extraction_method = "SPATIAL_FALLBACK"
            fallback_used = True
            logger.info("Running spatial fallback extraction for inspection %s", inspection_id)
            extracted_items = self.spatial_extractor.extract(ocr_result)
            for item in extracted_items:
                item.extraction_method = "SPATIAL_FALLBACK"

        # Clear existing declarations for idempotency
        self.db.query(Declaration).filter(
            Declaration.inspection_id == inspection_id
        ).delete(synchronize_session=False)

        field_name_map = {
            "IMPORTER": "importer_details",
            "MANUFACTURER": "manufacturer_details",
            "PACKER": "packer_details",
            "CONSUMER_CARE": "consumer_care_details",
            "NET_QUANTITY": "net_quantity",
            "MRP": "mrp",
            "PRODUCT_NAME": "product_name",
            "BRAND": "brand",
            "MANUFACTURING_DATE": "manufacturing_date",
            "PACKING_DATE": "packing_date",
            "BEST_BEFORE": "best_before",
            "USE_BY": "use_by",
            "BATCH_LOT_NUMBER": "batch_lot_number",
            "COUNTRY_OF_ORIGIN": "country_of_origin",
        }

        # Persist extracted declarations to the database
        for item in extracted_items:
            f_name = field_name_map.get(item.declaration_type, item.declaration_type.lower())
            self.db.add(
                Declaration(
                    inspection_id=inspection_id,
                    field_name=f_name,
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
            extraction_method=extraction_method,
            fallback_used=fallback_used,
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

        method = declarations[0].extraction_method if declarations else None
        fallback_used = (method == "SPATIAL_FALLBACK") if method else False

        return DeclarationListResponse(
            inspection_id=inspection_id,
            declarations=[
                declaration_to_response(declaration) for declaration in declarations
            ],
            extraction_method=method,
            fallback_used=fallback_used,
        )

    def _resolve_image_path(self, inspection_id: str) -> Path | None:
        """Finds and resolves the local file path to the uploaded inspection image."""
        evidence = (
            self.db.query(Evidence)
            .filter(
                Evidence.inspection_id == inspection_id,
                Evidence.violation_id.is_(None),
            )
            .order_by(Evidence.created_at)
            .first()
        )
        if not evidence or not evidence.file_path:
            return None

        direct_path = Path(evidence.file_path)
        if direct_path.exists() and direct_path.is_file():
            return direct_path

        try:
            filename = direct_path.name
            upload_path = storage_service.get_upload_path(filename)
            if upload_path.exists():
                return upload_path
        except Exception:
            pass

        return None

    def _map_vlm_to_declarations(
        self,
        vlm_data: StandardDeclarationExtraction,
        regions: list[Any],
        raw_full_text: str | None,
    ) -> list[ExtractedDeclaration]:
        """Converts StandardDeclarationExtraction into internal ExtractedDeclaration objects

        with OCR evidence matching and confidence thresholding.
        """
        results: list[ExtractedDeclaration] = []

        field_mappings = [
            ("PRODUCT_NAME", vlm_data.product_name, "product_name"),
            ("BRAND", vlm_data.brand, "brand"),
            ("NET_QUANTITY", vlm_data.net_quantity, "net_quantity"),
            ("MRP", vlm_data.mrp, "mrp"),
            ("MANUFACTURING_DATE", vlm_data.date_of_manufacture, "manufacturing_date"),
            ("PACKING_DATE", vlm_data.date_of_packing, "packing_date"),
            ("BEST_BEFORE", vlm_data.best_before, "best_before"),
            ("USE_BY", vlm_data.use_by, "use_by"),
            ("CONSUMER_CARE", vlm_data.consumer_care_details, "consumer_care"),
            ("BATCH_LOT_NUMBER", vlm_data.batch_lot_number, "batch_lot_number"),
            ("COUNTRY_OF_ORIGIN", vlm_data.country_of_origin, "country_of_origin"),
        ]

        # 1. Process singular fields
        for decl_type, field, _ in field_mappings:
            decl = self._build_single_declaration(
                decl_type, field, regions, raw_full_text
            )
            if decl:
                results.append(decl)

        # 2. Process multi-component identity fields (Manufacturer, Packer, Importer)
        mfg_decl = self._build_identity_declaration(
            "MANUFACTURER",
            vlm_data.manufacturer_name,
            vlm_data.manufacturer_address,
            regions,
            raw_full_text,
        )
        if mfg_decl:
            results.append(mfg_decl)

        packer_decl = self._build_identity_declaration(
            "PACKER",
            vlm_data.packer_name,
            vlm_data.packer_address,
            regions,
            raw_full_text,
        )
        if packer_decl:
            results.append(packer_decl)

        importer_decl = self._build_identity_declaration(
            "IMPORTER",
            vlm_data.importer_name,
            vlm_data.importer_address,
            regions,
            raw_full_text,
        )
        if importer_decl:
            results.append(importer_decl)

        return results

    def _build_single_declaration(
        self,
        decl_type: str,
        field: DeclarationField,
        regions: list[Any],
        raw_full_text: str | None,
    ) -> ExtractedDeclaration:
        """Maps a single DeclarationField to an ExtractedDeclaration with evidence matching."""
        if field.status == "missing" and not field.value and not field.evidence:
            return ExtractedDeclaration(
                declaration_type=decl_type,
                value="—",
                normalized_value=None,
                unit=None,
                source_text="—",
                confidence=0.0,
                ocr_confidence=0.0,
                extraction_method="VLM",
                status="MISSING",
                ocr_text_region_id=None,
                ocr_text_region_ids=None,
            )

        # Evidence matching against OCR
        evidence_text = field.evidence or field.value or ""
        match_result = self.evidence_matcher.match_evidence(
            evidence_text, regions, raw_full_text
        )

        # Evaluate status based on confidence thresholds
        conf = field.confidence or 0.0
        verified_thresh = settings.VLM_CONFIDENCE_VERIFIED
        uncertain_thresh = settings.VLM_CONFIDENCE_UNCERTAIN

        if field.status == "found":
            if conf >= verified_thresh:
                status_str = "FOUND"
            elif conf >= uncertain_thresh:
                status_str = "UNCERTAIN"
            else:
                status_str = "UNCERTAIN"
        elif field.status == "uncertain":
            status_str = "UNCERTAIN"
        else:
            status_str = "INCOMPLETE" if not field.value else "UNCERTAIN"

        value_str = field.value
        unit_str = field.unit
        normalized_val = field.normalized_value

        # Field-specific normalization adjustments
        if decl_type == "MRP":
            if not unit_str:
                unit_str = "INR"
            if value_str:
                cleaned_num = re.sub(r"[^\d.]", "", value_str)
                try:
                    normalized_val = float(cleaned_num) if "." in cleaned_num else int(cleaned_num)
                except ValueError:
                    normalized_val = value_str

        elif decl_type == "NET_QUANTITY":
            if value_str:
                # If value contains unit (e.g. "500 g"), separate if unit_str is missing
                m = re.search(r"(?i)^([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z]+)?$", value_str.strip())
                if m:
                    value_str = m.group(1)
                    if not unit_str and m.group(2):
                        unit_str = m.group(2)
                if not normalized_val:
                    try:
                        normalized_val = float(value_str) if "." in value_str else int(value_str)
                    except ValueError:
                        normalized_val = value_str

        elif decl_type == "PRODUCT_NAME" and not normalized_val:
            normalized_val = value_str

        return ExtractedDeclaration(
            declaration_type=decl_type,
            value=value_str,
            normalized_value=normalized_val,
            unit=unit_str,
            source_text=evidence_text,
            confidence=conf,
            ocr_confidence=match_result.ocr_confidence,
            extraction_method="VLM",
            status=status_str,
            ocr_text_region_id=match_result.ocr_text_region_id,
            ocr_text_region_ids=match_result.ocr_text_region_ids or None,
        )

    def _build_identity_declaration(
        self,
        decl_type: str,
        name_field: DeclarationField,
        addr_field: DeclarationField,
        regions: list[Any],
        raw_full_text: str | None,
    ) -> ExtractedDeclaration:
        """Combines name and address components into a single identity declaration (e.g. MANUFACTURER)."""
        has_name = bool(name_field.status != "missing" and (name_field.value or name_field.evidence))
        has_addr = bool(addr_field.status != "missing" and (addr_field.value or addr_field.evidence))

        if not has_name and not has_addr:
            return ExtractedDeclaration(
                declaration_type=decl_type,
                value="—",
                normalized_value=None,
                unit=None,
                source_text="—",
                confidence=0.0,
                ocr_confidence=0.0,
                extraction_method="VLM",
                status="MISSING",
                ocr_text_region_id=None,
                ocr_text_region_ids=None,
            )

        # Build combined value
        name_val = (name_field.value or "").strip()
        addr_val = (addr_field.value or "").strip()
        if name_val and addr_val:
            combined_value = f"{name_val}, {addr_val}"
        else:
            combined_value = name_val or addr_val

        # Build combined evidence
        name_ev = (name_field.evidence or "").strip()
        addr_ev = (addr_field.evidence or "").strip()
        if name_ev and addr_ev:
            combined_evidence = f"{name_ev} {addr_ev}"
        else:
            combined_evidence = name_ev or addr_ev or combined_value

        # Calculate confidence
        conf_candidates = []
        if has_name:
            conf_candidates.append(name_field.confidence or 0.0)
        if has_addr:
            conf_candidates.append(addr_field.confidence or 0.0)
        conf = sum(conf_candidates) / len(conf_candidates) if conf_candidates else 0.0

        # Match evidence to OCR
        match_result = self.evidence_matcher.match_evidence(
            combined_evidence, regions, raw_full_text
        )

        verified_thresh = settings.VLM_CONFIDENCE_VERIFIED
        uncertain_thresh = settings.VLM_CONFIDENCE_UNCERTAIN

        any_uncertain = (name_field.status == "uncertain" or addr_field.status == "uncertain")
        if any_uncertain or conf < uncertain_thresh:
            status_str = "UNCERTAIN"
        elif conf >= verified_thresh:
            status_str = "FOUND"
        else:
            status_str = "UNCERTAIN"

        return ExtractedDeclaration(
            declaration_type=decl_type,
            value=combined_value or None,
            normalized_value=combined_value or None,
            unit=None,
            source_text=combined_evidence,
            confidence=conf,
            ocr_confidence=match_result.ocr_confidence,
            extraction_method="VLM",
            status=status_str,
            ocr_text_region_id=match_result.ocr_text_region_id,
            ocr_text_region_ids=match_result.ocr_text_region_ids or None,
        )


def declaration_to_response(declaration: Declaration) -> DeclarationResponse:
    return DeclarationResponse.model_validate(declaration)
