"""
database.py  —  SQLite persistence for Job Autopilot
Tables: jobs, applications
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from loguru import logger

DB_PATH = Path(__file__).parent / "autopilot.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id          TEXT PRIMARY KEY,
            title       TEXT,
            company     TEXT,
            location    TEXT,
            url         TEXT,
            source      TEXT,
            description TEXT,
            match_score INTEGER DEFAULT 0,
            keywords    TEXT,
            seen_at     TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS applications (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id          TEXT REFERENCES jobs(id),
            status          TEXT,           -- pending | applied | failed | skipped
            resume_path     TEXT,
            cover_letter    TEXT,
            tailored_resume TEXT,
            applied_at      TEXT DEFAULT (datetime('now')),
            error_msg       TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_seen ON jobs(seen_at);
        CREATE INDEX IF NOT EXISTS idx_apps_status ON applications(status);
    """)
    conn.commit()
    conn.close()
    logger.info(f"DB ready at {DB_PATH}")


def job_seen(job_id: str) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    return row is not None


def save_job(job: dict):
    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO jobs (id, title, company, location, url, source, description, match_score, keywords)
        VALUES (:id, :title, :company, :location, :url, :source, :description, :match_score, :keywords)
    """, {**job, "keywords": json.dumps(job.get("keywords", []))})
    conn.commit()
    conn.close()


def save_application(job_id: str, status: str, resume_path: str = "",
                     cover_letter: str = "", tailored_resume: str = "", error: str = ""):
    conn = get_conn()
    conn.execute("""
        INSERT INTO applications (job_id, status, resume_path, cover_letter, tailored_resume, error_msg)
        VALUES (?,?,?,?,?,?)
    """, (job_id, status, resume_path, cover_letter, tailored_resume, error))
    conn.commit()
    conn.close()


def get_stats() -> dict:
    conn = get_conn()
    total   = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    applied = conn.execute("SELECT COUNT(*) FROM applications WHERE status='applied'").fetchone()[0]
    failed  = conn.execute("SELECT COUNT(*) FROM applications WHERE status='failed'").fetchone()[0]
    skipped = conn.execute("SELECT COUNT(*) FROM applications WHERE status='skipped'").fetchone()[0]
    recent  = conn.execute("""
        SELECT j.title, j.company, a.status, a.applied_at
        FROM applications a JOIN jobs j ON j.id=a.job_id
        ORDER BY a.applied_at DESC LIMIT 10
    """).fetchall()
    conn.close()
    return {
        "total_seen": total,
        "applied": applied,
        "failed": failed,
        "skipped": skipped,
        "recent": [dict(r) for r in recent],
    }


def pending_applications(limit=5):
    conn = get_conn()
    rows = conn.execute("""
        SELECT j.* FROM jobs j
        WHERE j.id NOT IN (SELECT job_id FROM applications)
        AND j.match_score >= 65
        ORDER BY j.match_score DESC, j.seen_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
