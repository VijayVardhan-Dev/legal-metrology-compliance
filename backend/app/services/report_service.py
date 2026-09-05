"""Evidence-backed inspection report generation."""
from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone
import os

from fastapi import HTTPException, status
from PIL import Image, ImageDraw
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image as PdfImage, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.compliance_run import ComplianceRun
from app.models.declaration import Declaration
from app.models.evidence import Evidence
from app.models.inspection import Inspection
from app.models.ocr_result import OCRResult
from app.models.product_category import ProductCategory
from app.models.report import Report
from app.models.rule_result import RuleResult
from app.models.visual_analysis import VisualAnalysis
from app.schemas.report import ReportResponse
from app.services.storage_service import storage_service


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.report_dir = Path(settings.STORAGE_PATH) / "reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, inspection_id: str) -> ReportResponse:
        data = self._load(inspection_id)
        report_number = self._next_report_number()
        target = self.report_dir / f"{report_number}.pdf"
        try:
            self._build_pdf(target, report_number, data)
            report = self._upsert_report(report_number, target, data)
            self.db.commit()
            self.db.refresh(report)
            return ReportResponse.from_model(report)
        except HTTPException:
            self.db.rollback()
            self._remove_file(target)
            raise
        except Exception as exc:
            self.db.rollback()
            self._remove_file(target)
            raise HTTPException(status_code=500, detail=f"Unable to generate inspection report: {exc}") from exc

    def latest(self, inspection_id: str) -> ReportResponse:
        return ReportResponse.from_model(self.report_model(inspection_id))

    def report_model(self, inspection_id: str) -> Report:
        report = self.db.query(Report).filter(Report.inspection_id == inspection_id).order_by(Report.created_at.desc()).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return report

    def _load(self, inspection_id):
        inspection = self.db.query(Inspection).filter(Inspection.id == inspection_id).first()
        if not inspection:
            raise HTTPException(status_code=404, detail="Inspection not found")
        run = self.db.query(ComplianceRun).filter(ComplianceRun.inspection_id == inspection_id).first()
        if not run:
            raise HTTPException(status_code=409, detail="Compliance has not been evaluated for this inspection")
        ocr = self.db.query(OCRResult).filter(OCRResult.inspection_id == inspection_id).first()
        visual = self.db.query(VisualAnalysis).filter(VisualAnalysis.inspection_id == inspection_id).first()
        category = self.db.query(ProductCategory).filter(ProductCategory.inspection_id == inspection_id).first()
        declarations = self.db.query(Declaration).filter(Declaration.inspection_id == inspection_id).order_by(Declaration.created_at, Declaration.id).all()
        results = self.db.query(RuleResult).filter(RuleResult.inspection_id == inspection_id).order_by(RuleResult.rule_id).all()
        evidence = self.db.query(Evidence).filter(Evidence.inspection_id == inspection_id, Evidence.violation_id.is_(None)).first()
        if not evidence:
            raise HTTPException(status_code=409, detail="Original inspection image is unavailable")
        try:
            storage_service.get_upload_path(os.path.basename(evidence.file_path))
        except HTTPException as exc:
            raise HTTPException(status_code=409, detail="Original inspection image is unavailable") from exc
        return {"inspection": inspection, "run": run, "ocr": ocr, "visual": visual, "category": category, "declarations": declarations, "results": results, "evidence": evidence}

    def _next_report_number(self):
        value = self.db.execute(text("SELECT nextval('lm_report_number_seq')")).scalar_one()
        return f"LM-{datetime.now(timezone.utc).year}-{value:06d}"

    def _upsert_report(self, report_number, target, data):
        run = data["run"]
        previous = self.db.query(Report).filter(Report.inspection_id == data["inspection"].id, Report.compliance_run_id == run.id).order_by(Report.created_at.desc()).first()
        if previous and Path(previous.file_path).exists():
            self._remove_file(target)
            return previous
        report = Report(
            inspection_id=data["inspection"].id, file_path=str(target), report_number=report_number,
            report_status="COMPLETED", overall_compliance_status=run.overall_status,
            overall_confidence=run.overall_confidence, compliance_run_id=run.id,
            rule_engine_version=run.rule_engine_version, classification_version=run.classification_version,
            ocr_result_id=run.ocr_result_id, visual_analysis_id=run.visual_analysis_id, report_type="pdf",
        )
        self.db.add(report)
        return report

    def _build_pdf(self, target, report_number, data):
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], alignment=TA_CENTER, spaceAfter=8))
        styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], textColor=colors.HexColor("#1f3b5b"), spaceBefore=10))
        styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
        doc = SimpleDocTemplate(str(target), pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm, topMargin=14 * mm, bottomMargin=14 * mm, pageCompression=0)
        story = [Paragraph("Legal Metrology Inspection Report", styles["ReportTitle"]), Paragraph(f"<b>{report_number}</b><br/>Generated: {self._date(data['run'].evaluated_at)}", styles["Normal"]), Spacer(1, 8)]
        story.extend(self._section("Inspection information", [["Inspection ID", data["inspection"].id], ["Inspection date/time", self._date(data["inspection"].created_at)], ["Image dimensions", self._dimensions(data["ocr"], data["visual"])], ["Image quality", getattr(data["visual"], "quality_status", None) or "Not detected / Not available"]]))
        story.extend(self._section("Product information", self._product_rows(data["inspection"].product, data["declarations"], data["category"])))
        run = data["run"]
        story.extend(self._section("Compliance summary", [["Overall status", run.overall_status], ["Overall confidence", self._confidence(run.overall_confidence)], ["Total rules", run.total_rules], ["Compliant", run.compliant_rules], ["Non-compliant", run.non_compliant_rules], ["Review required", run.review_required_rules], ["Not applicable", run.not_applicable_rules]]))
        story.append(Paragraph("Rule findings", styles["Section"]))
        for result in data["results"]:
            story.extend(self._rule_block(result, data, styles))
        review = [result for result in data["results"] if result.status == "REVIEW_REQUIRED"]
        story.append(Paragraph("Review required", styles["Section"]))
        if review:
            for result in review:
                story.append(Paragraph(f"<b>{result.rule_id} - {result.rule_name}</b>: {self._safe(result.reason)}", styles["BodyText"]))
        else:
            story.append(Paragraph("No review-required findings.", styles["BodyText"]))
        story.append(Paragraph("Disclaimer", styles["Section"]))
        story.append(Paragraph("This report is generated by an AI-assisted inspection and screening tool. It presents extracted facts, evidence, and deterministic rule evaluations. Final legal determination remains with the authorized inspecting authority.", styles["BodyText"]))
        doc.build(story)

    def _rule_block(self, result, data, styles):
        rows = [["Rule", f"{result.rule_id} - {result.rule_name}"], ["Legal reference", result.legal_reference], ["Applicability", result.applicability_status], ["Status", result.status], ["Severity", result.severity], ["Confidence", self._confidence(result.confidence)], ["Reason", result.reason], ["Warnings", "; ".join(result.warnings or []) or "None"]]
        story = [Table(rows, colWidths=[35 * mm, 145 * mm], style=self._table_style())]
        for item in self._evidence_for_result(result, data):
            story.append(Spacer(1, 3))
            story.append(Paragraph(f"Evidence: {self._safe(item['declaration_type'])} | Value: {self._safe(item['value'])} | Source: {self._safe(item['source_text'])} | OCR confidence: {self._confidence(item['ocr_confidence'])} | Visual status: {self._safe(item['visual_status'])}", styles["Small"]))
            crop = self._crop(data["evidence"], item["bbox"], item["declaration_type"], result.rule_id)
            story.append(PdfImage(crop, width=70 * mm, height=45 * mm, kind="proportional") if crop else Paragraph("Evidence image unavailable", styles["Small"]))
        story.append(Spacer(1, 7))
        return [KeepTogether(story)]

    def _evidence_for_result(self, result, data):
        declarations = {item.id: item for item in data["declarations"]}
        regions = {region.id: region for region in (data["ocr"].text_regions if data["ocr"] else [])}
        output = []
        for declaration_id in result.declaration_ids or []:
            declaration = declarations.get(declaration_id)
            if not declaration:
                continue
            region = regions.get(declaration.ocr_text_region_id)
            output.append({"declaration_type": declaration.declaration_type, "value": declaration.value or "Not detected / Not available", "source_text": declaration.source_text or "Not detected / Not available", "ocr_confidence": declaration.ocr_confidence, "visual_status": self._visual_status(data["visual"], declaration.id), "bbox": self._bbox(region)})
        return output

    @staticmethod
    def _visual_status(visual, declaration_id):
        for item in (visual.declarations if visual else []) or []:
            if item.get("declaration_id") == declaration_id:
                return item.get("status")
        return "Not detected / Not available"

    @staticmethod
    def _bbox(region):
        if not region or None in (region.bbox_x, region.bbox_y, region.bbox_width, region.bbox_height) or region.bbox_x < 0 or region.bbox_y < 0 or region.bbox_width <= 0 or region.bbox_height <= 0:
            return None
        return {"x": region.bbox_x, "y": region.bbox_y, "width": region.bbox_width, "height": region.bbox_height}

    def _crop(self, evidence, bbox, declaration_type, rule_id):
        if not bbox:
            return None
        try:
            image = Image.open(storage_service.get_upload_path(os.path.basename(evidence.file_path))).convert("RGB")
            right, bottom = min(image.width, bbox["x"] + bbox["width"]), min(image.height, bbox["y"] + bbox["height"])
            if bbox["x"] >= right or bbox["y"] >= bottom:
                return None
            crop = image.crop((bbox["x"], bbox["y"], right, bottom))
            draw = ImageDraw.Draw(crop)
            draw.rectangle((0, 0, crop.width - 1, crop.height - 1), outline="red", width=3)
            draw.text((4, 4), f"{rule_id} / {declaration_type}", fill="red")
            stream = BytesIO()
            crop.save(stream, format="PNG")
            stream.seek(0)
            return stream
        except (OSError, ValueError, HTTPException):
            return None

    @staticmethod
    def _section(title, rows):
        return [Paragraph(title, getSampleStyleSheet()["Heading2"]), Table(rows, colWidths=[45 * mm, 135 * mm], style=ReportService._table_style())]

    @staticmethod
    def _table_style():
        return TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef3f8")), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b8c4d0")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 5)])

    @staticmethod
    def _product_rows(product, declarations, category):
        by_type = {}
        for declaration in declarations:
            if declaration.value:
                by_type.setdefault(declaration.declaration_type, []).append(declaration.value)
        fields = [("Product name", product.name), ("Category", getattr(category, "category", None) or product.category), ("Subcategory", getattr(category, "subcategory", None)), ("Manufacturer / packer / importer", " / ".join(sum((by_type.get(key, []) for key in ("MANUFACTURER", "PACKER", "IMPORTER")), []))), ("Net quantity", " ".join(by_type.get("NET_QUANTITY", []))), ("MRP", " ".join(by_type.get("MRP", []))), ("Batch / lot", " ".join(by_type.get("BATCH_LOT_NUMBER", []))), ("Manufacturing / packing date", " ".join(by_type.get("MANUFACTURING_DATE", []) + by_type.get("PACKING_DATE", []))), ("Best-before", " ".join(by_type.get("BEST_BEFORE", []))), ("Use-by / expiry", " ".join(by_type.get("USE_BY", []))), ("Consumer care", " ".join(by_type.get("CONSUMER_CARE", []))), ("Country of origin", " ".join(by_type.get("COUNTRY_OF_ORIGIN", [])))]
        return [[label, value or "Not detected / Not available"] for label, value in fields]

    @staticmethod
    def _dimensions(ocr, visual):
        width, height = getattr(ocr, "image_width", None) or getattr(visual, "image_width", None), getattr(ocr, "image_height", None) or getattr(visual, "image_height", None)
        return f"{width} x {height}" if width and height else "Not detected / Not available"

    @staticmethod
    def _date(value):
        return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if value else "Not detected / Not available"

    @staticmethod
    def _confidence(value):
        return f"{value * 100:.1f}%" if value is not None else "Not detected / Not available"

    @staticmethod
    def _safe(value):
        return str(value or "Not detected / Not available").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @staticmethod
    def _remove_file(path):
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass
