from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InspectionHistoryItem(BaseModel):
    inspection_id: str
    inspection_date: datetime
    product_name: str
    category: str
    subcategory: str | None = None
    overall_compliance_status: str | None = None
    overall_confidence: float | None = None
    report_number: str | None = None
    report_status: str | None = None
    ocr_status: str | None = None
    visual_analysis_status: str | None = None
    declaration_count: int = 0
    compliant_rule_count: int = 0
    non_compliant_rule_count: int = 0
    review_required_rule_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InspectionHistoryResponse(BaseModel):
    items: list[InspectionHistoryItem]
    page: int
    page_size: int
    total: int
    total_pages: int


class DashboardSummary(BaseModel):
    total_inspections: int = 0
    compliant_inspections: int = 0
    non_compliant_inspections: int = 0
    review_required_inspections: int = 0
    inspections_without_completed_compliance: int = 0
    average_compliance_confidence: float | None = None
    average_ocr_confidence: float | None = None
    reports_generated: int = 0
    inspections_in_date_range: int = 0


class ComplianceDistributionItem(BaseModel):
    status: str
    count: int


class ComplianceDistribution(BaseModel):
    items: list[ComplianceDistributionItem]


class CategoryDistributionItem(BaseModel):
    category: str
    subcategory: str | None = None
    inspection_count: int


class CategoryDistribution(BaseModel):
    items: list[CategoryDistributionItem]


class RuleStatisticsItem(BaseModel):
    rule_id: str
    rule_name: str
    total_evaluations: int
    compliant_count: int
    non_compliant_count: int
    review_required_count: int
    not_applicable_count: int


class RuleStatistics(BaseModel):
    items: list[RuleStatisticsItem]


class RecentInspection(InspectionHistoryItem):
    pass
