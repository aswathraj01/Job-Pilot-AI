"""Initial schema — all tables.

Revision ID: 0001_initial
Revises: 
Create Date: 2026-08-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ENUM types are created automatically by SQLAlchemy sa.Enum

    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("gmail_access_token", sa.Text(), nullable=True),
        sa.Column("gmail_refresh_token", sa.Text(), nullable=True),
        sa.Column("gmail_token_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # resumes
    op.create_table(
        "resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("parsed_skills", postgresql.JSONB(), nullable=True),
        sa.Column("parsed_experience", postgresql.JSONB(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])

    # jobs
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("status", sa.Enum("saved","processing","applied","phone_screen","interview","offer","rejected","withdrawn", name="job_status"), nullable=False, server_default="saved"),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("search_vector", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "url", name="uq_user_job_url"),
    )
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_user_status", "jobs", ["user_id", "status"])
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])

    # job_details
    op.create_table(
        "job_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("remote_type", sa.Enum("onsite","remote","hybrid", name="remote_type"), nullable=True),
        sa.Column("job_type", sa.Enum("full_time","part_time","contract","internship","freelance", name="job_type"), nullable=True),
        sa.Column("salary_min", sa.Float(), nullable=True),
        sa.Column("salary_max", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("experience_years_min", sa.Integer(), nullable=True),
        sa.Column("experience_years_max", sa.Integer(), nullable=True),
        sa.Column("description_text", sa.Text(), nullable=True),
        sa.Column("description_html", sa.Text(), nullable=True),
        sa.Column("description_summary", sa.Text(), nullable=True),
        sa.Column("skills_required", postgresql.JSONB(), nullable=True),
        sa.Column("benefits", postgresql.JSONB(), nullable=True),
        sa.Column("requirements", postgresql.JSONB(), nullable=True),
        sa.Column("responsibilities", postgresql.JSONB(), nullable=True),
        sa.Column("application_deadline", sa.String(100), nullable=True),
        sa.Column("application_url", sa.Text(), nullable=True),
        sa.Column("source_platform", sa.String(100), nullable=True),
        sa.Column("job_id_on_platform", sa.String(255), nullable=True),
        sa.Column("raw_llm_response", postgresql.JSONB(), nullable=True),
        sa.Column("extraction_confidence", sa.Float(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_job_details_job_id", "job_details", ["job_id"])
    op.create_index("ix_job_details_company", "job_details", ["company"])

    # job_notes
    op.create_table(
        "job_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_job_notes_job_id", "job_notes", ["job_id"])

    # reminders
    op.create_table(
        "reminders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message", sa.String(1000), nullable=False),
        sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_reminders_job_id", "reminders", ["job_id"])
    op.create_index("ix_reminders_remind_at", "reminders", ["remind_at"])

    # email_threads
    op.create_table(
        "email_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gmail_thread_id", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(1000), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("from_email", sa.String(255), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "gmail_thread_id", name="uq_user_gmail_thread"),
    )

    # resume_matches
    op.create_table(
        "resume_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("matched_skills", postgresql.JSONB(), nullable=True),
        sa.Column("gap_skills", postgresql.JSONB(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("resume_id", "job_id", name="uq_resume_job_match"),
    )
    op.create_index("ix_resume_matches_score", "resume_matches", ["score"])

    # Full-text search index on job_details
    op.execute("""
        CREATE INDEX ix_job_details_fts ON job_details
        USING gin(to_tsvector('english', coalesce(title,'') || ' ' || coalesce(company,'') || ' ' || coalesce(description_text,'')))
    """)


def downgrade() -> None:
    op.drop_table("resume_matches")
    op.drop_table("email_threads")
    op.drop_table("reminders")
    op.drop_table("job_notes")
    op.drop_table("job_details")
    op.drop_table("jobs")
    op.drop_table("resumes")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS job_status")
    op.execute("DROP TYPE IF EXISTS remote_type")
    op.execute("DROP TYPE IF EXISTS job_type")
