"""Pydantic v2 schemas for jobs, notes, reminders, and full-text search."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field

from app.db.models import JobStatus, JobType, RemoteType


# ─── Job Detail Schemas ───────────────────────────────────────────────────────

class JobDetailsSchema(BaseModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    remote_type: RemoteType | None = None
    job_type: JobType | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = None
    experience_years_min: int | None = None
    experience_years_max: int | None = None
    description_text: str | None = None
    description_summary: str | None = None
    skills_required: list[str] | None = None
    benefits: list[str] | None = None
    requirements: list[str] | None = None
    responsibilities: list[str] | None = None
    application_deadline: str | None = None
    application_url: str | None = None
    source_platform: str | None = None
    extraction_confidence: float | None = None
    extracted_at: datetime | None = None

    model_config = {"from_attributes": True}


# ─── Job Schemas ──────────────────────────────────────────────────────────────

class JobCreateRequest(BaseModel):
    url: str = Field(description="Full URL of the job posting")
    status: JobStatus = JobStatus.SAVED
    applied_at: datetime | None = None
    deadline: datetime | None = None


class JobUpdateRequest(BaseModel):
    status: JobStatus | None = None
    applied_at: datetime | None = None
    deadline: datetime | None = None


class JobSummaryResponse(BaseModel):
    """Lightweight response for job list views."""
    id: UUID
    url: str
    status: JobStatus
    applied_at: datetime | None
    deadline: datetime | None
    created_at: datetime
    updated_at: datetime
    # Flattened from details
    title: str | None = None
    company: str | None = None
    location: str | None = None
    remote_type: RemoteType | None = None
    job_type: JobType | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = None
    skills_required: list[str] | None = None
    source_platform: str | None = None

    model_config = {"from_attributes": True}


class JobDetailResponse(BaseModel):
    """Full job record including details, notes, reminders, and match score."""
    id: UUID
    url: str
    status: JobStatus
    applied_at: datetime | None
    deadline: datetime | None
    created_at: datetime
    updated_at: datetime
    details: JobDetailsSchema | None = None
    notes: list["NoteResponse"] = []
    reminders: list["ReminderResponse"] = []
    resume_match: "ResumeMatchResponse | None" = None

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    items: list[JobSummaryResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


# ─── Notes ────────────────────────────────────────────────────────────────────

class NoteCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class NoteUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class NoteResponse(BaseModel):
    id: UUID
    job_id: UUID
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Reminders ────────────────────────────────────────────────────────────────

class ReminderCreateRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    remind_at: datetime


class ReminderResponse(BaseModel):
    id: UUID
    job_id: UUID
    message: str
    remind_at: datetime
    is_sent: bool
    sent_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Resume Match ─────────────────────────────────────────────────────────────

class ResumeMatchResponse(BaseModel):
    id: UUID
    resume_id: UUID
    job_id: UUID
    score: float
    matched_skills: list[str] | None = None
    gap_skills: list[str] | None = None
    ai_summary: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Processing Status ────────────────────────────────────────────────────────

class JobProcessingStatus(BaseModel):
    job_id: str
    status: str  # "queued" | "scraping" | "extracting" | "done" | "failed"
    message: str | None = None
    progress: int = 0  # 0-100


# Update forward references
JobDetailResponse.model_rebuild()
