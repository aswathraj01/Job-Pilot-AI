"""Celery periodic task: sync Gmail threads for all users with connected accounts."""
from __future__ import annotations

from app.core.logging import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.email_tasks.sync_all_users_email")
def sync_all_users_email() -> dict:
    """Sync Gmail for all users who have connected their accounts."""
    from app.db.models import EmailThread, Job, JobDetails, User

    db = _get_sync_db()
    synced_users = 0

    try:
        users_with_gmail = (
            db.query(User)
            .filter(User.gmail_access_token.isnot(None), User.is_active.is_(True))
            .all()
        )

        for user in users_with_gmail:
            try:
                sync_user_email.delay(str(user.id))
                synced_users += 1
            except Exception as e:
                logger.error("sync_user_queue_error", user_id=str(user.id), error=str(e))

        return {"queued_users": synced_users}
    finally:
        db.close()


@celery_app.task(name="app.tasks.email_tasks.sync_user_email")
def sync_user_email(user_id: str) -> dict:
    """Sync Gmail threads for a specific user and link them to jobs."""
    from app.db.models import EmailThread, Job, JobDetails, User
    from app.services.email_sync import fetch_job_related_threads

    db = _get_sync_db()
    new_threads = 0

    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.gmail_access_token:
            return {"error": "User not found or no Gmail token"}

        # Get all companies the user is tracking
        companies = (
            db.query(JobDetails.company)
            .join(Job, Job.id == JobDetails.job_id)
            .filter(Job.user_id == user_id, JobDetails.company.isnot(None))
            .distinct()
            .all()
        )
        company_names = [c.company for c in companies if c.company]

        threads = fetch_job_related_threads(
            access_token=user.gmail_access_token,
            refresh_token=user.gmail_refresh_token,
            expiry=user.gmail_token_expiry.isoformat() if user.gmail_token_expiry else None,
            company_names=company_names,
        )

        for thread_data in threads:
            # Check if already stored
            existing = (
                db.query(EmailThread)
                .filter(
                    EmailThread.user_id == user_id,
                    EmailThread.gmail_thread_id == thread_data["gmail_thread_id"],
                )
                .first()
            )
            if existing:
                # Update snippet and message count
                existing.snippet = thread_data.get("snippet")
                existing.message_count = thread_data.get("message_count", 1)
                continue

            # Try to link thread to a job by matching company name in subject/from
            matched_job = None
            subject = (thread_data.get("subject") or "").lower()
            from_email = (thread_data.get("from_email") or "").lower()

            for company in company_names:
                if company.lower() in subject or company.lower() in from_email:
                    job = (
                        db.query(Job)
                        .join(JobDetails, Job.id == JobDetails.job_id)
                        .filter(
                            Job.user_id == user_id,
                            JobDetails.company.ilike(f"%{company}%"),
                        )
                        .first()
                    )
                    if job:
                        matched_job = job
                        break

            if matched_job:
                new_thread = EmailThread(
                    job_id=matched_job.id,
                    user_id=user_id,
                    gmail_thread_id=thread_data["gmail_thread_id"],
                    subject=thread_data.get("subject"),
                    snippet=thread_data.get("snippet"),
                    from_email=thread_data.get("from_email"),
                    message_count=thread_data.get("message_count", 1),
                )
                db.add(new_thread)
                new_threads += 1

        db.commit()
        logger.info("email_sync_done", user_id=user_id, new_threads=new_threads)
        return {"new_threads": new_threads}

    except Exception as e:
        db.rollback()
        logger.error("email_sync_error", user_id=user_id, error=str(e))
        return {"error": str(e)}
    finally:
        db.close()


def _get_sync_db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.config import get_settings

    settings = get_settings()
    sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(sync_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    return Session()
