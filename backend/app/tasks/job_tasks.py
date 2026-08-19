"""
Job processing Celery task.
Pipeline: URL → Scrape HTML → Clean Text → LLM Extract → Save to DB → Notify WebSocket
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from celery import Task
from sqlalchemy import select

from app.core.logging import get_logger
from app.db.models import Job, JobDetails, JobStatus
from app.services.extractor import calculate_confidence, extract_job_details
from app.services.scraper import scrape_job_page
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


def _get_db_session():
    """Create a synchronous database session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.config import get_settings

    settings = get_settings()
    # Use sync driver for Celery (psycopg2)
    sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(sync_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    return Session()


def _publish_status(job_id: str, status: str, message: str, progress: int = 0) -> None:
    """Publish status to Redis pub/sub for WebSocket consumers."""
    import json

    import redis

    from app.core.config import get_settings

    try:
        r = redis.from_url(get_settings().REDIS_URL)
        r.publish(
            f"job_status:{job_id}",
            json.dumps({"job_id": job_id, "status": status, "message": message, "progress": progress}),
        )
    except Exception as e:
        logger.warning("redis_publish_failed", job_id=job_id, error=str(e))


@celery_app.task(
    name="app.tasks.job_tasks.process_job_url",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_job_url(self: Task, job_id: str, url: str, user_id: str) -> dict:
    """
    Full job processing pipeline:
    1. Scrape the page (httpx → playwright fallback)
    2. Extract structured data with Gemini LLM
    3. Update job_details in PostgreSQL
    4. Publish status updates via Redis
    """
    logger.info("job_processing_start", job_id=job_id, url=url)
    db = _get_db_session()

    try:
        # ── Step 1: Scraping ──────────────────────────────────────────
        _publish_status(job_id, "scraping", "Fetching job page...", progress=20)
        html, clean_text = asyncio.run(scrape_job_page(url))
        logger.info("scrape_done", job_id=job_id, text_len=len(clean_text))

        # ── Step 2: LLM Extraction ────────────────────────────────────
        _publish_status(job_id, "extracting", "Extracting job details with AI...", progress=55)
        extracted = asyncio.run(extract_job_details(clean_text, url))
        confidence = calculate_confidence(extracted)
        logger.info("extraction_done", job_id=job_id, confidence=confidence)

        # ── Step 3: Save to Database ──────────────────────────────────
        _publish_status(job_id, "saving", "Saving job details...", progress=80)
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error("job_not_found", job_id=job_id)
            return {"status": "failed", "error": "Job not found"}

        # Create or update JobDetails
        details = db.query(JobDetails).filter(JobDetails.job_id == job_id).first()
        if not details:
            details = JobDetails(job_id=job_id)
            db.add(details)

        # Map extracted fields to model
        details.title = extracted.get("title")
        details.company = extracted.get("company")
        details.location = extracted.get("location")
        details.remote_type = extracted.get("remote_type")
        details.job_type = extracted.get("job_type")
        details.salary_min = extracted.get("salary_min")
        details.salary_max = extracted.get("salary_max")
        details.currency = extracted.get("currency")
        details.experience_years_min = extracted.get("experience_years_min")
        details.experience_years_max = extracted.get("experience_years_max")
        details.description_text = clean_text[:50000]
        details.description_html = html[:100000]
        details.description_summary = extracted.get("description_summary")
        details.skills_required = extracted.get("skills_required")
        details.benefits = extracted.get("benefits")
        details.requirements = extracted.get("requirements")
        details.responsibilities = extracted.get("responsibilities")
        details.application_deadline = extracted.get("application_deadline")
        details.application_url = extracted.get("application_url")
        details.source_platform = extracted.get("source_platform")
        details.job_id_on_platform = extracted.get("job_id_on_platform")
        details.raw_llm_response = {"raw": extracted.get("_raw_response")}
        details.extraction_confidence = confidence
        details.extracted_at = datetime.now(UTC)

        # Update job status from PROCESSING → SAVED
        job.status = JobStatus.SAVED

        db.commit()
        logger.info("job_saved", job_id=job_id)

        # ── Step 4: Done ──────────────────────────────────────────────
        _publish_status(job_id, "done", "Job details extracted successfully!", progress=100)
        return {"status": "done", "job_id": job_id, "confidence": confidence}

    except Exception as exc:
        db.rollback()
        logger.error("job_processing_failed", job_id=job_id, error=str(exc))

        # Mark job as failed in DB
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = JobStatus.SAVED  # Revert to saved on failure
            db.commit()
        except Exception:
            pass

        _publish_status(job_id, "failed", f"Processing failed: {str(exc)[:200]}", progress=0)
        raise

    finally:
        db.close()
