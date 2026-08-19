"""Tests for Jobs API."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_job(client: AsyncClient, auth_headers: dict) -> None:
    with patch("app.api.jobs.process_job_url") as mock_task:
        mock_task.delay.return_value = None
        resp = await client.post(
            "/api/v1/jobs/",
            headers=auth_headers,
            json={"url": "https://example.com/job/123"},
        )
    assert resp.status_code == 202
    data = resp.json()
    assert data["url"] == "https://example.com/job/123"
    assert data["status"] == "processing"


@pytest.mark.asyncio
async def test_create_duplicate_job(client: AsyncClient, auth_headers: dict) -> None:
    with patch("app.api.jobs.process_job_url") as mock_task:
        mock_task.delay.return_value = None
        await client.post("/api/v1/jobs/", headers=auth_headers, json={"url": "https://dupe.com/job/1"})
        resp = await client.post("/api/v1/jobs/", headers=auth_headers, json={"url": "https://dupe.com/job/1"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_jobs(client: AsyncClient, auth_headers: dict) -> None:
    resp = await client.get("/api/v1/jobs/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_job_not_found(client: AsyncClient, auth_headers: dict) -> None:
    import uuid
    resp = await client.get(f"/api/v1/jobs/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_job_status(client: AsyncClient, auth_headers: dict) -> None:
    with patch("app.api.jobs.process_job_url") as mock_task:
        mock_task.delay.return_value = None
        create_resp = await client.post(
            "/api/v1/jobs/",
            headers=auth_headers,
            json={"url": "https://example.com/job/update-test"},
        )
    job_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/api/v1/jobs/{job_id}",
        headers=auth_headers,
        json={"status": "applied"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "applied"


@pytest.mark.asyncio
async def test_add_note(client: AsyncClient, auth_headers: dict) -> None:
    with patch("app.api.jobs.process_job_url") as mock_task:
        mock_task.delay.return_value = None
        create_resp = await client.post(
            "/api/v1/jobs/",
            headers=auth_headers,
            json={"url": "https://example.com/job/note-test"},
        )
    job_id = create_resp.json()["id"]
    resp = await client.post(
        f"/api/v1/jobs/{job_id}/notes",
        headers=auth_headers,
        json={"content": "Great company, follow up next week"},
    )
    assert resp.status_code == 201
    assert resp.json()["content"] == "Great company, follow up next week"


@pytest.mark.asyncio
async def test_delete_job(client: AsyncClient, auth_headers: dict) -> None:
    with patch("app.api.jobs.process_job_url") as mock_task:
        mock_task.delay.return_value = None
        create_resp = await client.post(
            "/api/v1/jobs/",
            headers=auth_headers,
            json={"url": "https://example.com/job/delete-test"},
        )
    job_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/v1/jobs/{job_id}", headers=auth_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_jobs_require_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/jobs/")
    assert resp.status_code == 403
