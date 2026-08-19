"""Celery periodic task: send due reminder emails."""
from __future__ import annotations

from datetime import UTC, datetime

from app.core.logging import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.reminder_tasks.send_due_reminders")
def send_due_reminders() -> dict:
    """Check for due reminders and send email notifications."""
    import asyncio

    from app.db.models import Job, JobDetails, Reminder, User
    from app.services.email_sync import send_reminder_email

    db = _get_sync_db()
    now = datetime.now(UTC)
    sent_count = 0

    try:
        due_reminders = (
            db.query(Reminder)
            .filter(Reminder.remind_at <= now, Reminder.is_sent.is_(False))
            .limit(100)
            .all()
        )

        for reminder in due_reminders:
            try:
                user = db.query(User).filter(User.id == reminder.user_id).first()
                job = db.query(Job).filter(Job.id == reminder.job_id).first()
                details = db.query(JobDetails).filter(JobDetails.job_id == reminder.job_id).first()

                if not user or not job:
                    continue

                job_title = (details.title if details else None) or "Job Application"
                company = (details.company if details else None) or "Unknown Company"

                subject = f"📋 Reminder: {job_title} at {company}"
                body = f"""
                <html><body style="font-family: Inter, sans-serif; background: #0f172a; color: #e2e8f0; padding: 24px;">
                  <div style="max-width: 600px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 32px;">
                    <h2 style="color: #6366f1; margin-bottom: 8px;">Job-Pilot-AI Reminder</h2>
                    <h3 style="color: #f1f5f9;">{job_title} at {company}</h3>
                    <p style="color: #94a3b8;">{reminder.message}</p>
                    <p style="color: #64748b; font-size: 14px;">
                      Reminder set for: {reminder.remind_at.strftime('%B %d, %Y at %H:%M UTC')}
                    </p>
                    <a href="{job.url}" style="display: inline-block; background: #6366f1; color: white;
                       padding: 12px 24px; border-radius: 8px; text-decoration: none; margin-top: 16px;">
                      View Job
                    </a>
                  </div>
                </body></html>
                """

                success = asyncio.run(send_reminder_email(user.email, subject, body))
                if success:
                    reminder.is_sent = True
                    reminder.sent_at = now
                    sent_count += 1

            except Exception as e:
                logger.error("reminder_send_error", reminder_id=str(reminder.id), error=str(e))

        db.commit()
        logger.info("reminders_processed", sent=sent_count, total=len(due_reminders))
        return {"sent": sent_count, "total": len(due_reminders)}

    except Exception as e:
        db.rollback()
        logger.error("reminders_task_error", error=str(e))
        return {"error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.reminder_tasks.send_single_reminder")
def send_single_reminder(reminder_id: str) -> dict:
    """Send a specific reminder immediately (called by user action)."""
    # Delegates to the batch task for simplicity
    return send_due_reminders()


def _get_sync_db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.config import get_settings

    settings = get_settings()
    sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(sync_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    return Session()
