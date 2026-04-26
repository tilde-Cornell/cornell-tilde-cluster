import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "coordinator.sqlite3"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id        TEXT PRIMARY KEY,
                slurm_job_id  TEXT,
                submitted_by  TEXT NOT NULL DEFAULT '',
                submitted_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                cpus          INTEGER NOT NULL DEFAULT 1,
                mem_mb        INTEGER NOT NULL DEFAULT 512,
                -- output is retrieved from the container once and stored here so
                -- the coordinator never needs a shared host volume for job data.
                output        TEXT
            )
        """)


def save_job(job_id: str, slurm_job_id: str, submitted_by: str, cpus: int, mem_mb: int) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO jobs (job_id, slurm_job_id, submitted_by, cpus, mem_mb) VALUES (?,?,?,?,?)",
            (job_id, slurm_job_id, submitted_by, cpus, mem_mb),
        )


def store_output(job_id: str, output: str) -> None:
    with _conn() as conn:
        conn.execute("UPDATE jobs SET output = ? WHERE job_id = ?", (output, job_id))


def get_job(job_id: str) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


def list_jobs(limit: int = 100) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT job_id, slurm_job_id, submitted_by, submitted_at, cpus, mem_mb "
            "FROM jobs ORDER BY submitted_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
