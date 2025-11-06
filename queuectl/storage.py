# queuectl/storage.py
import sqlite3
import os
from datetime import datetime, timezone
from typing import Optional, Dict

DEFAULT_DB = os.environ.get("QUEUECTL_DB", "data/jobs.db")

def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

class Storage:
    def __init__(self, db_path: str = DEFAULT_DB):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        # isolation_level=None means we control transactions manually
        self.conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
              id TEXT PRIMARY KEY,
              command TEXT NOT NULL,
              state TEXT NOT NULL,
              attempts INTEGER NOT NULL DEFAULT 0,
              max_retries INTEGER NOT NULL DEFAULT 3,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              next_run_at TEXT NOT NULL,
              last_error TEXT,
              timeout_seconds INTEGER
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_state_next ON jobs(state, next_run_at);")
        cur.close()

    # ——— CRUD ———
    def enqueue(self, job: Dict) -> bool:
        now = iso_now()
        job_db = {
            "id": job["id"],
            "command": job["command"],
            "state": "pending",
            "attempts": int(job.get("attempts", 0)),
            "max_retries": int(job.get("max_retries", 3)),
            "created_at": now,
            "updated_at": now,
            "next_run_at": now,
            "last_error": job.get("last_error"),
            "timeout_seconds": job.get("timeout") or job.get("timeout_seconds")
        }
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO jobs (id,command,state,attempts,max_retries,created_at,updated_at,next_run_at,last_error,timeout_seconds)
                VALUES (:id,:command,:state,:attempts,:max_retries,:created_at,:updated_at,:next_run_at,:last_error,:timeout_seconds)
                """,
                job_db,
            )
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            cur.close()

    def claim_job(self, now_iso: str) -> Optional[Dict]:
        cur = self.conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            cur.execute(
                """
                SELECT id FROM jobs
                WHERE state='pending' AND next_run_at <= ?
                ORDER BY created_at
                LIMIT 1
                """,
                (now_iso,),
            )
            row = cur.fetchone()
            if not row:
                cur.execute("COMMIT")
                return None
            job_id = row["id"]
            updated = iso_now()
            cur.execute("UPDATE jobs SET state='processing', updated_at=? WHERE id=?", (updated, job_id))
            cur.execute("COMMIT")
            cur.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
            return dict(cur.fetchone())
        except Exception:
            cur.execute("ROLLBACK")
            raise
        finally:
            cur.close()

    def set_job_completed(self, job_id: str):
        cur = self.conn.cursor()
        now = iso_now()
        cur.execute("UPDATE jobs SET state='completed', updated_at=? WHERE id=?", (now, job_id))
        cur.close()

    def set_job_failed(self, job_id: str, attempts: int, max_retries: int, base: int, last_error: str):
        cur = self.conn.cursor()
        now = datetime.now(timezone.utc)
        now_iso = iso_now()
        if attempts >= max_retries:
            # move to DLQ
            cur.execute(
                "UPDATE jobs SET state='dead', attempts=?, last_error=?, updated_at=? WHERE id=?",
                (attempts, last_error, now_iso, job_id),
            )
        else:
            delay = base ** attempts
            next_run = datetime.fromtimestamp(now.timestamp() + delay, tz=timezone.utc)
            next_iso = next_run.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
            cur.execute(
                """
                UPDATE jobs
                SET state='pending', attempts=?, last_error=?, next_run_at=?, updated_at=?
                WHERE id=?
                """,
                (attempts, last_error, next_iso, now_iso, job_id),
            )
        cur.close()

    def list_jobs(self, state: Optional[str] = None):
        cur = self.conn.cursor()
        if state:
            cur.execute("SELECT * FROM jobs WHERE state=? ORDER BY created_at", (state,))
        else:
            cur.execute("SELECT * FROM jobs ORDER BY created_at")
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        return rows

    def get_stats(self):
        cur = self.conn.cursor()
        cur.execute("SELECT state, COUNT(*) as c FROM jobs GROUP BY state")
        data = {r["state"]: r["c"] for r in cur.fetchall()}
        cur.close()
        return data

    def set_pending_from_dead(self, job_id: str):
        cur = self.conn.cursor()
        now = iso_now()
        cur.execute(
            "UPDATE jobs SET state='pending', attempts=0, next_run_at=?, updated_at=? WHERE id=?",
            (now, now, job_id),
        )
        cur.close()
