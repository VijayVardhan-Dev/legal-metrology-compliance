"""Deterministic image-quality and OCR-region visibility analysis."""
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageStat, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.models.declaration import Declaration
from app.models.evidence import Evidence
from app.models.inspection import Inspection
from app.models.ocr_text_region import OCRTextRegion
from app.models.visual_analysis import VisualAnalysis
from app.schemas.visual_analysis import VisualAnalysisRequest
from app.services.storage_service import storage_service

try:
    import cv2
except ImportError:  # pragma: no cover - Pillow fallback is supported
    cv2 = None


class VisualAnalysisService:
    def __init__(self, db: Session):
        self.db = db

    def analyze(self, inspection_id: str, request: VisualAnalysisRequest | None = None) -> VisualAnalysis:
        inspection = self.db.query(Inspection).filter(Inspection.id == inspection_id).first()
        if not inspection:
            raise ValueError("Inspection not found")
        evidence = self.db.query(Evidence).filter(
            Evidence.inspection_id == inspection_id, Evidence.violation_id.is_(None)
        ).order_by(Evidence.created_at).first()
        if not evidence:
            raise ValueError("Image evidence not found for this inspection")

        existing = self.db.query(VisualAnalysis).filter(
            VisualAnalysis.inspection_id == inspection_id
        ).first()
        if existing:
            self.db.delete(existing)
            self.db.flush()

        path = Path(evidence.file_path)
        if not path.exists():
            path = storage_service.get_upload_path(path.name)
        try:
            image = Image.open(path).convert("RGB")
        except (OSError, UnidentifiedImageError) as exc:
            result = VisualAnalysis(
                inspection_id=inspection_id,
                evidence_id=evidence.id,
                status="REVIEW_REQUIRED",
                quality_status="REVIEW_REQUIRED",
                processing_status="FAILED",
                metrics={},
                visibility_flags={},
                findings=[],
                declarations=[],
                error_message=f"Unable to analyse inspection image: {exc}",
                warnings=["The image could not be decoded for visual analysis."],
            )
            self.db.add(result)
            self.db.commit()
            self.db.refresh(result)
            return result
        width, height = image.size
        gray = np.asarray(image.convert("L"), dtype=np.float32)
        stat = ImageStat.Stat(image)
        brightness = float(np.mean(gray))
        contrast = float(np.std(gray))
        sharpness = self._sharpness(gray)
        blur_score = sharpness
        quality = self._quality_score(width, height, contrast, sharpness)
        brightness_score = max(0.0, 1.0 - abs(brightness - 128.0) / 128.0)
        contrast_score = min(1.0, contrast / 45.0)
        glare_fraction = float(np.mean(gray >= 250))
        quality_status = (
            "GOOD" if quality >= 0.70 else
            "POOR" if quality < 0.40 else
            "REVIEW_REQUIRED"
        )
        warnings = []
        if min(width, height) < 800:
            warnings.append("Image resolution may be insufficient for reliable visual assessment.")
        if blur_score < 30:
            warnings.append("Image sharpness is low; text visibility may be unreliable.")
        if brightness < 45:
            warnings.append("Image is dark or underexposed.")
        elif brightness > 220:
            warnings.append("Image is bright or overexposed.")
        if contrast < 20:
            warnings.append("Image contrast is low.")
        if glare_fraction > 0.01:
            warnings.append("Possible glare or overexposed regions detected.")
        orientation = "LANDSCAPE" if width > height else "PORTRAIT" if height > width else "SQUARE"

        declarations = self.db.query(Declaration).filter(
            Declaration.inspection_id == inspection_id
        ).order_by(Declaration.created_at, Declaration.id).all()
        flags: dict[str, Any] = {}
        declaration_results: list[dict[str, Any]] = []
        findings: list[dict[str, Any]] = []
        prior_regions: list[tuple[str, dict[str, int]]] = []
        for declaration in declarations:
            region = self._region_for(declaration)
            key = declaration.id
            flag = self._visibility(region, declaration, width, height, quality)
            bbox = flag["bbox"]
            if all(value is not None for value in bbox.values()):
                for prior_id, prior_bbox in prior_regions:
                    if self._boxes_overlap(bbox, prior_bbox):
                        flag["uncertain"] = True
                        flag["visible"] = False
                        flag["flag"] = "PARTIALLY_OBSCURED"
                        flag["reason"] = f"OCR region overlaps declaration region {prior_id}."
                        break
                prior_regions.append((declaration.id, bbox))
            flags[key] = flag
            flags.setdefault(declaration.declaration_type, flag)
            declaration_results.append({
                "declaration_id": declaration.id,
                "declaration_type": declaration.declaration_type,
                "status": flag["flag"],
                "visibility": "YES" if flag["visible"] else "REVIEW_REQUIRED",
                "detected": True,
                "visible": flag["visible"],
                "partially_cropped": flag["partially_cropped"],
                "ocr_region_ids": [declaration.ocr_text_region_id] if declaration.ocr_text_region_id else [],
                "relative_text_height": flag["relative_text_height"],
                "relative_text_area": flag["relative_text_area"],
                "evidence": self._declaration_evidence(declaration, region, width, height),
            })
            if flag["uncertain"]:
                findings.append({
                    "finding_type": "DECLARATION_VISIBILITY",
                    "status": "REVIEW_REQUIRED",
                    "message": flag["reason"],
                    "declaration_id": declaration.id,
                    "declaration_type": declaration.declaration_type,
                    "evidence": self._declaration_evidence(declaration, region, width, height),
                })

        if quality_status != "GOOD":
            findings.append({
                "finding_type": "IMAGE_QUALITY",
                "status": "REVIEW_REQUIRED",
                "message": "Image quality is insufficient to make a reliable visual determination.",
                "evidence": {"metrics": {"quality_score": quality}},
            })
        flags["_summary"] = {
            "image_quality_ok": quality >= 0.60,
            "declarations_checked": len(declarations),
            "uncertain_count": sum(
                1 for finding in findings if finding["status"] == "REVIEW_REQUIRED"
            ),
        }
        calibration = self._calibration(request)
        result = VisualAnalysis(
            inspection_id=inspection_id,
            evidence_id=evidence.id,
            status="REVIEW_REQUIRED" if findings else "COMPLIANT",
            processing_status="COMPLETED",
            quality_status=quality_status,
            image_width=width,
            image_height=height,
            quality_score=quality,
            metrics={
                "brightness_mean": round(brightness, 4),
                "brightness_std": round(float(np.std(gray)), 4),
                "contrast": round(contrast, 4),
                "brightness_score": round(brightness_score, 4),
                "contrast_score": round(contrast_score, 4),
                "sharpness": round(sharpness, 4),
                "blur_score": round(blur_score, 4),
                "quality_score": quality,
                "channel_means": [round(float(x), 4) for x in stat.mean],
                "declaration_count": len(declarations),
                "orientation": orientation,
                "skew": {"status": "NOT_ESTIMATED", "method": "OCR-region analysis does not infer camera skew."},
                "glare_fraction": round(glare_fraction, 6),
            },
            visibility_flags=flags,
            findings=findings,
            warnings=warnings,
            declarations=declaration_results,
            calibration=calibration,
            evidence={"evidence_id": evidence.id, "file_path": evidence.file_path},
        )
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result

    def get(self, inspection_id: str) -> VisualAnalysis | None:
        return self.db.query(VisualAnalysis).filter(
            VisualAnalysis.inspection_id == inspection_id
        ).first()

    @staticmethod
    def _sharpness(gray: np.ndarray) -> float:
        if cv2 is not None:
            # OpenCV does not support converting float32 input to float64 here.
            return float(cv2.Laplacian(gray.astype(np.float64), cv2.CV_64F).var())
        # A finite-difference fallback keeps the service usable without OpenCV.
        return float(np.var(np.diff(gray, axis=0)) + np.var(np.diff(gray, axis=1)))

    @staticmethod
    def _quality_score(width: int, height: int, contrast: float, sharpness: float) -> float:
        resolution = min(1.0, min(width, height) / 800.0)
        contrast_score = min(1.0, contrast / 45.0)
        sharpness_score = min(1.0, sharpness / 180.0)
        return round(max(0.0, min(1.0, 0.2 * resolution + 0.35 * contrast_score + 0.45 * sharpness_score)), 4)

    def _region_for(self, declaration: Declaration) -> OCRTextRegion | None:
        if not declaration.ocr_text_region_id:
            return None
        return self.db.query(OCRTextRegion).filter(
            OCRTextRegion.id == declaration.ocr_text_region_id
        ).first()

    @staticmethod
    def _visibility(region, declaration, width: int, height: int, quality: float) -> dict[str, Any]:
        confidence = declaration.ocr_confidence if declaration.ocr_confidence is not None else declaration.confidence
        x = getattr(region, "bbox_x", None)
        y = getattr(region, "bbox_y", None)
        w = getattr(region, "bbox_width", None)
        h = getattr(region, "bbox_height", None)
        reasons = []
        partially_cropped = False
        near_boundary = False
        if region is None or None in (x, y, w, h) or w <= 0 or h <= 0:
            reasons.append("No normalized OCR region is available.")
        elif x < 0 or y < 0 or x + w > width or y + h > height:
            reasons.append("OCR region is outside the image bounds.")
            partially_cropped = True
        elif x <= width * 0.02 or y <= height * 0.02 or x + w >= width * 0.98 or y + h >= height * 0.98:
            near_boundary = True
            reasons.append("OCR region is near an image boundary.")
        relative_text_height = (h / height * 100.0) if h and height else None
        relative_text_area = (w * h / (width * height) * 100.0) if w and h and width and height else None
        if relative_text_height is not None and relative_text_height < 1.0:
            reasons.append("Declaration text is very small relative to the image.")
        if confidence is not None and confidence < 0.60:
            reasons.append("OCR confidence is below the visual-analysis threshold.")
        if quality < 0.60:
            reasons.append("Image quality is below the visual-analysis threshold.")
        flag = (
            "CROPPED" if partially_cropped else
            "SMALL" if relative_text_height is not None and relative_text_height < 1.0 else
            "REVIEW_REQUIRED" if near_boundary else
            "LOW_CONFIDENCE" if confidence is not None and confidence < 0.60 else
            "REVIEW_REQUIRED" if reasons else
            "CLEAR"
        )
        return {
            "visible": not reasons,
            "uncertain": bool(reasons),
            "flag": flag,
            "partially_cropped": partially_cropped,
            "near_boundary": near_boundary,
            "ocr_confidence": confidence,
            "bbox": {"x": x, "y": y, "width": w, "height": h},
            "pixel_dimensions": {"width": w, "height": h},
            "relative_text_height": relative_text_height,
            "relative_text_area": relative_text_area,
            "reason": " ".join(reasons) if reasons else "Region is visible with adequate image quality.",
        }

    @staticmethod
    def _declaration_evidence(declaration, region, width, height):
        return {
            "declaration_id": declaration.id,
            "ocr_text_region_id": declaration.ocr_text_region_id,
            "source_text": declaration.source_text,
            "image_width": width,
            "image_height": height,
            "bbox": {
                "x": getattr(region, "bbox_x", None), "y": getattr(region, "bbox_y", None),
                "width": getattr(region, "bbox_width", None), "height": getattr(region, "bbox_height", None),
            },
        }

    @staticmethod
    def _boxes_overlap(first: dict[str, int], second: dict[str, int]) -> bool:
        return (
            first["x"] < second["x"] + second["width"]
            and first["x"] + first["width"] > second["x"]
            and first["y"] < second["y"] + second["height"]
            and first["y"] + first["height"] > second["y"]
        )

    @staticmethod
    def _calibration(request):
        if not request or not request.calibration:
            return None
        values = request.calibration.model_dump(exclude_none=True)
        if "pixels_per_mm" not in values and {"reference_length_mm", "reference_pixels"} <= values.keys():
            values["pixels_per_mm"] = values["reference_pixels"] / values["reference_length_mm"]
        return values
