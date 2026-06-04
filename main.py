"""
main.py  —  Job Autopilot Orchestrator
Runs the full pipeline on a schedule: scrape → analyze → tailor → apply
"""
import sys
import yaml
from pathlib import Path
from datetime import datetime
from loguru import logger
from apscheduler.schedulers.blocking import BlockingScheduler

from database import init_db, job_seen, save_job, save_application, get_stats, pending_applications
from ai_engine import init_ai, analyze_match, tailor_resume, generate_cover_letter
from scraper import scrape_all
from applier import apply_to_job, build_resume_pdf

# ── Setup logging ─────────────────────────────────────────────────────────────

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}", colorize=True)
logger.add(LOG_DIR / "autopilot_{time:YYYY-MM-DD}.log", rotation="1 day", retention="14 days", level="DEBUG")


# ── Load config ───────────────────────────────────────────────────────────────

def load_config() -> dict:
    cfg_path = Path(__file__).parent / "config.yaml"
    if not cfg_path.exists():
        logger.error("config.yaml not found. Copy config.yaml and fill in your details.")
        sys.exit(1)
    with open(cfg_path) as f:
        return yaml.safe_load(f)


# ── Core cycle ────────────────────────────────────────────────────────────────

def run_cycle(config: dict, resume: str):
    logger.info("=" * 60)
    logger.info(f"Cycle started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    filters = config.get("filters", {})
    min_score    = filters.get("min_match_score", 65)
    exclude_kw   = [k.lower() for k in filters.get("exclude_keywords", [])]
    max_apps     = filters.get("max_applications_per_cycle", 5)
    resumes_dir  = Path(__file__).parent / "resumes"
    resumes_dir.mkdir(exist_ok=True)

    # 1. Scrape ─────────────────────────────────────────────────────────────
    jobs = scrape_all(config)
    new_jobs = [j for j in jobs if not job_seen(j["id"])]
    logger.info(f"New jobs found: {len(new_jobs)}")

    # 2. Analyze & filter ───────────────────────────────────────────────────
    qualified = []
    for job in new_jobs:
        if not job.get("description"):
            save_job({**job, "match_score": 0})
            continue

        # Quick keyword exclude check
        desc_lower = (job.get("description", "") + job.get("title", "")).lower()
        if any(kw in desc_lower for kw in exclude_kw):
            logger.info(f"Excluded (keyword filter): {job['title']}")
            save_job({**job, "match_score": -1})
            save_application(job["id"], "skipped", error="keyword filter")
            continue

        analysis = analyze_match(resume, job["description"], job["title"])
        score    = analysis.get("matchScore", 0)
        keywords = analysis.get("atsKeywords", [])

        job["match_score"] = score
        job["keywords"]    = keywords
        if not job["company"]:
            job["company"] = analysis.get("company", "")

        save_job(job)
        logger.info(f"[{score:3d}] {job['title']} @ {job['company']} ({job['source']})")

        if score >= min_score:
            qualified.append((job, analysis))

    # 3. Tailor + Apply ─────────────────────────────────────────────────────
    applied_count = 0
    for job, analysis in sorted(qualified, key=lambda x: x[1].get("matchScore", 0), reverse=True):
        if applied_count >= max_apps:
            break

        logger.info(f"Processing application: {job['title']} @ {job['company']} (score {job['match_score']})")

        try:
            kw             = analysis.get("atsKeywords", [])
            tailored       = tailor_resume(resume, job["description"], kw)
            cover_letter   = generate_cover_letter(tailored, job["description"],
                                                    company=job["company"], role=job["title"])

            # Save tailored resume PDF
            ts          = datetime.now().strftime("%Y%m%d_%H%M%S")
            slug        = "".join(c for c in job["title"][:30] if c.isalnum() or c == " ").replace(" ", "_")
            pdf_path    = str(resumes_dir / f"{slug}_{ts}.pdf")
            build_resume_pdf(tailored, pdf_path)

            # Apply
            success = apply_to_job(job, pdf_path, cover_letter, config)
            status  = "applied" if success else "failed"

            save_application(job["id"], status,
                             resume_path=pdf_path,
                             cover_letter=cover_letter,
                             tailored_resume=tailored)

            if success:
                applied_count += 1
                logger.success(f"Applied to {job['title']} @ {job['company']}")
            else:
                logger.warning(f"Apply failed / manual needed: {job['url']}")

        except Exception as e:
            logger.error(f"Application error for {job['id']}: {e}")
            save_application(job["id"], "failed", error=str(e))

    # 4. Stats ──────────────────────────────────────────────────────────────
    stats = get_stats()
    logger.info(
        f"Cycle done — "
        f"applied this cycle: {applied_count} | "
        f"total applied: {stats['applied']} | "
        f"total seen: {stats['total_seen']}"
    )
    logger.info("=" * 60)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    config = load_config()
    init_db()
    init_ai(config["anthropic_api_key"])

    resume_path = Path(__file__).parent / config.get("resume_file", "resume.txt")
    if not resume_path.exists():
        logger.error(f"Resume file not found: {resume_path}")
        sys.exit(1)
    resume = resume_path.read_text(encoding="utf-8")
    logger.info(f"Loaded resume ({len(resume)} chars)")

    interval = config.get("scheduler", {}).get("interval_minutes", 8)
    logger.info(f"Scheduler: every {interval} minutes")

    # Run immediately on startup
    run_cycle(config, resume)

    # Schedule repeating
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        run_cycle,
        "interval",
        minutes=interval,
        args=[config, resume],
        id="job_cycle",
        max_instances=1,
        coalesce=True,
    )

    logger.info("Autopilot running. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Autopilot stopped.")


if __name__ == "__main__":
    main()
