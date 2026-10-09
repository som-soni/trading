"""The worker: runs the job queue (jobs/queue.py), one item at a time, and enqueues schedules when due.

    python -m jobs worker                 run in the foreground (Ctrl-C to stop)
    python -m jobs worker --launchd       print a macOS launchd agent that keeps it running (see --install)

Each item runs as `python -m jobs run ...` in its own process group — exactly what the terminal would run
— so the run log records it like any other run and Stop can end it cleanly (SIGTERM, which the run log
records as "stopped"; SIGKILL if it has not exited 30 s later). The item's final status comes from the
run log when the run got that far (ok / partial → failed / interrupted → stopped), else from the exit code.

Only one worker runs at a time (a Postgres advisory lock). If the worker restarts while an item's process
is still alive, it keeps following that process instead of starting another. Every few seconds it writes a
heartbeat, which the portal shows as "worker running" / "worker stopped".
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import signal
import socket
import subprocess
import sys
import time

import psycopg2

from swing_screener import paths

from . import queue

logger = logging.getLogger("jobs.worker")
POLL_S = 2            # how often it looks for work while idle
SCHEDULE_EVERY_S = 30 # how often it checks the schedules
KILL_AFTER_S = 30     # after Stop: SIGKILL if the job has not exited by then

_stop = False


def _alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _run_id_for(pid: int, since: str | None) -> int | None:
    """The job_runs row the item's process created (runlog records the pid)."""
    r = queue._q("SELECT id FROM job_runs WHERE pid=%s AND started_at >= %s::timestamptz - interval '5 seconds' ORDER BY id DESC LIMIT 1",
                 (pid, since or "epoch"), fetch="one")
    return r[0] if r else None


def _outside_run() -> dict | None:
    """A run still going that the queue did not start (`python -m jobs run` from a terminal): the worker
    waits for it rather than run two jobs at once."""
    for rid, pid in queue._q("""SELECT r.id, r.pid FROM job_runs r WHERE r.status='running' AND r.host=%s
                                 AND NOT EXISTS (SELECT 1 FROM job_queue q WHERE q.run_id = r.id AND q.status='running')""",
                             (socket.gethostname(),)):
        if _alive(pid):
            return {"run_id": rid, "pid": pid}
    return None


def _final_status(item: dict, exit_code: int | None) -> str:
    stopped = queue.stop_requested(item["id"])
    run_id = item.get("run_id") or (item.get("pid") and _run_id_for(item["pid"], item.get("started_at")))
    if run_id:
        r = queue._q("SELECT status FROM job_runs WHERE id=%s", (run_id,), fetch="one")
        st = r[0] if r else None
        if st == "ok":
            return "ok"
        if st == "interrupted" or stopped:
            return "stopped"
        if st in ("partial", "failed"):
            return "failed"
    if stopped:
        return "stopped"
    return "ok" if exit_code == 0 else "failed"


