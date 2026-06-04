"""
ai_engine.py  —  Claude-powered analysis, resume tailoring, cover letter
"""
import json
import re
import anthropic
from loguru import logger

_client = None


def init_ai(api_key: str):
    global _client
    _client = anthropic.Anthropic(api_key=api_key)
    logger.info("Anthropic client ready")


def _call(prompt: str, max_tokens: int = 1500) -> str:
    msg = _client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


# ── 1. Analyze match ──────────────────────────────────────────────────────────

def analyze_match(resume: str, job_description: str, job_title: str = "") -> dict:
    """Return match analysis as a dict. Keys: matchScore, matchingSkills,
    missingSkills, atsKeywords, summary."""
    prompt = f"""Analyze this resume against the job description. Reply ONLY with valid JSON, no markdown.

RESUME:
{resume}

JOB DESCRIPTION:
{job_description}

JSON schema (fill every field):
{{
  "matchScore": <integer 0-100>,
  "jobTitle": "<extracted title>",
  "company": "<extracted company>",
  "matchingSkills": ["skill", ...],
  "missingSkills":  ["skill", ...],
  "atsKeywords":    ["keyword", ...],
  "summary": "<2 sentence assessment>"
}}"""
    try:
        text = _call(prompt, max_tokens=800)
        clean = re.sub(r"```json|```", "", text).strip()
        return json.loads(clean)
    except Exception as e:
        logger.error(f"analyze_match failed: {e}")
        return {"matchScore": 0, "matchingSkills": [], "missingSkills": [],
                "atsKeywords": [], "summary": "Analysis failed.", "jobTitle": job_title, "company": ""}


# ── 2. Tailor resume ──────────────────────────────────────────────────────────

def tailor_resume(resume: str, job_description: str, keywords: list[str]) -> str:
    """Rewrite resume for ATS and role fit. Returns complete resume text."""
    kw_str = ", ".join(keywords[:20])
    prompt = f"""Tailor this resume for the job below. Requirements:
- Naturally incorporate these ATS keywords: {kw_str}
- Rewrite the professional summary for this specific role
- Reorder/reframe bullet points to highlight relevant experience first
- Keep all factual information accurate — do not fabricate achievements
- Return the complete resume text only, no commentary

ORIGINAL RESUME:
{resume}

JOB DESCRIPTION:
{job_description}"""
    try:
        return _call(prompt, max_tokens=2000)
    except Exception as e:
        logger.error(f"tailor_resume failed: {e}")
        return resume  # fallback to original


# ── 3. Cover letter ───────────────────────────────────────────────────────────

def generate_cover_letter(resume: str, job_description: str,
                          company: str = "", role: str = "") -> str:
    """Generate a targeted cover letter. Returns letter text."""
    ctx = f"Role: {role} at {company}" if company else ""
    prompt = f"""Write a compelling 3-paragraph cover letter for this job application.
Structure: (1) Strong opening hook with genuine enthusiasm for the specific role/company.
(2) 2-3 concrete achievements from the resume that directly address the job requirements.
(3) Confident call to action. Under 280 words. Return the letter text only.
{ctx}

RESUME:
{resume}

JOB DESCRIPTION:
{job_description}"""
    try:
        return _call(prompt, max_tokens=700)
    except Exception as e:
        logger.error(f"generate_cover_letter failed: {e}")
        return ""
