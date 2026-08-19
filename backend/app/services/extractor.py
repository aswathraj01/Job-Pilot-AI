"""
LLM extraction service using Google Gemini 1.5 Flash.
Extracts structured JSON from raw job posting text.
Policy: return null for missing fields — NEVER hallucinate.
"""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ─── JSON Schema sent to Gemini ───────────────────────────────────────────────
EXTRACTION_SCHEMA = {
    "title": "string | null — Job title exactly as written",
    "company": "string | null — Company name",
    "location": "string | null — City, State, Country or 'Remote'",
    "remote_type": "onsite | remote | hybrid | null",
    "job_type": "full_time | part_time | contract | internship | freelance | null",
    "salary_min": "number | null — Minimum annual salary in numeric form",
    "salary_max": "number | null — Maximum annual salary in numeric form",
    "currency": "string | null — ISO 4217 code e.g. USD, EUR, GBP",
    "experience_years_min": "integer | null — Minimum years of experience required",
    "experience_years_max": "integer | null — Maximum years of experience preferred",
    "skills_required": "array of strings | null — Technical and soft skills listed",
    "benefits": "array of strings | null — Benefits and perks listed",
    "requirements": "array of strings | null — Must-have qualifications",
    "responsibilities": "array of strings | null — Key job duties",
    "application_deadline": "string | null — Application deadline date as written",
    "application_url": "string | null — Direct application link if different from the posting URL",
    "source_platform": "string | null — Platform name e.g. linkedin, indeed, greenhouse, lever, workday",
    "job_id_on_platform": "string | null — The platform's own job ID if visible",
    "description_summary": "string | null — 2-3 sentence summary of the role",
}

SYSTEM_PROMPT = """You are a precise job posting parser. Your ONLY task is to extract structured data from job posting text.

RULES (strictly enforced):
1. Return ONLY valid JSON that matches the schema. No markdown, no explanation, no prose.
2. Use null for ANY field where the information is not explicitly stated in the text.
3. NEVER infer, guess, or hallucinate data. If it's not in the text, it's null.
4. For salary: convert to annual figures. If hourly rate given, multiply by 2080. Keep null if uncertain.
5. For skills_required: extract ONLY skills explicitly mentioned, not implied ones.
6. For remote_type: use "remote" only if explicitly stated as fully remote.
7. For source_platform: infer from URL patterns (linkedin.com → "linkedin", etc.).
"""


def _build_user_prompt(text: str, url: str) -> str:
    # Truncate to avoid token limits (keep first 8000 chars — most job descriptions are <4000)
    truncated = text[:8000] if len(text) > 8000 else text
    return f"""Extract job data from this posting.

Source URL: {url}

Job Posting Text:
---
{truncated}
---

Return JSON matching exactly this schema (use null for missing fields):
{json.dumps(EXTRACTION_SCHEMA, indent=2)}

JSON output only:"""


def _clean_llm_json(raw: str) -> str:
    """Strip markdown code fences if Gemini wraps the JSON."""
    raw = raw.strip()
    # Remove ```json ... ``` wrapping
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if match:
        return match.group(1).strip()
    return raw


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def extract_job_details(text: str, url: str) -> dict[str, Any]:
    """
    Call Gemini 1.5 Flash to extract structured job data.
    Returns a dict with all schema fields (nulls for missing data).
    Retries up to 3 times on API errors.
    """
    settings = get_settings()
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT,
        generation_config=genai.GenerationConfig(
            temperature=0.0,       # Deterministic — no creativity wanted
            max_output_tokens=2048,
            response_mime_type="application/json",
        ),
    )

    prompt = _build_user_prompt(text, url)

    logger.info("llm_extraction_start", url=url, text_len=len(text))
    response = await model.generate_content_async(prompt)
    raw_output = response.text
    logger.info("llm_extraction_done", url=url, response_len=len(raw_output))

    cleaned = _clean_llm_json(raw_output)

    try:
        extracted: dict[str, Any] = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("llm_json_parse_error", raw=raw_output[:500], error=str(e))
        # Return a null-filled dict rather than crashing
        extracted = {k: None for k in EXTRACTION_SCHEMA}

    # Ensure all schema keys exist (null if missing)
    for key in EXTRACTION_SCHEMA:
        extracted.setdefault(key, None)

    extracted["_raw_response"] = raw_output
    extracted["_extracted_at"] = datetime.now(UTC).isoformat()

    return extracted


def calculate_confidence(extracted: dict[str, Any]) -> float:
    """
    Heuristic confidence score based on how many fields were successfully extracted.
    Score 0.0–1.0.
    """
    key_fields = ["title", "company", "location", "job_type", "skills_required", "description_summary"]
    filled = sum(1 for k in key_fields if extracted.get(k) is not None)
    return round(filled / len(key_fields), 2)
