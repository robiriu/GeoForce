"""SQLite job queue for the Waiwera simulation campaign.

Producer: VPS, called from `simulation/campaign.py` to enqueue scenarios.
Consumer: Kaggle notebook, claims a job-range and writes results back
(status, runtime_s, output_path, error).

States: pending -> running -> {done, failed}. A worker claims a job by
atomically updating its state from pending to running together with its
worker_id. Idempotent: claiming the same job twice raises.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "queue.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    scenario_id   TEXT PRIMARY KEY,
    params_json   TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('pending', 'running', 'done', 'failed')) DEFAULT 'pending',
    worker_id     TEXT,
    output_path   TEXT,
    runtime_s     REAL,
    error         TEXT,
    enqueued_at   REAL NOT NULL,
    started_at    REAL,
    finished_at   REAL
);
CREATE INDEX IF NOT EXISTS jobs_status_idx ON jobs (status);
"""


@dataclass(frozen=True)
class Job:
    scenario_id: str
    params: dict
    status: str
    worker_id: str | None
    output_path: str | None
    runtime_s: float | None
    error: str | None


def connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    return conn


def enqueue(conn: sqlite3.Connection, scenario_id: str, params: dict) -> None:
    """Insert a job; no-op if the scenario is already in the queue."""
    conn.execute(
        "INSERT OR IGNORE INTO jobs (scenario_id, params_json, enqueued_at) VALUES (?, ?, ?)",
        (scenario_id, json.dumps(params, sort_keys=True), time.time()),
    )


def claim(conn: sqlite3.Connection, worker_id: str, n: int = 1) -> list[Job]:
    """Atomically claim up to `n` pending jobs for `worker_id`. FIFO."""
    out: list[Job] = []
    for _ in range(n):
        cur = conn.execute(
            """
            UPDATE jobs SET status='running', worker_id=?, started_at=?
            WHERE scenario_id = (
              SELECT scenario_id FROM jobs WHERE status='pending'
              ORDER BY enqueued_at ASC LIMIT 1
            )
            RETURNING scenario_id, params_json, status, worker_id, output_path, runtime_s, error
            """,
            (worker_id, time.time()),
        )
        row = cur.fetchone()
        if row is None:
            break
        out.append(
            Job(
                scenario_id=row[0],
                params=json.loads(row[1]),
                status=row[2],
                worker_id=row[3],
                output_path=row[4],
                runtime_s=row[5],
                error=row[6],
            )
        )
    return out


def mark_done(conn: sqlite3.Connection, scenario_id: str, output_path: str, runtime_s: float) -> None:
    conn.execute(
        "UPDATE jobs SET status='done', output_path=?, runtime_s=?, finished_at=? WHERE scenario_id=?",
        (output_path, runtime_s, time.time(), scenario_id),
    )


def mark_failed(conn: sqlite3.Connection, scenario_id: str, error: str) -> None:
    conn.execute(
        "UPDATE jobs SET status='failed', error=?, finished_at=? WHERE scenario_id=?",
        (error[:4096], time.time(), scenario_id),
    )


def stats(conn: sqlite3.Connection) -> dict[str, int]:
    cur = conn.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status")
    return {row[0]: int(row[1]) for row in cur.fetchall()}
