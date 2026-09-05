from datetime import datetime
from math import ceil

from fastapi import HTTPException
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.compliance_run import ComplianceRun
from app.models.declaration import Declaration
from app.models.inspection import Inspection
from app.models.ocr_result import OCRResult
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.report import Report
from app.models.rule_result import RuleResult
from app.models.visual_analysis import VisualAnalysis
from app.schemas.history import (
    CategoryDistribution,
    CategoryDistributionItem,
    ComplianceDistribution,
    ComplianceDistributionItem,
    DashboardSummary,
    InspectionHistoryItem,
    InspectionHistoryResponse,
    RecentInspection,
    RuleStatistics,
    RuleStatisticsItem,
)


COMPLIANCE_STATUSES = {"COMPLIANT", "NON_COMPLIANT", "REVIEW_REQUIRED"}
SORT_COLUMNS = {
    "created_at": Inspection.created_at,
    "updated_at": Inspection.updated_at,
    "product_name": Product.name,
    "compliance_status": ComplianceRun.overall_status,
    "overall_confidence": ComplianceRun.overall_confidence,
}


def _date_filters(query, date_from: datetime | None, date_to: datetime | None):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must be before or equal to date_to")
    if date_from:
        query = query.filter(Inspection.created_at >= date_from)
    if date_to:
        query = query.filter(Inspection.created_at <= date_to)
    return query


