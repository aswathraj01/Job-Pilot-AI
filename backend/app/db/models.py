"""
SQLAlchemy ORM models for Job-Pilot-AI.

Tables:
  users            — authenticated accounts
  resumes          — uploaded resume files + parsed data
  jobs             — application records
  job_details      — LLM-extracted structured job info (1:1 with jobs)
  job_notes        — user notes on a job
  reminders        — scheduled reminders for jobs
  email_threads    — Gmail threads linked to jobs
  resume_matches   — AI match scores between resume and job
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


# ─── Enumerations ─────────────────────────────────────────────────────────────

class JobStatus(str, enum.Enum):
    SAVED = "saved"
    PROCESSING = "processing"
    APPLIED = "applied"
    PHONE_SCREEN = "phone_screen"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class RemoteType(str, enum.Enum):
    ONSITE = "onsite"
    REMOTE = "remote"
    HYBRID = "hybrid"


class JobType(str, enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"


# ─── Users ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Gmail OAuth tokens (encrypted at application layer)
    gmail_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    gmail_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    gmail_token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="user", cascade="all, delete-orphan")
    resumes: Mapped[list["Resume"]] = relationship("Resume", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


# ─── Resumes ──────────────────────────────────────────────────────────────────

class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_skills: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # ["Python", "FastAPI", ...]
    parsed_experience: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # Only one active resume per user

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="resumes")
    matches: Mapped[list["ResumeMatch"]] = relationship("ResumeMatch", back_populates="resume", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Resume id={self.id} filename={self.filename}>"


# ─── Jobs ─────────────────────────────────────────────────────────────────────

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), default=JobStatus.SAVED, nullable=False, index=True
    )

    # User-editable fields (may override LLM extraction)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Full-text search vector (auto-maintained by trigger or application)
    search_vector: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="jobs")
    details: Mapped["JobDetails | None"] = relationship("JobDetails", back_populates="job", uselist=False, cascade="all, delete-orphan")
    notes: Mapped[list["JobNote"]] = relationship("JobNote", back_populates="job", cascade="all, delete-orphan")
    reminders: Mapped[list["Reminder"]] = relationship("Reminder", back_populates="job", cascade="all, delete-orphan")
    email_threads: Mapped[list["EmailThread"]] = relationship("EmailThread", back_populates="job", cascade="all, delete-orphan")
    resume_matches: Mapped[list["ResumeMatch"]] = relationship("ResumeMatch", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "url", name="uq_user_job_url"),
        Index("ix_jobs_user_status", "user_id", "status"),
        Index("ix_jobs_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} status={self.status}>"


class JobDetails(Base):
    """LLM-extracted structured data for a job posting. All fields nullable."""
    __tablename__ = "job_details"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # Core extracted fields
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    remote_type: Mapped[RemoteType | None] = mapped_column(Enum(RemoteType, name="remote_type"), nullable=True)
    job_type: Mapped[JobType | None] = mapped_column(Enum(JobType, name="job_type"), nullable=True)

    # Compensation
    salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Experience
    experience_years_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    experience_years_max: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Rich content
    description_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_html: Mapped[str | None] = mapped_column(Text, nullable=True)  # Original scraped HTML
    description_summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # LLM-generated summary

    # Structured lists
    skills_required: Mapped[list | None] = mapped_column(JSONB, nullable=True)   # ["Python", "FastAPI"]
    benefits: Mapped[list | None] = mapped_column(JSONB, nullable=True)           # ["Health insurance", "401k"]
    requirements: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    responsibilities: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Application info
    application_deadline: Mapped[str | None] = mapped_column(String(100), nullable=True)
    application_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Source metadata
    source_platform: Mapped[str | None] = mapped_column(String(100), nullable=True)  # "linkedin", "indeed", etc.
    job_id_on_platform: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # LLM audit trail
    raw_llm_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship
    job: Mapped["Job"] = relationship("Job", back_populates="details")

    def __repr__(self) -> str:
        return f"<JobDetails job_id={self.job_id} title={self.title} company={self.company}>"


# ─── Notes ────────────────────────────────────────────────────────────────────

class JobNote(Base):
    __tablename__ = "job_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    job: Mapped["Job"] = relationship("Job", back_populates="notes")

    def __repr__(self) -> str:
        return f"<JobNote id={self.id} job_id={self.job_id}>"


# ─── Reminders ────────────────────────────────────────────────────────────────

class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job: Mapped["Job"] = relationship("Job", back_populates="reminders")

    def __repr__(self) -> str:
        return f"<Reminder id={self.id} remind_at={self.remind_at} sent={self.is_sent}>"


# ─── Email Threads ────────────────────────────────────────────────────────────

class EmailThread(Base):
    __tablename__ = "email_threads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    gmail_thread_id: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job: Mapped["Job"] = relationship("Job", back_populates="email_threads")

    __table_args__ = (
        UniqueConstraint("user_id", "gmail_thread_id", name="uq_user_gmail_thread"),
    )


# ─── Resume Matches ───────────────────────────────────────────────────────────

class ResumeMatch(Base):
    __tablename__ = "resume_matches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 - 100.0
    matched_skills: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    gap_skills: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    resume: Mapped["Resume"] = relationship("Resume", back_populates="matches")
    job: Mapped["Job"] = relationship("Job", back_populates="resume_matches")

    __table_args__ = (
        UniqueConstraint("resume_id", "job_id", name="uq_resume_job_match"),
        Index("ix_resume_matches_score", "score"),
    )

    def __repr__(self) -> str:
        return f"<ResumeMatch resume={self.resume_id} job={self.job_id} score={self.score}>"
