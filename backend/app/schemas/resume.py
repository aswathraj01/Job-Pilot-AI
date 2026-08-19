"""Pydantic schemas for resume upload and matching."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ResumeResponse(BaseModel):
    id: UUID
    filename: str
    file_size_bytes: int
    mime_type: str
    parsed_skills: list[str] | None = None
    parsed_experience: dict | None = None
    is_active: bool
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class ResumeMatchRequest(BaseModel):
    job_id: UUID


class ResumeMatchResponse(BaseModel):
    id: UUID
    resume_id: UUID
    job_id: UUID
    score: float
    matched_skills: list[str] | None
    gap_skills: list[str] | None
    ai_summary: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AllMatchesResponse(BaseModel):
    items: list[ResumeMatchResponse]
    total: int
