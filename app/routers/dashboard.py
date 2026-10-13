"""Dashboard endpoints: headline metrics and chart breakdowns.

Both accept the same filters as GET /api/evaluations.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.filters import CallFilters
from app.schemas import DashboardAnalytics, DashboardMetrics
from app.services.analytics import compute_analytics, compute_metrics

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/metrics", response_model=DashboardMetrics, summary="Headline call metrics")
def dashboard_metrics(filters: CallFilters = Depends(), db: Session = Depends(get_db)) -> DashboardMetrics:
    return compute_metrics(db, filters)


@router.get("/analytics", response_model=DashboardAnalytics, summary="Breakdowns for dashboard charts")
def dashboard_analytics(filters: CallFilters = Depends(), db: Session = Depends(get_db)) -> DashboardAnalytics:
    return compute_analytics(db, filters)
