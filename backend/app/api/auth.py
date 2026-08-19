"""Authentication API routes: register, login, refresh, logout."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_redis
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    store_refresh_token,
    validate_refresh_token,
    verify_password,
)
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import (
    RefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


def _build_token_response(user_id: str, raw_refresh: str) -> TokenResponse:
    access = create_access_token(user_id)
    return TokenResponse(
        access_token=access,
        refresh_token=raw_refresh,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    """Create a new user account and return JWT tokens."""
    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    await db.flush()  # get the UUID before commit

    raw_refresh, token_hash = create_refresh_token(str(user.id))
    await store_refresh_token(redis, str(user.id), token_hash)
    await db.commit()

    return _build_token_response(str(user.id), raw_refresh)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    """Authenticate with email + password, return JWT tokens."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    raw_refresh, token_hash = create_refresh_token(str(user.id))
    await store_refresh_token(redis, str(user.id), token_hash)

    return _build_token_response(str(user.id), raw_refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    body: RefreshRequest,
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    """Rotate refresh token — old token is invalidated on use."""
    # The refresh token encodes user_id:token_hash
    try:
        user_id, old_hash = body.refresh_token.split(":", 1)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if not await validate_refresh_token(redis, user_id, old_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired or revoked")

    # Rotate: invalidate old, issue new
    await revoke_refresh_token(redis, user_id, old_hash)
    raw_refresh, new_hash = create_refresh_token(user_id)
    await store_refresh_token(redis, user_id, new_hash)

    return _build_token_response(user_id, raw_refresh)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    body: RefreshRequest,
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict:
    """Revoke the provided refresh token (logout current device)."""
    try:
        _, token_hash = body.refresh_token.split(":", 1)
        await revoke_refresh_token(redis, str(current_user.id), token_hash)
    except (ValueError, Exception):
        pass  # Already invalid — idempotent logout
    return {"message": "Logged out successfully"}


@router.post("/logout-all", status_code=status.HTTP_200_OK)
async def logout_all(
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict:
    """Revoke all refresh tokens for the user (logout all devices)."""
    await revoke_all_refresh_tokens(redis, str(current_user.id))
    return {"message": "Logged out from all devices"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the currently authenticated user's profile."""
    return current_user