def _category_expression():
    return func.coalesce(ProductCategory.category, Product.category, "UNKNOWN")


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def history(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None,
        compliance_status: str | None,
        category: str | None,
        subcategory: str | None,
        product_name: str | None,
        report_number: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        minimum_confidence: float | None,
        maximum_confidence: float | None,
        search: str | None,
        sort_by: str,
        sort_order: str,
    ) -> InspectionHistoryResponse:
        if status and status not in {
            "PENDING", "PROCESSING", "COMPLIANT", "NON_COMPLIANT", "REVIEW_REQUIRED"
        }:
            raise HTTPException(status_code=422, detail="Invalid inspection status")
        if compliance_status and compliance_status not in COMPLIANCE_STATUSES:
            raise HTTPException(status_code=422, detail="Invalid compliance_status")
        if sort_by not in SORT_COLUMNS:
            raise HTTPException(status_code=422, detail="Invalid sort_by")
        if sort_order not in {"asc", "desc"}:
            raise HTTPException(status_code=422, detail="sort_order must be asc or desc")
        if minimum_confidence is not None and maximum_confidence is not None and minimum_confidence > maximum_confidence:
            raise HTTPException(status_code=422, detail="minimum_confidence must be <= maximum_confidence")

        base = (
            self.db.query(Inspection.id)
            .join(Product, Product.id == Inspection.product_id)
            .outerjoin(ProductCategory, ProductCategory.inspection_id == Inspection.id)
            .outerjoin(ComplianceRun, ComplianceRun.inspection_id == Inspection.id)
        )
        base = _date_filters(base, date_from, date_to)
        if status:
            base = base.filter(Inspection.status == status)
        if compliance_status:
            base = base.filter(ComplianceRun.overall_status == compliance_status)
        if category:
            base = base.filter(_category_expression().ilike(category))
        if subcategory:
            base = base.filter(ProductCategory.subcategory.ilike(subcategory))
        if product_name:
            base = base.filter(Product.name.ilike(f"%{product_name}%"))
        if report_number:
            base = base.filter(
                self._latest_report_exists(report_number)
            )
        if minimum_confidence is not None:
            base = base.filter(ComplianceRun.overall_confidence >= minimum_confidence)
        if maximum_confidence is not None:
            base = base.filter(ComplianceRun.overall_confidence <= maximum_confidence)
        if search:
            term = f"%{search}%"
            base = base.filter(
                or_(
                    Product.name.ilike(term),
                    Product.brand.ilike(term),
                    Inspection.id.ilike(term),
                    self._latest_report_number().ilike(term),
                )
            )
        filtered_ids = base.with_entities(Inspection.id).distinct().subquery()
        filtered_id_select = select(filtered_ids.c.id)
        total = self.db.query(func.count()).select_from(filtered_ids).scalar() or 0

        query = (
            self.db.query(
                Inspection,
                Product.name.label("product_name"),
                func.coalesce(ProductCategory.category, Product.category, "UNKNOWN").label("category"),
                ProductCategory.subcategory.label("subcategory"),
                ComplianceRun.overall_status.label("overall_status"),
                ComplianceRun.overall_confidence.label("overall_confidence"),
                OCRResult.status.label("ocr_status"),
                VisualAnalysis.processing_status.label("visual_status"),
                func.count(func.distinct(Declaration.id)).label("declaration_count"),
                func.count(func.distinct(case((RuleResult.status == "COMPLIANT", RuleResult.id)))).label("compliant_count"),
                func.count(func.distinct(case((RuleResult.status == "NON_COMPLIANT", RuleResult.id)))).label("non_compliant_count"),
                func.count(func.distinct(case((RuleResult.status == "REVIEW_REQUIRED", RuleResult.id)))).label("review_count"),
                self._latest_report_number().label("report_number"),
                self._latest_report_status().label("report_status"),
            )
            .join(Product, Product.id == Inspection.product_id)
            .outerjoin(ProductCategory, ProductCategory.inspection_id == Inspection.id)
            .outerjoin(ComplianceRun, ComplianceRun.inspection_id == Inspection.id)
            .outerjoin(OCRResult, OCRResult.inspection_id == Inspection.id)
            .outerjoin(VisualAnalysis, VisualAnalysis.inspection_id == Inspection.id)
            .outerjoin(Declaration, Declaration.inspection_id == Inspection.id)
            .outerjoin(RuleResult, RuleResult.inspection_id == Inspection.id)
            .filter(Inspection.id.in_(filtered_id_select))
            .group_by(
                Inspection.id, Product.name, ProductCategory.category,
                Product.category, ProductCategory.subcategory,
                ComplianceRun.overall_status, ComplianceRun.overall_confidence,
                OCRResult.status, VisualAnalysis.processing_status,
            )
        )
        sort_column = SORT_COLUMNS[sort_by]
        query = query.order_by(sort_column.asc() if sort_order == "asc" else sort_column.desc())
        rows = query.offset((page - 1) * page_size).limit(page_size).all()
        items = [self._history_item(row) for row in rows]
        return InspectionHistoryResponse(
            items=items, page=page, page_size=page_size, total=total,
            total_pages=ceil(total / page_size) if total else 0,
        )

    def _latest_report_number(self):
        latest = (
            self.db.query(Report.report_number)
            .filter(Report.inspection_id == Inspection.id)
            .order_by(Report.created_at.desc(), Report.id.desc())
            .limit(1)
            .correlate(Inspection)
            .scalar_subquery()
        )
        return latest

    def _latest_report_status(self):
        latest = (
            self.db.query(Report.report_status)
            .filter(Report.inspection_id == Inspection.id)
            .order_by(Report.created_at.desc(), Report.id.desc())
            .limit(1)
            .correlate(Inspection)
            .scalar_subquery()
        )
        return latest

    def _latest_report_exists(self, report_number):
        return self.db.query(Report.id).filter(
            Report.inspection_id == Inspection.id,
            Report.report_number.ilike(f"%{report_number}%"),
        ).exists()

    @staticmethod
    def _history_item(row):
        inspection = row[0]
        return InspectionHistoryItem(
            inspection_id=inspection.id,
            inspection_date=inspection.created_at,
            product_name=row.product_name,
            category=row.category or "UNKNOWN",
            subcategory=row.subcategory,
            overall_compliance_status=row.overall_status,
            overall_confidence=row.overall_confidence,
            report_number=row.report_number,
            report_status=row.report_status,
            ocr_status=row.ocr_status,
            visual_analysis_status=row.visual_status,
            declaration_count=int(row.declaration_count or 0),
            compliant_rule_count=int(row.compliant_count or 0),
            non_compliant_rule_count=int(row.non_compliant_count or 0),
            review_required_rule_count=int(row.review_count or 0),
            created_at=inspection.created_at,
            updated_at=inspection.updated_at,
        )

    def _filtered_inspection_query(self, date_from, date_to, category):
        query = (
            self.db.query(Inspection.id)
            .join(Product, Product.id == Inspection.product_id)
            .outerjoin(ProductCategory, ProductCategory.inspection_id == Inspection.id)
        )
        query = _date_filters(query, date_from, date_to)
        if category:
            query = query.filter(_category_expression().ilike(category))
        return query.distinct()

    def summary(self, date_from, date_to, category) -> DashboardSummary:
        ids = self._filtered_inspection_query(date_from, date_to, category).subquery()
        id_select = select(ids.c.id)
        total = self.db.query(func.count()).select_from(ids).scalar() or 0
        counts = dict(
            self.db.query(ComplianceRun.overall_status, func.count())
            .filter(ComplianceRun.inspection_id.in_(id_select))
            .group_by(ComplianceRun.overall_status)
            .all()
        )
        avg_conf = self.db.query(func.avg(ComplianceRun.overall_confidence)).filter(
            ComplianceRun.inspection_id.in_(id_select)
        ).scalar()
        avg_ocr = self.db.query(func.avg(OCRResult.average_confidence)).filter(
            OCRResult.inspection_id.in_(id_select), OCRResult.status == "COMPLETED"
        ).scalar()
        reports = self.db.query(func.count(Report.id)).filter(Report.inspection_id.in_(id_select)).scalar() or 0
        return DashboardSummary(
            total_inspections=total,
            compliant_inspections=counts.get("COMPLIANT", 0),
            non_compliant_inspections=counts.get("NON_COMPLIANT", 0),
            review_required_inspections=counts.get("REVIEW_REQUIRED", 0),
            inspections_without_completed_compliance=total - sum(counts.values()),
            average_compliance_confidence=round(float(avg_conf), 4) if avg_conf is not None else None,
            average_ocr_confidence=round(float(avg_ocr), 4) if avg_ocr is not None else None,
            reports_generated=reports,
            inspections_in_date_range=total,
        )

    def compliance_distribution(self, date_from, date_to, category):
        ids = self._filtered_inspection_query(date_from, date_to, category).subquery()
        id_select = select(ids.c.id)
        rows = self.db.query(ComplianceRun.overall_status, func.count()).filter(
            ComplianceRun.inspection_id.in_(id_select)
        ).group_by(ComplianceRun.overall_status).all()
        counts = {status: count for status, count in rows}
        return ComplianceDistribution(items=[
            ComplianceDistributionItem(status=status, count=counts.get(status, 0))
            for status in ("COMPLIANT", "NON_COMPLIANT", "REVIEW_REQUIRED", "NOT_APPLICABLE")
        ])

    def category_distribution(self, date_from, date_to, category):
        category_value = func.coalesce(ProductCategory.category, Product.category)
        query = (
            self.db.query(
                category_value.label("category"),
                ProductCategory.subcategory,
                func.count(func.distinct(Inspection.id)),
            )
            .join(Product, Product.id == Inspection.product_id)
            .outerjoin(ProductCategory, ProductCategory.inspection_id == Inspection.id)
        )
        query = _date_filters(query, date_from, date_to)
        if category:
            query = query.filter(_category_expression().ilike(category))
        rows = query.group_by(
            ProductCategory.category, Product.category, ProductCategory.subcategory
        ).order_by(
            category_value, ProductCategory.subcategory
        ).all()
        return CategoryDistribution(items=[
            CategoryDistributionItem(category=cat or "UNKNOWN", subcategory=subcat, inspection_count=count)
            for cat, subcat, count in rows
        ])

    def rule_statistics(self, date_from, date_to, category):
        ids = self._filtered_inspection_query(date_from, date_to, category).subquery()
        id_select = select(ids.c.id)
        rows = self.db.query(
            RuleResult.rule_id,
            RuleResult.rule_name,
            func.count().label("total"),
            func.sum(case((RuleResult.status == "COMPLIANT", 1), else_=0)).label("compliant"),
            func.sum(case((RuleResult.status == "NON_COMPLIANT", 1), else_=0)).label("non_compliant"),
            func.sum(case((RuleResult.status == "REVIEW_REQUIRED", 1), else_=0)).label("review"),
            func.sum(case((RuleResult.applicability_status == "NOT_APPLICABLE", 1), else_=0)).label("not_applicable"),
        ).filter(RuleResult.inspection_id.in_(id_select)).group_by(
            RuleResult.rule_id, RuleResult.rule_name
        ).order_by(RuleResult.rule_id).all()
        return RuleStatistics(items=[
            RuleStatisticsItem(
                rule_id=rule_id, rule_name=rule_name, total_evaluations=total,
                compliant_count=compliant or 0, non_compliant_count=non_compliant or 0,
                review_required_count=review or 0, not_applicable_count=not_applicable or 0,
            )
            for rule_id, rule_name, total, compliant, non_compliant, review, not_applicable in rows
        ])

    def recent(self, limit, date_from, date_to, category):
        result = self.history(
            page=1, page_size=limit, status=None, compliance_status=None,
            category=category, subcategory=None, product_name=None,
            report_number=None, date_from=date_from, date_to=date_to,
            minimum_confidence=None, maximum_confidence=None, search=None,
            sort_by="created_at", sort_order="desc",
        )
        return [RecentInspection.model_validate(item) for item in result.items]
