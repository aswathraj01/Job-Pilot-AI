"""
Core application configuration using pydantic-settings.
All values are read from environment variables or .env file.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AnyHttpUrl, PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_NAME: str = "Job-Pilot-AI"
    APP_VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"

    # ── API ──────────────────────────────────────────────────────────────
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v

    # ── Database ─────────────────────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "jobpilot"
    POSTGRES_USER: str = "jobpilot"
    POSTGRES_PASSWORD: str = "changeme"
    DATABASE_URL: str = ""

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return self

    # ── Redis ─────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── JWT ───────────────────────────────────────────────────────────────
    JWT_PRIVATE_KEY_PATH: str = "./keys/private.pem"
    JWT_PUBLIC_KEY_PATH: str = "./keys/public.pem"
    JWT_PRIVATE_KEY_RAW: str = ""
    JWT_PUBLIC_KEY_RAW: str = ""
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @property
    def jwt_private_key(self) -> str:
        if self.JWT_PRIVATE_KEY_RAW:
            # Replace literal \n with actual newlines in case it's passed as a single string
            return self.JWT_PRIVATE_KEY_RAW.replace("\\n", "\n")
        return Path(self.JWT_PRIVATE_KEY_PATH).read_text()

    @property
    def jwt_public_key(self) -> str:
        if self.JWT_PUBLIC_KEY_RAW:
            return self.JWT_PUBLIC_KEY_RAW.replace("\\n", "\n")
        return Path(self.JWT_PUBLIC_KEY_PATH).read_text()

    # ── LLM ──────────────────────────────────────────────────────────────
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    LLM_MAX_RETRIES: int = 3
    LLM_TIMEOUT_SECONDS: int = 60

    # ── Gmail OAuth2 ──────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/email/callback"

    # ── SMTP ─────────────────────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@jobpilot.ai"

    # ── Frontend ─────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance. Use as FastAPI dependency."""
    return Settings()
