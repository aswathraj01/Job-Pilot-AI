"""Gmail OAuth2 and email thread API routes."""
from __future__ import annotations

import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_redis
from app.db.models import EmailThread, Job, User
from app.db.session import get_db
from app.services.email_sync import exchange_code_for_tokens, get_gmail_auth_url
from app.tasks.email_tasks import sync_user_email

router = APIRouter(prefix="/email", tags=["Email"])


class EmailThreadResponse(BaseModel):
    id: UUID
    job_id: UUID
    gmail_thread_id: str
    subject: str | None
    snippet: str | None
    from_email: str | None
    message_count: int
    received_at: str | None

    model_config = {"from_attributes": True}


class ConnectResponse(BaseModel):
    auth_url: str


@router.get("/connect", response_model=ConnectResponse)
async def gmail_connect(
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
) -> ConnectResponse:
    """Return the Gmail OAuth2 authorization URL."""
    state = secrets.token_urlsafe(16)
    await redis.setex(f"oauth_state:{state}", 600, str(current_user.id))
    url = get_gmail_auth_url(state)
    return ConnectResponse(auth_url=url)


@router.get("/callback")
async def gmail_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> RedirectResponse:
    """Handle OAuth2 callback, store tokens, redirect to frontend."""
    from app.core.config import get_settings

    settings = get_settings()

    # Validate state
    user_id = await redis.get(f"oauth_state:{state}")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    await redis.delete(f"oauth_state:{state}")

    # Exchange code for tokens
    try:
        tokens = exchange_code_for_tokens(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {e}")

    # Store tokens on user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.gmail_access_token = tokens["access_token"]
    user.gmail_refresh_token = tokens.get("refresh_token")
    await db.commit()

    # Trigger initial sync
    sync_user_email.delay(user_id)

    return RedirectResponse(url=f"{settings.FRONTEND_URL}/settings?gmail=connected")


@router.post("/sync")
async def trigger_sync(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Manually trigger Gmail sync for the current user."""
    if not current_user.gmail_access_token:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    sync_user_email.delay(str(current_user.id))
    return {"message": "Email sync queued"}


@router.get("/threads/{job_id}", response_model=list[EmailThreadResponse])
async def get_job_threads(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EmailThreadResponse]:
    """Return Gmail threads linked to a specific job."""
    result = await db.execute(
        select(EmailThread).where(
            EmailThread.job_id == job_id,
            EmailThread.user_id == current_user.id,
        )
    )
    threads = result.scalars().all()
    return [EmailThreadResponse.model_validate(t) for t in threads]


@router.delete("/disconnect", status_code=200)
async def disconnect_gmail(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Disconnect Gmail and delete all synced threads."""
    current_user.gmail_access_token = None
    current_user.gmail_refresh_token = None
    current_user.gmail_token_expiry = None
    
    # Delete synced threads
    await db.execute(delete(EmailThread).where(EmailThread.user_id == current_user.id))
    await db.commit()
    return {"message": "Gmail disconnected successfully"}
