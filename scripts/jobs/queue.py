"""Job queue: the portal, schedules and the command line ask for work here; one worker runs it.

Everything that wants a job run goes through this module's functions — never the tables directly — so the
backend can be swapped (RQ or Celery would implement these same functions) without touching the portal,
the command line or the jobs themselves:

    enqueue(targets, market, opts, requested_by)  ask for a run (a duplicate of a waiting one is not added)
    items() / get(id) / position(id)              what is queued, running and recently finished
    cancel(id)                                    drop a waiting item, or stop the running one
    to_front(id)                                  run a waiting item next
    claim_next() / mark_running() / finish()      the worker's side
    heartbeat() / worker_status()                 is a worker alive, and what is it doing

Schedules ("daily · India at 18:30, Mon–Fri") live here too: `due_schedules()` is what the worker checks
every minute; a due schedule simply enqueues its run. A slot missed while the machine slept runs once
when the worker next looks — not once per missed day.

A queue item is a request: targets (jobs / pipelines), market ("all" or one), options (the `jobs run`
flags as JSON). The worker runs it as `python -m jobs run ...`, so the run log (`swing_screener/runlog.py`)
stays the record of what happened, whoever asked for it.
"""

from __future__ import annotations

import datetime as dt
import json

from swing_screener.marketdata import db

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
WORKER_ALIVE_S = 20          # a worker that has not checked in for this long is considered stopped
LOCK_KEY = 742_003_117       # pg advisory lock: one worker at a time

SCHEMA = """
CREATE TABLE IF NOT EXISTS job_queue (
    id SERIAL PRIMARY KEY,
    targets JSONB NOT NULL,                  -- ["daily"] / ["prices", "breadth"]
    market TEXT NOT NULL DEFAULT 'all',
    opts JSONB NOT NULL DEFAULT '{}',        -- strategies, force, from, allow_stale, ...
    requested_by TEXT NOT NULL DEFAULT 'you',-- you | schedule | command line | breadth page
    schedule_id INT,
    priority INT NOT NULL DEFAULT 0,         -- higher runs first; FIFO within a priority
    status TEXT NOT NULL DEFAULT 'queued',   -- queued | running | ok | failed | stopped | cancelled | interrupted
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    pid INT,
    run_id INT,                              -- job_runs.id of the run it produced
    exit_code INT,
    cancel_requested BOOLEAN NOT NULL DEFAULT false,
    command TEXT,
    out_path TEXT,
    note TEXT
);
CREATE INDEX IF NOT EXISTS job_queue_status ON job_queue (status, priority DESC, id);
CREATE TABLE IF NOT EXISTS job_schedules (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    targets JSONB NOT NULL,
    market TEXT NOT NULL DEFAULT 'all',
    opts JSONB NOT NULL DEFAULT '{}',
    days TEXT NOT NULL DEFAULT 'mon,tue,wed,thu,fri',   -- weekdays it runs on (ignored when monthday is set)
    monthday INT,                                       -- 1..28: monthly, on this day
    at_time TEXT NOT NULL DEFAULT '18:30',              -- local time, HH:MM
    enabled BOOLEAN NOT NULL DEFAULT true,
    last_slot TIMESTAMPTZ,                              -- the latest slot already enqueued
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS job_worker (
    id INT PRIMARY KEY DEFAULT 1,
    pid INT, host TEXT, started_at TIMESTAMPTZ, heartbeat_at TIMESTAMPTZ, current_item INT, note TEXT
);
"""

# The default schedules (created once, when the table is empty). Times are this machine's local time
# and assume India: NSE closes 15:30 IST and its data settles by ~17:30; the NYSE closes ~01:30/02:30 IST.
DEFAULT_SCHEDULES = [
    {"name": "Daily data · India", "targets": ["daily"], "market": "india", "days": "mon,tue,wed,thu,fri", "at_time": "18:30"},
    {"name": "Daily data · US", "targets": ["daily"], "market": "us", "days": "tue,wed,thu,fri,sat", "at_time": "07:00"},
    {"name": "Weekly reference data", "targets": ["weekly"], "market": "all", "days": "sat", "at_time": "10:00"},
    {"name": "Monthly classification", "targets": ["monthly"], "market": "all", "monthday": 1, "at_time": "09:00"},
]

_COLS = ("id, targets, market, opts, requested_by, schedule_id, priority, status, created_at, started_at, finished_at, "
         "pid, run_id, exit_code, cancel_requested, command, out_path, note")
