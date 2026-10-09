"""Run log: what the offline jobs did, step by step, with timestamps.

The web app only views data that offline scripts produce, so it needs to know
whether that data is current and, when it is not, which step failed. Every job
records itself here (`job_runs`, one row per run; `job_steps`, one row per step):

    with runlog.run("daily", args={...}, plan=[("prices", "us", "Prices"), ...]) as r:
        with r.step("prices", "us") as s:
            result = refresh(...)
            s.detail = "3,402 / 3,412 symbols · newest bar 2 Oct"
            s.stats = {...}

A job's *plan* is written up front, so the web app's Status page shows the
steps still to come while a run is in progress. A step that raises is recorded
as failed (with the error) and, unless `critical=True`, the job carries on —
one market failing must not stop the other. Steps a run never reached are
marked skipped. Standalone commands use `runlog.track(job, step)` to record
a one-step run.

Recording never breaks a job: if Postgres is unreachable the job runs exactly
as before, just unlogged.
"""

import contextlib
import json
import logging
import os
import socket
import time
import traceback

from .marketdata import db

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS job_runs (
    id SERIAL PRIMARY KEY,
    job TEXT NOT NULL,                       -- daily | prices | breadth | industries | ...
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',  -- running | ok | partial | failed
    args JSONB,
    host TEXT,
    pid INT,
    log_path TEXT,
    summary TEXT
);
CREATE TABLE IF NOT EXISTS job_steps (
    id SERIAL PRIMARY KEY,
    run_id INT NOT NULL REFERENCES job_runs(id) ON DELETE CASCADE,
    seq INT NOT NULL,
    step TEXT NOT NULL,
    market TEXT,
    label TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | running | ok | failed | skipped
    detail TEXT,
    error TEXT,
    stats JSONB
);
CREATE INDEX IF NOT EXISTS job_steps_run ON job_steps (run_id, seq);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _exec(sql: str, params: tuple = (), fetch: bool = False):
    """Run one statement; swallow (and log) database errors so a job never fails because of its log."""
    try:
        with db.get_connection().cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone() if fetch else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("run log not written (%s: %s)", type(exc).__name__, exc)
        return None


class Step:
    def __init__(self, run: "Run", row_id: int | None, critical: bool):
        self.run, self.id, self.critical = run, row_id, critical
        self.detail: str | None = None
        self.stats: dict | None = None
        self.status: str | None = None   # set "skipped" to record a deliberate skip
        self.ok = True
        self._progress_at = 0.0

    def skip(self, why: str) -> None:
        self.status, self.detail = "skipped", why

    def progress(self, text: str, every: float = 2.0) -> None:
        """Live progress for a long step: written to the step's `detail` while it still runs, so the
        Runs page shows movement instead of a silent step. Call it as often as you like — writes are
        throttled to one per `every` seconds. The final `detail` set at the end overwrites it; if the
        step crashes instead, the last progress line stays, showing how far it got."""
        self.detail = text
        now = time.monotonic()
        if self.id is None or now - self._progress_at < every:
            return
        self._progress_at = now
        _exec("UPDATE job_steps SET detail=%s WHERE id=%s", (text, self.id))


class Run:
    def __init__(self, job: str, args: dict | None = None, plan: list[tuple] | None = None, log_path=None):
        self.job, self.id, self.failed_steps, self.critical_failure = job, None, [], False
        self._seq = 0
        try:
            init_schema()
        except Exception as exc:  # noqa: BLE001
            logger.warning("run log unavailable (%s)", exc)
            return
        row = _exec("INSERT INTO job_runs (job, args, host, pid, log_path) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                    (job, json.dumps(args or {}, default=str), socket.gethostname(), os.getpid(),
                     str(log_path) if log_path else None), fetch=True)
        self.id = row[0] if row else None
        for step, market, label in plan or []:
            self._seq += 1
            _exec("INSERT INTO job_steps (run_id, seq, step, market, label) VALUES (%s,%s,%s,%s,%s)",
                  (self.id, self._seq, step, market, label))

    @contextlib.contextmanager
    def step(self, step: str, market: str | None = None, label: str | None = None, critical: bool = False):
        row = None
        if self.id is not None:
            row = _exec("""UPDATE job_steps SET status='running', started_at=now() WHERE id = (
                             SELECT id FROM job_steps WHERE run_id=%s AND step=%s AND market IS NOT DISTINCT FROM %s
                             AND status='pending' ORDER BY seq LIMIT 1) RETURNING id""", (self.id, step, market), fetch=True)
            if not row:  # not in the plan: append it
                self._seq += 1
                row = _exec("""INSERT INTO job_steps (run_id, seq, step, market, label, status, started_at)
                               VALUES (%s, %s, %s, %s, %s, 'running', now()) RETURNING id""",
                            (self.id, self._seq, step, market, label or step), fetch=True)
        s = Step(self, row[0] if row else None, critical)
        try:
            yield s
        except Exception as exc:  # noqa: BLE001
            s.ok = False
            self.failed_steps.append(f"{step}{'/' + market if market else ''}")
            err = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            tb = traceback.format_exc(limit=-4)
            logger.exception("step %s %s failed", step, market or "")
            if s.id is not None:
                _exec("UPDATE job_steps SET status='failed', finished_at=now(), detail=%s, error=%s, stats=%s WHERE id=%s",
                      (s.detail, f"{err}\n\n{tb}", json.dumps(s.stats, default=str) if s.stats else None, s.id))
            if critical:
                self.critical_failure = True
                raise
        else:
            if s.id is not None:
                _exec("UPDATE job_steps SET status=%s, finished_at=now(), detail=%s, stats=%s WHERE id=%s",
                      (s.status or "ok", s.detail, json.dumps(s.stats, default=str) if s.stats else None, s.id))

    def finish(self, summary: str | None = None, stopped: bool = False) -> str:
        status = "failed" if self.critical_failure else "partial" if self.failed_steps else "ok"
        if self.id is not None and stopped:  # stopped from outside (Stop button, Ctrl+C): the step in progress did not finish
            _exec("UPDATE job_steps SET status='failed', finished_at=now(), error='stopped before it finished' WHERE run_id=%s AND status='running'",
                  (self.id,))
            summary = summary or "stopped"
        if self.id is not None:
            _exec("UPDATE job_steps SET status='skipped', detail=COALESCE(detail, 'not reached') WHERE run_id=%s AND status IN ('pending','running')",
                  (self.id,))
            _exec("UPDATE job_runs SET status=%s, finished_at=now(), summary=%s WHERE id=%s",
                  (status, summary or (f"failed: {', '.join(self.failed_steps)}" if self.failed_steps else None), self.id))
        return status


@contextlib.contextmanager
def run(job: str, args: dict | None = None, plan: list[tuple] | None = None, log_path=None):
    r = Run(job, args, plan, log_path)
    try:
        yield r
    except BaseException as exc:
        r.critical_failure = True
        r.finish(stopped=isinstance(exc, (KeyboardInterrupt, SystemExit)))
        raise
    else:
        r.finish()


@contextlib.contextmanager
def track(job: str, step: str | None = None, market: str | None = None, label: str | None = None, args: dict | None = None):
    """A standalone command as a one-step run: `with runlog.track("breadth", market="us") as s: ...`"""
    step = step or job
    with run(job, args=args or ({"market": market} if market else None), plan=[(step, market, label or step)]) as r:
        with r.step(step, market, critical=True) as s:
            yield s
