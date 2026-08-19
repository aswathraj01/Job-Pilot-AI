"""Tests for LLM extraction service — mocked Gemini calls."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.extractor import calculate_confidence, extract_job_details


@pytest.mark.asyncio
async def test_extract_returns_all_schema_keys() -> None:
    mock_response = json.dumps({
        "title": "Senior Backend Engineer",
        "company": "Acme Corp",
        "location": "San Francisco, CA",
        "remote_type": "hybrid",
        "job_type": "full_time",
        "salary_min": 150000,
        "salary_max": 200000,
        "currency": "USD",
        "experience_years_min": 5,
        "experience_years_max": 8,
        "skills_required": ["Python", "FastAPI", "PostgreSQL"],
        "benefits": ["Health insurance", "401k"],
        "requirements": ["5+ years experience"],
        "responsibilities": ["Design APIs"],
        "application_deadline": "2024-12-31",
        "application_url": None,
        "source_platform": "linkedin",
        "job_id_on_platform": "123456",
        "description_summary": "A great backend role at Acme.",
    })

    with patch("app.services.extractor.genai") as mock_genai:
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=MagicMock(text=mock_response))
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.configure = MagicMock()
        mock_genai.GenerationConfig = MagicMock()

        result = await extract_job_details("Some job text", "https://linkedin.com/job/123")

    assert result["title"] == "Senior Backend Engineer"
    assert result["company"] == "Acme Corp"
    assert result["salary_min"] == 150000
    assert result["skills_required"] == ["Python", "FastAPI", "PostgreSQL"]
    assert result["application_url"] is None  # Null returned correctly


@pytest.mark.asyncio
async def test_extract_handles_malformed_json() -> None:
    """If LLM returns garbage, all fields should be null — no crash."""
    with patch("app.services.extractor.genai") as mock_genai:
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=MagicMock(text="NOT JSON AT ALL"))
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.configure = MagicMock()
        mock_genai.GenerationConfig = MagicMock()

        result = await extract_job_details("Some text", "https://example.com/job")

    assert result["title"] is None
    assert result["company"] is None


def test_confidence_score_full() -> None:
    extracted = {
        "title": "Engineer",
        "company": "ACME",
        "location": "NYC",
        "job_type": "full_time",
        "skills_required": ["Python"],
        "description_summary": "A good role.",
    }
    score = calculate_confidence(extracted)
    assert score == 1.0


def test_confidence_score_empty() -> None:
    extracted = {k: None for k in ["title", "company", "location", "job_type", "skills_required", "description_summary"]}
    score = calculate_confidence(extracted)
    assert score == 0.0
