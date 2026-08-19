"""
Gmail OAuth2 email sync service.
Fetches email threads and links them to tracked jobs by company/subject matching.
"""
from __future__ import annotations

import base64
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_gmail_auth_url(state: str) -> str:
    """Build the Google OAuth2 authorization URL."""
    settings = get_settings()
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true", state=state)
    return url


def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    """Exchange OAuth2 authorization code for access + refresh tokens."""
    settings = get_settings()
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    return {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }


def _build_gmail_service(access_token: str, refresh_token: str | None, expiry: str | None):
    """Build an authenticated Gmail API service client."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    settings = get_settings()
    expiry_dt = None
    if expiry:
        try:
            expiry_dt = datetime.fromisoformat(expiry)
        except ValueError:
            pass

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        expiry=expiry_dt,
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _decode_header(encoded: str) -> str:
    """Decode a base64url-encoded email header value."""
    try:
        return base64.urlsafe_b64decode(encoded + "==").decode("utf-8", errors="replace")
    except Exception:
        return encoded


def fetch_job_related_threads(
    access_token: str,
    refresh_token: str | None,
    expiry: str | None,
    company_names: list[str],
    max_results: int = 50,
) -> list[dict[str, Any]]:
    """
    Search Gmail for threads related to job applications.
    Searches for emails mentioning company names or common hiring keywords.
    """
    service = _build_gmail_service(access_token, refresh_token, expiry)

    # Build search query
    company_query = " OR ".join(f'from:"{c}"' for c in company_names if c)
    keyword_query = "subject:(application OR interview OR offer OR recruiter OR position OR opportunity)"
    query = f"({company_query}) OR ({keyword_query})" if company_names else keyword_query

    try:
        response = (
            service.users()
            .threads()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        threads_meta = response.get("threads", [])
    except Exception as e:
        logger.error("gmail_list_threads_error", error=str(e))
        return []

    threads = []
    for meta in threads_meta[:20]:  # Limit detail fetches
        try:
            thread = (
                service.users()
                .threads()
                .get(userId="me", id=meta["id"], format="metadata", metadataHeaders=["Subject", "From", "Date"])
                .execute()
            )
            messages = thread.get("messages", [])
            if not messages:
                continue

            first_msg = messages[0]
            headers = {h["name"]: h["value"] for h in first_msg.get("payload", {}).get("headers", [])}

            threads.append(
                {
                    "gmail_thread_id": meta["id"],
                    "subject": headers.get("Subject", ""),
                    "from_email": headers.get("From", ""),
                    "snippet": thread.get("snippet", ""),
                    "message_count": len(messages),
                    "received_at": headers.get("Date"),
                }
            )
        except Exception as e:
            logger.warning("gmail_thread_fetch_error", thread_id=meta["id"], error=str(e))

    return threads


async def send_reminder_email(to_email: str, subject: str, body: str) -> bool:
    """Send a reminder email via SMTP."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    settings = get_settings()
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to_email
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())
        logger.info("reminder_email_sent", to=to_email, subject=subject)
        return True
    except Exception as e:
        logger.error("reminder_email_failed", to=to_email, error=str(e))
        return False
