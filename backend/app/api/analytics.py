"""Analytics API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.analytics import (
    AnalyticsSummary,
    FunnelResponse,
    SummaryResponse,
    TimelineResponse,
)
from app.services.analytics import (
    get_full_analytics,
    get_funnel,
    get_summary,
    get_timeline,
    get_top_companies,
    get_top_skills,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/", response_model=AnalyticsSummary)
async def full_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsSummary:
    """Return all analytics data in a single request for the dashboard."""
    return await get_full_analytics(db, current_user.id)


@router.get("/summary", response_model=SummaryResponse)
async def analytics_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SummaryResponse:
    return await get_summary(db, current_user.id)


@router.get("/timeline", response_model=TimelineResponse)
async def analytics_timeline(
    granularity: str = Query("week", pattern="^(week|month)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TimelineResponse:
    return await get_timeline(db, current_user.id, granularity)


@router.get("/funnel", response_model=FunnelResponse)
async def analytics_funnel(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FunnelResponse:
    return await get_funnel(db, current_user.id)