_SCOLS = "id, name, targets, market, opts, days, monthday, at_time, enabled, last_slot, created_at"
_ACTIVE = ("queued", "running")


def _q(sql: str, params: tuple = (), fetch: str | None = "all"):
    with db.get_connection().cursor() as cur:
        cur.execute(sql, params)
        if fetch == "all":
            return cur.fetchall()
        if fetch == "one":
            return cur.fetchone()
        return None


_ready = False


def init_schema() -> None:
    global _ready
    if _ready:
        return
    _q(SCHEMA, fetch=None)
    if not _q("SELECT 1 FROM job_schedules LIMIT 1"):
        for s in DEFAULT_SCHEDULES:
            save_schedule(s)
    _ready = True


def _iso(t):
    return t.isoformat() if t else None


def _item(r) -> dict:
    keys = [k.strip() for k in _COLS.split(",")]
    d = dict(zip(keys, r))
    for k in ("created_at", "started_at", "finished_at"):
        d[k] = _iso(d[k])
    return d


def command_for(targets: list, market: str, opts: dict) -> list[str]:
    """The `python -m jobs run` arguments for a request (also shown in the portal)."""
    cmd = ["run", *targets, "--market", market or "all"]
    if opts.get("strategies"):
        s = opts["strategies"]
        cmd += ["--strategies", s if isinstance(s, str) else ",".join(s)]
    if opts.get("from"):
        cmd += ["--from", str(opts["from"])]
    for flag in ("force", "allow_stale", "no_ingest"):
        if opts.get(flag):
            cmd.append("--" + flag.replace("_", "-"))
    for k in ("universe_days", "quality_top", "days", "start", "sample"):
        if opts.get(k) is not None:
            cmd += ["--" + k.replace("_", "-"), str(opts[k])]
    # repeatable flags, one occurrence per value. Anything missing here is silently
    # dropped on the way to the worker's subprocess: --vcp was stored in opts and
    # honoured by the backtest job, but never reached it, so the variant ran the
    # shipped rules and looked like it had succeeded.
    for kv in (opts.get("vcp") or []):
        cmd += ["--vcp", str(kv)]
    for kv in (opts.get("const") or []):
        cmd += ["--const", str(kv)]
    if opts.get("accept_labels"):
        cmd += ["--accept-labels", str(opts["accept_labels"])]
    return cmd


# ------------------------------------------------------------------ asking for work

def enqueue(targets: list, market: str = "all", opts: dict | None = None, requested_by: str = "you",
            schedule_id: int | None = None, priority: int = 0, skip_if_running: bool = False) -> dict:
    """Ask for a run. Returns the queue item; an identical request still waiting is returned instead of a
    second copy (and, with skip_if_running, one already running too — what schedules use)."""
    init_schema()
    opts = {k: v for k, v in (opts or {}).items() if v not in (None, False, "", [])}
    same = _q(f"""SELECT {_COLS} FROM job_queue WHERE status = ANY(%s) AND targets = %s::jsonb AND market = %s AND opts = %s::jsonb
                  ORDER BY id LIMIT 1""", (["queued", "running"] if skip_if_running else ["queued"], json.dumps(targets), market,
                                          json.dumps(opts, sort_keys=True)), fetch="one")
    if same:
        return {**_item(same), "duplicate": True}
    r = _q(f"""INSERT INTO job_queue (targets, market, opts, requested_by, schedule_id, priority, command)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING {_COLS}""",
           (json.dumps(targets), market, json.dumps(opts, sort_keys=True), requested_by, schedule_id, priority,
            "python -m jobs " + " ".join(command_for(targets, market, opts))), fetch="one")
    return _item(r)


def items(recent: int = 15) -> dict:
    """{"running": item|None, "queued": [...] in run order, "recent": [...] newest first}."""
    init_schema()
    act = [_item(r) for r in _q(f"SELECT {_COLS} FROM job_queue WHERE status = ANY(%s) ORDER BY priority DESC, id", (list(_ACTIVE),))]
    done = [_item(r) for r in _q(f"SELECT {_COLS} FROM job_queue WHERE status <> ALL(%s) ORDER BY finished_at DESC NULLS LAST, id DESC LIMIT %s",
                                 (list(_ACTIVE), recent))]
    return {"running": next((x for x in act if x["status"] == "running"), None),
            "queued": [x for x in act if x["status"] == "queued"], "recent": done}


def get(item_id: int) -> dict | None:
    r = _q(f"SELECT {_COLS} FROM job_queue WHERE id=%s", (item_id,), fetch="one")
    return _item(r) if r else None


