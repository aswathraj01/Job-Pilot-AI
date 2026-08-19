"""
JWT RS256 authentication utilities.
- Access tokens: 30-minute short-lived, signed with RS256
- Refresh tokens: 7-day long-lived, stored hash in Redis for rotation
- Blacklisting: refresh tokens invalidated on logout via Redis
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as aioredis
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token type identifiers
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


# ─── Password Utilities ───────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ─── Token Creation ───────────────────────────────────────────────────────────

def create_access_token(user_id: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a short-lived JWT access token signed with RS256."""
    settings = get_settings()
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(claims, settings.jwt_private_key, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """
    Create a secure refresh token.
    Returns (raw_token, token_hash) — store only the hash server-side.
    """
    raw_token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, token_hash


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


# ─── Token Validation ─────────────────────────────────────────────────────────

def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate an access token.
    Raises JWTError on invalid/expired tokens.
    """
    settings = get_settings()
    return jwt.decode(
        token,
        settings.jwt_public_key,
        algorithms=[settings.JWT_ALGORITHM],
        options={"verify_exp": True},
    )


def extract_user_id(token: str) -> str:
    """Extract user_id from a valid access token."""
    payload = decode_access_token(token)
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise JWTError("Invalid token type")
    return payload["sub"]


# ─── Redis Refresh Token Store ────────────────────────────────────────────────

REFRESH_TOKEN_PREFIX = "refresh_token:"
BLACKLIST_PREFIX = "blacklist:"


async def store_refresh_token(
    redis: aioredis.Redis,
    user_id: str,
    token_hash: str,
    expire_days: int | None = None,
) -> None:
    """Store refresh token hash in Redis with TTL."""
    settings = get_settings()
    ttl = timedelta(days=expire_days or settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    key = f"{REFRESH_TOKEN_PREFIX}{user_id}:{token_hash}"
    await redis.setex(key, int(ttl.total_seconds()), "1")


async def validate_refresh_token(
    redis: aioredis.Redis,
    user_id: str,
    token_hash: str,
) -> bool:
    """Return True if refresh token exists and is not blacklisted."""
    key = f"{REFRESH_TOKEN_PREFIX}{user_id}:{token_hash}"
    return bool(await redis.exists(key))


async def revoke_refresh_token(
    redis: aioredis.Redis,
    user_id: str,
    token_hash: str,
) -> None:
    """Delete refresh token from Redis (logout)."""
    key = f"{REFRESH_TOKEN_PREFIX}{user_id}:{token_hash}"
    await redis.delete(key)


async def revoke_all_refresh_tokens(redis: aioredis.Redis, user_id: str) -> None:
    """Revoke all refresh tokens for a user (e.g., password change)."""
    pattern = f"{REFRESH_TOKEN_PREFIX}{user_id}:*"
    async for key in redis.scan_iter(pattern):
        await redis.delete(key)
