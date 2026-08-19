"""
Jobs API: CRUD, notes, reminders, search, WebSocket status.
"""
from __future__ import annotations

import asyncio
import json
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_current_user_ws, get_redis
from app.core.ws_manager import ws_manager
from app.db.models import Job, JobDetails, JobNote, JobStatus, Reminder, User
from app.db.session import get_db
from app.schemas.jobs import (
    JobCreateRequest,
    JobDetailResponse,
    JobDetailsSchema,
    JobListResponse,
    JobSummaryResponse,
    JobUpdateRequest,
    NoteCreateRequest,
    NoteResponse,
    NoteUpdateRequest,
    ReminderCreateRequest,
    ReminderResponse,
    ResumeMatchResponse,
)
from app.tasks.job_tasks import process_job_url

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# ─── Helper ───────────────────────────────────────────────────────────────────

def _job_to_summary(job: Job) -> JobSummaryResponse:
    d = job.details
    return JobSummaryResponse(
        id=job.id,
        url=job.url,
        status=job.status,
        applied_at=job.applied_at,
        deadline=job.deadline,
        created_at=job.created_at,
        updated_at=job.updated_at,
        title=d.title if d else None,
        company=d.company if d else None,
        location=d.location if d else None,
        remote_type=d.remote_type if d else None,
        job_type=d.job_type if d else None,
        salary_min=d.salary_min if d else None,
        salary_max=d.salary_max if d else None,
        currency=d.currency if d else None,
        skills_required=d.skills_required if d else None,
        source_platform=d.source_platform if d else None,
    )


# ─── Create Job ───────────────────────────────────────────────────────────────