def position(item_id: int) -> int | None:
    """1 = next to run (0 = running)."""
    it = items()
    if it["running"] and it["running"]["id"] == item_id:
        return 0
    ids = [x["id"] for x in it["queued"]]
    return ids.index(item_id) + 1 if item_id in ids else None


def cancel(item_id: int) -> str:
    """A waiting item is cancelled; the running one is asked to stop (the worker stops its process)."""
    it = get(item_id)
    if not it:
        return "unknown"
    if it["status"] == "queued":
        _q("UPDATE job_queue SET status='cancelled', finished_at=now() WHERE id=%s AND status='queued'", (item_id,), fetch=None)
        return "cancelled"
    if it["status"] == "running":
        _q("UPDATE job_queue SET cancel_requested=true WHERE id=%s", (item_id,), fetch=None)
        return "stopping"
    return it["status"]


def to_front(item_id: int) -> None:
    _q("""UPDATE job_queue SET priority = (SELECT COALESCE(max(priority), 0) + 1 FROM job_queue WHERE status='queued')
          WHERE id=%s AND status='queued'""", (item_id,), fetch=None)


# ------------------------------------------------------------------ the worker's side

def claim_next() -> dict | None:
    """Take the next waiting item (FOR UPDATE SKIP LOCKED: safe even if two workers ever ran)."""
    r = _q(f"""UPDATE job_queue SET status='running', started_at=now() WHERE id = (
                 SELECT id FROM job_queue WHERE status='queued' ORDER BY priority DESC, id FOR UPDATE SKIP LOCKED LIMIT 1)
               RETURNING {_COLS}""", fetch="one")
    return _item(r) if r else None


def mark_running(item_id: int, pid: int, out_path: str) -> None:
    _q("UPDATE job_queue SET pid=%s, out_path=%s WHERE id=%s", (pid, out_path, item_id), fetch=None)


def set_run(item_id: int, run_id: int) -> None:
    _q("UPDATE job_queue SET run_id=%s WHERE id=%s", (run_id, item_id), fetch=None)


def finish(item_id: int, status: str, exit_code: int | None = None, note: str | None = None) -> None:
    _q("UPDATE job_queue SET status=%s, exit_code=%s, note=COALESCE(%s, note), finished_at=now() WHERE id=%s",
       (status, exit_code, note, item_id), fetch=None)


def stop_requested(item_id: int) -> bool:
    r = _q("SELECT cancel_requested FROM job_queue WHERE id=%s", (item_id,), fetch="one")
    return bool(r and r[0])


def heartbeat(pid: int, host: str, started_at: dt.datetime, current_item: int | None, note: str = "") -> None:
    _q("""INSERT INTO job_worker (id, pid, host, started_at, heartbeat_at, current_item, note) VALUES (1, %s, %s, %s, now(), %s, %s)
          ON CONFLICT (id) DO UPDATE SET pid=EXCLUDED.pid, host=EXCLUDED.host, started_at=EXCLUDED.started_at,
          heartbeat_at=now(), current_item=EXCLUDED.current_item, note=EXCLUDED.note""",
       (pid, host, started_at, current_item, note), fetch=None)


def worker_stopped() -> None:
    _q("UPDATE job_worker SET heartbeat_at = now() - interval '1 day', current_item = NULL, note='stopped' WHERE id=1", fetch=None)


def worker_status() -> dict:
    init_schema()
    r = _q("SELECT pid, host, started_at, heartbeat_at, current_item, note, now() FROM job_worker WHERE id=1", fetch="one")
    if not r or not r[3]:
        return {"alive": False, "seen": None}
    age = (r[6] - r[3]).total_seconds()
    return {"alive": age <= WORKER_ALIVE_S, "pid": r[0], "host": r[1], "started_at": _iso(r[2]), "seen": _iso(r[3]),
            "seen_s_ago": round(age), "current_item": r[4], "note": r[5]}


# ------------------------------------------------------------------ schedules

def _sched(r) -> dict:
    keys = [k.strip() for k in _SCOLS.split(",")]
    d = dict(zip(keys, r))
    d["last_slot"], d["created_at"] = _iso(d["last_slot"]), _iso(d["created_at"])
    d["next_slot"] = _iso(next_slot(d))
    return d


def _local_now() -> dt.datetime:
    return dt.datetime.now().astimezone()


