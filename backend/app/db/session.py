"""
SQLAlchemy async database engine, session factory, and Base model.
Uses asyncpg driver for non-blocking PostgreSQL access.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


def _create_engine():
    settings = get_settings()
    return create_async_engine(
        settings.DATABASE_URL,
        echo=not settings.is_production,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )


# Lazily initialized engine and session factory
_engine = None
_async_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _create_engine()
    return _engine


def get_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async database session."""
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
