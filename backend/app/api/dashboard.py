from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.history import (
    CategoryDistribution,
    ComplianceDistribution,
    DashboardSummary,
    RecentInspection,
    RuleStatistics,
)
from app.services.dashboard_service import DashboardService

router = APIRouter()


def date_parameters(
    date_from: datetime | None = Query(default=None, description="Inclusive ISO 8601 timestamp"),
    date_to: datetime | None = Query(default=None, description="Inclusive ISO 8601 timestamp"),
    category: str | None = Query(default=None),
):
    return date_from, date_to, category


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(params=Depends(date_parameters), db: Session = Depends(get_db)):
    date_from, date_to, category = params
    return DashboardService(db).summary(date_from, date_to, category)


@router.get("/compliance-distribution", response_model=ComplianceDistribution)
def compliance_distribution(params=Depends(date_parameters), db: Session = Depends(get_db)):
    date_from, date_to, category = params
    return DashboardService(db).compliance_distribution(date_from, date_to, category)


@router.get("/category-distribution", response_model=CategoryDistribution)
def category_distribution(params=Depends(date_parameters), db: Session = Depends(get_db)):
    date_from, date_to, category = params
    return DashboardService(db).category_distribution(date_from, date_to, category)


@router.get("/rules", response_model=RuleStatistics)
def rule_statistics(params=Depends(date_parameters), db: Session = Depends(get_db)):
    date_from, date_to, category = params
    return DashboardService(db).rule_statistics(date_from, date_to, category)


@router.get("/recent-inspections", response_model=list[RecentInspection])
def recent_inspections(
    limit: int = Query(default=10, ge=1, le=100),
    params=Depends(date_parameters),
    db: Session = Depends(get_db),
):
    date_from, date_to, category = params
    return DashboardService(db).recent(limit, date_from, date_to, category)