def _slot_on(day: dt.date, at_time: str, tz) -> dt.datetime:
    h, m = (int(x) for x in at_time.split(":"))
    return dt.datetime(day.year, day.month, day.day, h, m, tzinfo=tz)


def _runs_on(s: dict, day: dt.date) -> bool:
    if s.get("monthday"):
        return day.day == int(s["monthday"])
    return WEEKDAYS[day.weekday()] in {d.strip() for d in (s.get("days") or "").split(",")}


def latest_slot(s: dict, now: dt.datetime | None = None) -> dt.datetime | None:
    """The most recent time (≤ now) the schedule was meant to run, looking back up to 40 days."""
    now = now or _local_now()
    for back in range(0, 41):
        day = (now - dt.timedelta(days=back)).date()
        if _runs_on(s, day):
            t = _slot_on(day, s["at_time"], now.tzinfo)
            if t <= now:
                return t
    return None


def next_slot(s: dict, now: dt.datetime | None = None) -> dt.datetime | None:
    if not s.get("enabled", True):
        return None
    now = now or _local_now()
    for ahead in range(0, 41):
        day = (now + dt.timedelta(days=ahead)).date()
        if _runs_on(s, day):
            t = _slot_on(day, s["at_time"], now.tzinfo)
            if t > now:
                return t
    return None


def schedules() -> list[dict]:
    init_schema()
    return [_sched(r) for r in _q(f"SELECT {_SCOLS} FROM job_schedules ORDER BY id")]


def save_schedule(s: dict) -> dict:
    """Create (no id) or update a schedule. A new or changed schedule does not fire for a slot already past."""
    _q(SCHEMA, fetch=None)
    at = s.get("at_time") or "18:30"
    h, m = (int(x) for x in at.split(":"))
    assert 0 <= h < 24 and 0 <= m < 60, "time must be HH:MM"
    days = ",".join(d for d in WEEKDAYS if d in {x.strip().lower()[:3] for x in str(s.get("days") or "").split(",")})
    monthday = int(s["monthday"]) if s.get("monthday") else None
    if not monthday and not days:
        raise ValueError("pick at least one weekday, or a day of the month")
    probe = {"days": days, "monthday": monthday, "at_time": f"{h:02d}:{m:02d}"}
    last = latest_slot(probe)
    vals = (s.get("name") or " + ".join(s["targets"]), json.dumps(s["targets"]), s.get("market") or "all",
            json.dumps({k: v for k, v in (s.get("opts") or {}).items() if v not in (None, False, "", [])}, sort_keys=True),
            days or "mon", monthday, probe["at_time"], bool(s.get("enabled", True)), last)
    if s.get("id"):
        r = _q(f"""UPDATE job_schedules SET name=%s, targets=%s, market=%s, opts=%s, days=%s, monthday=%s, at_time=%s, enabled=%s,
                   last_slot=%s WHERE id=%s RETURNING {_SCOLS}""", (*vals, s["id"]), fetch="one")
    else:
        r = _q(f"""INSERT INTO job_schedules (name, targets, market, opts, days, monthday, at_time, enabled, last_slot)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING {_SCOLS}""", vals, fetch="one")
    return _sched(r)


def set_enabled(sid: int, enabled: bool) -> None:
    # re-enabling does not fire for slots missed while it was off
    s = next((x for x in schedules() if x["id"] == sid), None)
    last = latest_slot(s) if s and enabled else None
    _q("UPDATE job_schedules SET enabled=%s, last_slot=COALESCE(%s, last_slot) WHERE id=%s", (enabled, last, sid), fetch=None)


def delete_schedule(sid: int) -> None:
    _q("DELETE FROM job_schedules WHERE id=%s", (sid,), fetch=None)


def due_schedules(now: dt.datetime | None = None) -> list[tuple[dict, dt.datetime]]:
    """Enabled schedules whose latest slot has not been enqueued yet (at most one slot each)."""
    out = []
    for s in schedules():
        if not s["enabled"]:
            continue
        slot = latest_slot(s, now)
        last = dt.datetime.fromisoformat(s["last_slot"]) if s["last_slot"] else None
        if slot and (last is None or slot > last):
            out.append((s, slot))
    return out


def mark_slot(sid: int, slot: dt.datetime) -> None:
    _q("UPDATE job_schedules SET last_slot=%s WHERE id=%s", (slot, sid), fetch=None)


def try_worker_lock(conn) -> bool:
    """Hold the single-worker lock on `conn` (released when that connection closes)."""
    with conn.cursor() as cur:
        cur.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_KEY,))
        return bool(cur.fetchone()[0])
