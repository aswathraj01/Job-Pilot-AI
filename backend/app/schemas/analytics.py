"""Pydantic schemas for analytics endpoints."""
from __future__ import annotations

from pydantic import BaseModel


class StatusCount(BaseModel):
    status: str
    count: int


class SummaryResponse(BaseModel):
    total_jobs: int
    saved: int
    processing: int
    applied: int
    phone_screen: int
    interview: int
    offer: int
    rejected: int
    withdrawn: int
    response_rate_pct: float  # (phone_screen + interview + offer) / applied * 100


class TimelinePoint(BaseModel):
    period: str  # "2024-W01" or "2024-01"
    count: int


class TimelineResponse(BaseModel):
    granularity: str  # "week" | "month"
    data: list[TimelinePoint]


class FunnelStage(BaseModel):
    stage: str
    count: int
    conversion_pct: float | None  # vs previous stage


class FunnelResponse(BaseModel):
    stages: list[FunnelStage]


class CompanyCount(BaseModel):
    company: str
    count: int


class SkillDemand(BaseModel):
    skill: str
    count: int
    pct_of_jobs: float


class AnalyticsSummary(BaseModel):
    summary: SummaryResponse
    timeline: TimelineResponse
    funnel: FunnelResponse
    top_companies: list[CompanyCount]
    top_skills: list[SkillDemand]
