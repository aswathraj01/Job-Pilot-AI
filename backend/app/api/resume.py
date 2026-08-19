"""Resume upload, parsing, and AI matching API routes."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import Job, JobDetails, Resume, ResumeMatch
from app.db.session import get_db
from app.db.models import User
from app.schemas.resume import AllMatchesResponse, ResumeMatchResponse, ResumeResponse
from app.services.matcher import extract_resume_skills, match_resume_to_job
from app.services.resume_parser import (
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE_BYTES,
    extract_resume_text,
)

router = APIRouter(prefix="/resume", tags=["Resume"])


@router.post("/upload", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeResponse:
    """
    Upload a PDF or DOCX resume.
    Extracts text and parses skills with Gemini.
    Marks all previous resumes as inactive.
    """
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Allowed: PDF, DOCX",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum 10 MB.",
        )

    # Extract text
    try:
        raw_text = extract_resume_text(file_bytes, file.content_type)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # Parse skills with LLM
    skills = await extract_resume_skills(raw_text)

    # Deactivate previous resumes
    await db.execute(
        update(Resume)
        .where(Resume.user_id == current_user.id)
        .values(is_active=False)
    )

    resume = Resume(
        user_id=current_user.id,
        filename=file.filename or "resume",
        file_size_bytes=len(file_bytes),
        mime_type=file.content_type,
        raw_text=raw_text,
        parsed_skills=skills,
        is_active=True,
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    return ResumeResponse.model_validate(resume)


@router.get("/", response_model=ResumeResponse | None)
async def get_active_resume(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeResponse | None:
    """Return the user's currently active resume."""
    result = await db.execute(
        select(Resume).where(Resume.user_id == current_user.id, Resume.is_active.is_(True))
    )
    resume = result.scalar_one_or_none()
    return ResumeResponse.model_validate(resume) if resume else None


@router.post("/match/{job_id}", response_model=ResumeMatchResponse)
async def match_resume(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeMatchResponse:
    """
    Run AI resume matching for a specific job.
    Requires an active resume to be uploaded.
    """
    # Get active resume
    resume_result = await db.execute(
        select(Resume).where(Resume.user_id == current_user.id, Resume.is_active.is_(True))
    )
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="No active resume found. Please upload your resume first.")

    # Get job details
    job_result = await db.execute(
        select(Job, JobDetails)
        .join(JobDetails, Job.id == JobDetails.job_id, isouter=True)
        .where(Job.id == job_id, Job.user_id == current_user.id, Job.is_deleted.is_(False))
    )
    row = job_result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    job, details = row

    # Run AI matching
    result = await match_resume_to_job(
        resume_text=resume.raw_text or "",
        resume_skills=resume.parsed_skills or [],
        job_skills=details.skills_required if details else [],
        job_description=details.description_text if details else "",
    )

    # Upsert match record
    existing = await db.execute(
        select(ResumeMatch).where(ResumeMatch.resume_id == resume.id, ResumeMatch.job_id == job_id)
    )
    match = existing.scalar_one_or_none()
    if match:
        match.score = result["score"]
        match.matched_skills = result.get("matched_skills")
        match.gap_skills = result.get("gap_skills")
        match.ai_summary = result.get("ai_summary")
    else:
        match = ResumeMatch(
            resume_id=resume.id,
            job_id=job_id,
            score=result["score"],
            matched_skills=result.get("matched_skills"),
            gap_skills=result.get("gap_skills"),
            ai_summary=result.get("ai_summary"),
        )
        db.add(match)

    await db.commit()
    await db.refresh(match)
    return ResumeMatchResponse.model_validate(match)


@router.get("/matches", response_model=AllMatchesResponse)
async def list_matches(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AllMatchesResponse:
    """Return all resume match scores for the active resume, sorted by score."""
    resume_result = await db.execute(
        select(Resume).where(Resume.user_id == current_user.id, Resume.is_active.is_(True))
    )
    resume = resume_result.scalar_one_or_none()
    if not resume:
        return AllMatchesResponse(items=[], total=0)

    matches_result = await db.execute(
        select(ResumeMatch)
        .where(ResumeMatch.resume_id == resume.id)
        .order_by(ResumeMatch.score.desc())
    )
    matches = matches_result.scalars().all()
    return AllMatchesResponse(
        items=[ResumeMatchResponse.model_validate(m) for m in matches],
        total=len(matches),
    )
