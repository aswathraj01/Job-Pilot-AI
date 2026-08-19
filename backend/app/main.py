"""
FastAPI application entry point.
Registers all routers, middleware, startup/shutdown hooks, and OpenAPI config.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api import analytics, auth, email, jobs, resume
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("app_starting", env=settings.APP_ENV, version=settings.APP_VERSION)
    yield
    logger.info("app_shutdown")


app = FastAPI(
    title="Job-Pilot-AI API",
    description=(
        "AI-powered job application tracker. "
        "Paste a job URL — we extract every detail, track your pipeline, and match your resume."
    ),
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

prefix = settings.API_PREFIX
app.include_router(auth.router, prefix=prefix)
app.include_router(jobs.router, prefix=prefix)
app.include_router(analytics.router, prefix=prefix)
app.include_router(resume.router, prefix=prefix)
app.include_router(email.router, prefix=prefix)


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok", "version": settings.APP_VERSION, "env": settings.APP_ENV}


@app.get("/", tags=["Health"])
async def root() -> dict:
    return {"message": "Job-Pilot-AI API", "docs": "/api/docs"}
