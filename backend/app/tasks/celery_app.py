"""
Celery application factory and task queue configuration.
Broker: Redis (DB 1)
Result Backend: Redis (DB 2)
"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "jobpilot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.job_tasks", "app.tasks.reminder_tasks", "app.tasks.email_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    # Beat schedule — periodic tasks
    beat_schedule={
        "send-due-reminders": {
            "task": "app.tasks.reminder_tasks.send_due_reminders",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        },
        "sync-all-email": {
            "task": "app.tasks.email_tasks.sync_all_users_email",
            "schedule": crontab(minute=0, hour="*/2"),  # Every 2 hours
        },
    },
)
