"""
Resume matching service.
Uses Gemini to compare a user's resume skills against a job's requirements.
Returns a score (0-100), matched skills, skill gaps, and an AI summary.
"""
from __future__ import annotations

import json
from typing import Any

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

MATCH_SYSTEM_PROMPT = """You are a senior technical recruiter evaluating a candidate's fit for a job.
Given a resume and a job description, provide an honest assessment.

RULES:
1. Return ONLY valid JSON. No markdown, no explanation.
2. Be objective and fair — neither too optimistic nor too harsh.
3. score: integer 0-100 (100 = perfect match).
4. matched_skills: skills from the job requirements that the candidate clearly has.
5. gap_skills: skills the job requires that are missing or unclear from the resume.
6. ai_summary: 2-3 sentence recruiter-style summary of fit.
"""


def _build_match_prompt(resume_text: str, job_skills: list[str], job_description: str) -> str:
    return f"""Evaluate this candidate's fit for the job.

RESUME (truncated to 4000 chars):
---
{resume_text[:4000]}
---

JOB REQUIREMENTS:
Required Skills: {json.dumps(job_skills)}
Job Description (truncated):
---
{job_description[:2000]}
---

Return JSON:
{{
  "score": <integer 0-100>,
  "matched_skills": ["<skill>", ...],
  "gap_skills": ["<skill>", ...],
  "ai_summary": "<2-3 sentences>"
}}
"""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
async def match_resume_to_job(
    resume_text: str,
    resume_skills: list[str],
    job_skills: list[str],
    job_description: str,
) -> dict[str, Any]:
    """
    AI-powered resume ↔ job matching.
    Returns dict with score, matched_skills, gap_skills, ai_summary.
    """
    settings = get_settings()
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=MATCH_SYSTEM_PROMPT,
        generation_config=genai.GenerationConfig(
            temperature=0.1,
            max_output_tokens=1024,
            response_mime_type="application/json",
        ),
    )

    prompt = _build_match_prompt(resume_text, job_skills or [], job_description or "")
    logger.info("resume_match_start", skills_count=len(job_skills or []))

    response = await model.generate_content_async(prompt)
    raw = response.text.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("match_json_parse_error", raw=raw[:300])
        result = {"score": 0, "matched_skills": [], "gap_skills": job_skills, "ai_summary": "Matching failed."}

    # Clamp score
    result["score"] = max(0.0, min(100.0, float(result.get("score", 0))))
    return result


SKILL_EXTRACTION_PROMPT = """Extract a list of technical and professional skills from this resume.
Return ONLY a JSON array of skill strings. No markdown. No explanation.
Include: programming languages, frameworks, tools, methodologies, certifications, soft skills.
Example: ["Python", "FastAPI", "PostgreSQL", "Docker", "Agile", "REST API design"]
"""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
async def extract_resume_skills(resume_text: str) -> list[str]:
    """Extract skills from resume text using Gemini."""
    settings = get_settings()
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=SKILL_EXTRACTION_PROMPT,
        generation_config=genai.GenerationConfig(
            temperature=0.0,
            max_output_tokens=512,
            response_mime_type="application/json",
        ),
    )

    prompt = f"Resume text:\n{resume_text[:6000]}\n\nSkills JSON array:"
    response = await model.generate_content_async(prompt)

    try:
        skills = json.loads(response.text.strip())
        if isinstance(skills, list):
            return [str(s) for s in skills if s]
    except (json.JSONDecodeError, TypeError):
        pass
    return []