def _start(item: dict) -> subprocess.Popen:
    cmd = [sys.executable, "-m", "jobs", *queue.command_for(item["targets"], item["market"], item["opts"])]
    out = paths.LOGS_DIR / "jobs" / f"{dt.datetime.now():%Y-%m-%d_%H%M%S}_queue_{item['id']}.out"
    out.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONPATH": str(paths.SCRIPTS_DIR)}
    with open(out, "w") as f:
        proc = subprocess.Popen(cmd, cwd=str(paths.SCRIPTS_DIR), env=env, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
    queue.mark_running(item["id"], proc.pid, str(out))
    logger.info("item #%d started (pid %d): %s", item["id"], proc.pid, " ".join(cmd[2:]))
    return proc


def _follow(item: dict, proc: subprocess.Popen | None, tick) -> None:
    """Wait for the item's process to finish (handling Stop), then record its outcome. `tick` keeps the
    heartbeat and the schedules going meanwhile. If the worker itself is stopping, it leaves the job
    running (its own process group) for the next worker to follow."""
    pid = proc.pid if proc else item["pid"]
    stop_sent = None
    while True:
        if _stop:
            logger.info("worker stopping: item #%d keeps running (pid %s)", item["id"], pid)
            return
        tick(item["id"])
        if not item.get("run_id"):
            rid = _run_id_for(pid, item.get("started_at"))
            if rid:
                item["run_id"] = rid
                queue.set_run(item["id"], rid)
        done = proc.poll() is not None if proc else not _alive(pid)
        if done:
            break
        if queue.stop_requested(item["id"]):
            if stop_sent is None:
                logger.info("item #%d: stop requested", item["id"])
                try:
                    os.killpg(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                stop_sent = time.time()
            elif time.time() - stop_sent > KILL_AFTER_S:
                try:
                    os.killpg(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        time.sleep(POLL_S)
    code = proc.returncode if proc else None
    status = _final_status(item, code)
    queue.finish(item["id"], status, code)
    logger.info("item #%d finished: %s (exit %s)", item["id"], status, code)


def _enqueue_due() -> None:
    for s, slot in queue.due_schedules():
        it = queue.enqueue(s["targets"], s["market"], s["opts"], requested_by="schedule", schedule_id=s["id"], skip_if_running=True)
        queue.mark_slot(s["id"], slot)
        logger.info("schedule '%s' (%s): %s", s["name"], slot.strftime("%a %d %b %H:%M"),
                    "already queued" if it.get("duplicate") else f"queued as item #{it['id']}")


def run_forever() -> int:
    global _stop
    queue.init_schema()
    lock_conn = psycopg2.connect()
    lock_conn.autocommit = True
    if not queue.try_worker_lock(lock_conn):
        print("Another worker is already running (only one runs at a time).")
        return 1
    started = dt.datetime.now().astimezone()
    host, me = socket.gethostname(), os.getpid()
    last_sched = [0.0]

    def tick(cur=None):
        """heartbeat, and enqueue any schedule that has come due (also while a job is running)"""
        queue.heartbeat(me, host, started, cur)
        if time.time() - last_sched[0] >= SCHEDULE_EVERY_S:
            try:
                _enqueue_due()
            except Exception as exc:  # noqa: BLE001 - a bad schedule must not stop the worker
                logger.warning("schedules: %s", exc)
            last_sched[0] = time.time()

    def on_signal(*_):
        global _stop
        _stop = True
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    logger.info("worker %d started on %s", me, host)

    # an item left "running" by a previous worker: keep following its process if it is still alive
    q = queue.items()
    if q["running"]:
        it = q["running"]
        if _alive(it["pid"]):
            logger.info("following item #%d left running by the previous worker (pid %s)", it["id"], it["pid"])
            _follow(it, None, tick)
        else:
            queue.finish(it["id"], _final_status(it, None) if it.get("run_id") else "interrupted", None, "the worker stopped while it ran")

    try:
        while not _stop:
            tick()
            outside = _outside_run()
            if outside:
                queue.heartbeat(me, host, started, None, f"waiting for run #{outside['run_id']} started outside the queue")
                time.sleep(POLL_S * 5)
                continue
            item = queue.claim_next()
            if not item:
                time.sleep(POLL_S)
                continue
            try:
                proc = _start(item)
                item["pid"] = proc.pid
                _follow(item, proc, tick)
            except Exception as exc:  # noqa: BLE001
                logger.exception("item #%d could not run", item["id"])
                queue.finish(item["id"], "failed", None, f"{type(exc).__name__}: {exc}")
    finally:
        # a job still running keeps running (its own process group); the next worker picks it up
        queue.worker_stopped()
        logger.info("worker %d stopped", me)
    return 0


LAUNCHD_LABEL = "com.trading.jobs-worker"


def launchd_plist() -> str:
    log = paths.LOGS_DIR / "worker.log"
    env = "".join(f"<key>{k}</key><string>{v}</string>" for k, v in os.environ.items() if k.startswith("PG"))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{LAUNCHD_LABEL}</string>
  <key>ProgramArguments</key><array><string>{sys.executable}</string><string>-m</string><string>jobs</string><string>worker</string></array>
  <key>WorkingDirectory</key><string>{paths.SCRIPTS_DIR}</string>
  <key>EnvironmentVariables</key><dict><key>PYTHONPATH</key><string>{paths.SCRIPTS_DIR}</string>{env}</dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>30</integer>
  <key>StandardOutPath</key><string>{log}</string>
  <key>StandardErrorPath</key><string>{log}</string>
</dict>
</plist>
"""


def launchd_path():
    from pathlib import Path
    return Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"