@router.post("/", response_model=JobSummaryResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    body: JobCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobSummaryResponse:
    """
    Add a job by URL. Returns immediately with status=processing.
    Processing happens asynchronously via Celery.
    """
    # Check for duplicate
    existing = await db.execute(
        select(Job).where(Job.user_id == current_user.id, Job.url == body.url, Job.is_deleted.is_(False))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job already tracked")

    job = Job(
        user_id=current_user.id,
        url=body.url,
        status=JobStatus.PROCESSING,
        applied_at=body.applied_at,
        deadline=body.deadline,
    )
    db.add(job)
    await db.flush()

    # Enqueue background task
    process_job_url.delay(str(job.id), body.url, str(current_user.id))
    await db.commit()

    return _job_to_summary(job)


# ─── List Jobs ────────────────────────────────────────────────────────────────

@router.get("/", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: JobStatus | None = None,
    company: str | None = None,
    remote_type: str | None = None,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """Paginated job list with optional filters and full-text search."""
    query = (
        select(Job)
        .options(selectinload(Job.details))
        .where(Job.user_id == current_user.id, Job.is_deleted.is_(False))
    )

    if status:
        query = query.where(Job.status == status)
    if company:
        query = query.join(JobDetails, Job.id == JobDetails.job_id).where(
            JobDetails.company.ilike(f"%{company}%")
        )
    if remote_type:
        if not company:
            query = query.join(JobDetails, Job.id == JobDetails.job_id)
        query = query.where(JobDetails.remote_type == remote_type)
    if search:
        if not company and not remote_type:
            query = query.outerjoin(JobDetails, Job.id == JobDetails.job_id)
        query = query.where(
            or_(
                JobDetails.title.ilike(f"%{search}%"),
                JobDetails.company.ilike(f"%{search}%"),
                JobDetails.description_text.ilike(f"%{search}%"),
                Job.url.ilike(f"%{search}%"),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Paginate
    query = query.order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        items=[_job_to_summary(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )


# ─── Get Job Detail ───────────────────────────────────────────────────────────

@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobDetailResponse:
    """Full job record with details, notes, reminders, and best resume match."""
    result = await db.execute(
        select(Job)
        .options(
            selectinload(Job.details),
            selectinload(Job.notes),
            selectinload(Job.reminders),
            selectinload(Job.resume_matches),
        )
        .where(Job.id == job_id, Job.user_id == current_user.id, Job.is_deleted.is_(False))
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Best resume match (highest score)
    best_match = max(job.resume_matches, key=lambda m: m.score, default=None) if job.resume_matches else None

    return JobDetailResponse(
        id=job.id,
        url=job.url,
        status=job.status,
        applied_at=job.applied_at,
        deadline=job.deadline,
        created_at=job.created_at,
        updated_at=job.updated_at,
        details=JobDetailsSchema.model_validate(job.details) if job.details else None,
        notes=[NoteResponse.model_validate(n) for n in job.notes],
        reminders=[ReminderResponse.model_validate(r) for r in job.reminders],
        resume_match=ResumeMatchResponse.model_validate(best_match) if best_match else None,
    )


# ─── Update Job ───────────────────────────────────────────────────────────────

@router.patch("/{job_id}", response_model=JobSummaryResponse)
async def update_job(
    job_id: UUID,
    body: JobUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobSummaryResponse:
    result = await db.execute(
        select(Job)
        .options(selectinload(Job.details))
        .where(Job.id == job_id, Job.user_id == current_user.id, Job.is_deleted.is_(False))
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if body.status is not None:
        job.status = body.status
    if body.applied_at is not None:
        job.applied_at = body.applied_at
    if body.deadline is not None:
        job.deadline = body.deadline

    await db.commit()
    await db.refresh(job)
    return _job_to_summary(job)


# ─── Delete Job ───────────────────────────────────────────────────────────────

@router.delete("/{job_id}", status_code=status.HTTP_200_OK)
async def delete_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.user_id == current_user.id, Job.is_deleted.is_(False))
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.is_deleted = True
    await db.commit()
    return {}


# ─── Notes ────────────────────────────────────────────────────────────────────

@router.post("/{job_id}/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def add_note(
    job_id: UUID,
    body: NoteCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NoteResponse:
    # Verify ownership
    job_result = await db.execute(
        select(Job).where(Job.id == job_id, Job.user_id == current_user.id, Job.is_deleted.is_(False))
    )
    if not job_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Job not found")

    note = JobNote(job_id=job_id, user_id=current_user.id, content=body.content)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return NoteResponse.model_validate(note)


@router.put("/{job_id}/notes/{note_id}", response_model=NoteResponse)
async def update_note(
    job_id: UUID,
    note_id: UUID,
    body: NoteUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NoteResponse:
    result = await db.execute(
        select(JobNote).where(
            JobNote.id == note_id,
            JobNote.job_id == job_id,
            JobNote.user_id == current_user.id,
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    note.content = body.content
    await db.commit()
    await db.refresh(note)
    return NoteResponse.model_validate(note)


@router.delete("/{job_id}/notes/{note_id}", status_code=status.HTTP_200_OK)
async def delete_note(
    job_id: UUID,
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(JobNote).where(
            JobNote.id == note_id, JobNote.job_id == job_id, JobNote.user_id == current_user.id
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    await db.delete(note)
    await db.commit()
    return {}


# ─── Reminders ────────────────────────────────────────────────────────────────

@router.post("/{job_id}/reminders", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def add_reminder(
    job_id: UUID,
    body: ReminderCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderResponse:
    job_result = await db.execute(
        select(Job).where(Job.id == job_id, Job.user_id == current_user.id, Job.is_deleted.is_(False))
    )
    if not job_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Job not found")

    reminder = Reminder(
        job_id=job_id,
        user_id=current_user.id,
        message=body.message,
        remind_at=body.remind_at,
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return ReminderResponse.model_validate(reminder)


@router.delete("/{job_id}/reminders/{reminder_id}", status_code=status.HTTP_200_OK)
async def delete_reminder(
    job_id: UUID,
    reminder_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Reminder).where(
            Reminder.id == reminder_id, Reminder.job_id == job_id, Reminder.user_id == current_user.id
        )
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    await db.delete(reminder)
    await db.commit()
    return {}


# ─── WebSocket: Real-time Job Processing Status ───────────────────────────────

@router.websocket("/{job_id}/ws")
async def job_status_ws(
    websocket: WebSocket,
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    WebSocket endpoint for real-time job processing status.
    Connect with: ws://host/api/v1/jobs/{job_id}/ws?token=<jwt>
    Subscribes to Redis pub/sub and forwards messages.
    """
    user = await get_current_user_ws(websocket, db)
    if not user:
        await websocket.close(code=4001)
        return

    await ws_manager.connect(websocket, job_id)

    # Subscribe to Redis channel for this job
    redis_client = aioredis.from_url(__import__("app.core.config", fromlist=["get_settings"]).get_settings().REDIS_URL)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"job_status:{job_id}")

    try:
        async def listen_redis():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await ws_manager.broadcast_status(
                        job_id,
                        status=data.get("status", ""),
                        message=data.get("message"),
                        progress=data.get("progress", 0),
                    )
                    if data.get("status") in ("done", "failed"):
                        break

        await asyncio.wait_for(listen_redis(), timeout=300)
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        await pubsub.unsubscribe(f"job_status:{job_id}")
        await redis_client.aclose()
        ws_manager.disconnect(websocket, job_id)
