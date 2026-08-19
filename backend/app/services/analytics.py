"""
Analytics query service.
All queries run against PostgreSQL using SQLAlchemy async ORM.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job, JobDetails, JobStatus, ResumeMatch
from app.schemas.analytics import (
    AnalyticsSummary,
    CompanyCount,
    FunnelResponse,
    FunnelStage,
    SkillDemand,
    StatusCount,
    SummaryResponse,
    TimelinePoint,
    TimelineResponse,
)


async def get_summary(db: AsyncSession, user_id: UUID) -> SummaryResponse:
    """Return counts by status and compute response rate."""
    result = await db.execute(
        select(Job.status, func.count(Job.id).label("count"))
        .where(Job.user_id == user_id, Job.is_deleted.is_(False))
        .group_by(Job.status)
    )
    rows = result.all()
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row.status.value] = row.count

    total = sum(counts.values())
    applied = counts.get("applied", 0)
    responses = (
        counts.get("phone_screen", 0) + counts.get("interview", 0) + counts.get("offer", 0)
    )
    response_rate = round((responses / applied * 100) if applied > 0 else 0.0, 1)

    return SummaryResponse(
        total_jobs=total,
        saved=counts.get("saved", 0),
        processing=counts.get("processing", 0),
        applied=applied,
        phone_screen=counts.get("phone_screen", 0),
        interview=counts.get("interview", 0),
        offer=counts.get("offer", 0),
        rejected=counts.get("rejected", 0),
        withdrawn=counts.get("withdrawn", 0),
        response_rate_pct=response_rate,
    )


async def get_timeline(
    db: AsyncSession, user_id: UUID, granularity: str = "week"
) -> TimelineResponse:
    """Return application counts grouped by week or month."""
    if granularity == "month":
        period_expr = func.to_char(Job.created_at, "YYYY-MM")
    else:
        period_expr = func.to_char(Job.created_at, "IYYY-\"W\"IW")

    result = await db.execute(
        select(period_expr.label("period"), func.count(Job.id).label("count"))
        .where(
            Job.user_id == user_id,
            Job.is_deleted.is_(False),
            Job.created_at >= datetime.now(UTC) - timedelta(days=365),
        )
        .group_by("period")
        .order_by("period")
    )

    return TimelineResponse(
        granularity=granularity,
        data=[TimelinePoint(period=row.period, count=row.count) for row in result.all()],
    )


async def get_funnel(db: AsyncSession, user_id: UUID) -> FunnelResponse:
    """Return stage conversion funnel."""
    stages = [
        JobStatus.SAVED,
        JobStatus.APPLIED,
        JobStatus.PHONE_SCREEN,
        JobStatus.INTERVIEW,
        JobStatus.OFFER,
    ]

    result = await db.execute(
        select(Job.status, func.count(Job.id).label("count"))
        .where(Job.user_id == user_id, Job.is_deleted.is_(False))
        .group_by(Job.status)
    )
    counts: dict[str, int] = {row.status.value: row.count for row in result.all()}

    funnel_stages = []
    prev_count: int | None = None
    for stage in stages:
        count = counts.get(stage.value, 0)
        conv = None
        if prev_count and prev_count > 0:
            conv = round(count / prev_count * 100, 1)
        funnel_stages.append(FunnelStage(stage=stage.value, count=count, conversion_pct=conv))
        prev_count = count

    return FunnelResponse(stages=funnel_stages)


async def get_top_companies(
    db: AsyncSession, user_id: UUID, limit: int = 10
) -> list[CompanyCount]:
    result = await db.execute(
        select(JobDetails.company, func.count(Job.id).label("count"))
        .join(JobDetails, Job.id == JobDetails.job_id)
        .where(
            Job.user_id == user_id,
            Job.is_deleted.is_(False),
            JobDetails.company.isnot(None),
        )
        .group_by(JobDetails.company)
        .order_by(func.count(Job.id).desc())
        .limit(limit)
    )
    return [CompanyCount(company=row.company, count=row.count) for row in result.all()]


async def get_top_skills(
    db: AsyncSession, user_id: UUID, limit: int = 20
) -> list[SkillDemand]:
    """Aggregate skills_required across all jobs using JSONB unnesting."""
    sql = text("""
        SELECT
            skill,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / (
                SELECT COUNT(*) FROM jobs j2
                JOIN job_details jd2 ON j2.id = jd2.job_id
                WHERE j2.user_id = :user_id AND j2.is_deleted = false
                  AND jd2.skills_required IS NOT NULL
            ), 1) as pct
        FROM jobs j
        JOIN job_details jd ON j.id = jd.job_id,
        jsonb_array_elements_text(jd.skills_required) AS skill
        WHERE j.user_id = :user_id
          AND j.is_deleted = false
          AND jd.skills_required IS NOT NULL
        GROUP BY skill
        ORDER BY count DESC
        LIMIT :limit
    """)
    result = await db.execute(sql, {"user_id": str(user_id), "limit": limit})
    return [
        SkillDemand(skill=row.skill, count=row.count, pct_of_jobs=float(row.pct or 0))
        for row in result.all()
    ]


async def get_full_analytics(db: AsyncSession, user_id: UUID) -> AnalyticsSummary:
    summary, timeline, funnel, companies, skills = await _gather(
        get_summary(db, user_id),
        get_timeline(db, user_id),
        get_funnel(db, user_id),
        get_top_companies(db, user_id),
        get_top_skills(db, user_id),
    )
    return AnalyticsSummary(
        summary=summary,
        timeline=timeline,
        funnel=funnel,
        top_companies=companies,
        top_skills=skills,
    )


async def _gather(*coros):
    """Simple sequential gather (asyncio.gather needs running loop)."""
    import asyncio
    return await asyncio.gather(*coros)
