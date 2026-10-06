"""Data status for the web app: how current every dataset is, and what the offline jobs did.

Two independent views, so each catches what the other misses:

  * Freshness is read from the data itself (latest price day, breadth day,
    screening run, ...), compared with the trading day the data *should* have
    reached by now. It is right even when data was updated by hand or a job
    was never logged.
  * Runs come from the run log (`swing_screener/runlog.py`): each daily run and
    standalone command, step by step, with timestamps, results and errors.

The expected trading day: a market's session counts once its close plus a data
delay has passed (US 17:30 New York, India 17:00 Kolkata), on weekdays. Exchange
holidays are not modelled, so being one trading day behind is a warning
("a holiday, or today's update has not run yet"), two or more is stale.
"""

import datetime as dt
import os
import socket
from zoneinfo import ZoneInfo

import numpy as np

from .. import paths, runlog
from ..marketdata.freshness import expected_session, lag as _lag

MARKET_NAME = {"us": "US", "india": "India"}
BENCH_SERIES = {"us": "SPX", "india": "NIFTY50"}
# (ok within, warn within) days for datasets that are not refreshed every trading day
AGE_LIMITS = {"universe": (8, 15), "industries": (35, 60), "names": (60, 120), "quality": (8, 32), "earnings": (8, 15)}
LOG_TAIL_LINES = 150


def _session_item(key: str, label: str, d, expected, note: str = "") -> dict:
    lag = _lag(d, expected)
    status = "missing" if lag is None else "ok" if lag == 0 else "warn" if lag == 1 else "stale"
    text = ("no data" if d is None else "up to date" if lag == 0
            else "1 trading day behind — a holiday, or today's update has not run yet" if lag == 1
            else f"{lag} trading days behind")
    return {"key": key, "label": label, "date": d.isoformat() if d else None, "status": status,
            "text": text + (f" · {note}" if note else ""), "kind": "session"}


def _age_item(key: str, label: str, when, note: str = "") -> dict:
    ok, warn = AGE_LIMITS[key]
    if when is None:
        return {"key": key, "label": label, "date": None, "status": "missing", "text": "never" + (f" · {note}" if note else ""), "kind": "age"}
    if isinstance(when, dt.datetime):
        when_dt = when if when.tzinfo else when.replace(tzinfo=dt.timezone.utc)
    else:
        when_dt = dt.datetime.combine(when, dt.time(), dt.timezone.utc)
    age = (dt.datetime.now(dt.timezone.utc) - when_dt).total_seconds() / 86400
    status = "ok" if age <= ok else "warn" if age <= warn else "stale"
    return {"key": key, "label": label, "date": when_dt.isoformat(), "status": status, "kind": "age",
            "text": f"{age:.0f} days old (refresh every ~{ok - 1})" + (f" · {note}" if note else "")}


def _mtime(p) -> dt.datetime | None:
    return dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc) if p.exists() else None


def freshness(q, price_day) -> dict:
    """q: the server's query helper; price_day(market) -> (latest complete session, partial newer day or None, rows)."""
    out = {}
    for m in ("us", "india"):
        exp = expected_session(m)
        items = []
        d, partial, n = price_day(m)
        note = f"{n:,} symbols on that day" + (f" · {partial[0].isoformat()} partly loaded ({partial[1]:,} symbols)" if partial else "")
        items.append(_session_item("prices", "Prices", d, exp, note))
        b = q("SELECT max(date) FROM breadth_daily WHERE market=%s", (m,))[0][0]
        items.append(_session_item("breadth", "Market breadth", min(b, d) if (b and d) else b, exp,
                                   "" if not (b and d) or b >= d else f"prices reach {d.isoformat()}"))
        ix = q("SELECT max(date) FROM index_series WHERE market=%s AND series=%s", (m, BENCH_SERIES[m]))[0][0]
        items.append(_session_item("indexes", "Index & VIX series", ix, exp))
        runs = q("SELECT strategy, max(run_id) FROM universe_history WHERE market=%s GROUP BY strategy", (m,))
        last = max((r[1] for r in runs), default=None)
        last_d = dt.date.fromisoformat(last[:10]) if last else None
        latest = sorted(s for s, r in runs if r[:10] == (last or "")[:10])
        items.append(_session_item("screening", "Screening", last_d, exp,
                                   f"strategies run that day: {', '.join(latest)}" if latest else ""))
        items.append(_age_item("universe", "Universe list", _mtime(paths.DATA_DIR / f"universe_{m}.csv")))
        items.append(_age_item("industries", "Industry classification (Sectors)",
                               q("SELECT max(updated_at) FROM symbol_industry WHERE market=%s", (m,))[0][0]))
        items.append(_age_item("names", "Company names", q("SELECT max(updated_at) FROM symbol_names WHERE market=%s", (m,))[0][0]))
        items.append(_age_item("quality", "Quality scores", q("SELECT max(computed_at) FROM quality_scores WHERE market=%s", (m,))[0][0]))
        items.append(_age_item("earnings", "Earnings dates", _mtime(paths.DATA_DIR / f"earnings_cache_{m}.csv")))
        out[m] = {"name": MARKET_NAME[m], "expected": exp.isoformat(), "items": items}
    rep = q("SELECT max(loaded_at), count(*) FROM report_runs")[0]
    out["viewer"] = {"reports_loaded_at": rep[0].isoformat() if rep[0] else None, "reports": rep[1]}
    return out


def _alive(host: str | None, pid: int | None) -> bool | None:
    if not pid or host != socket.gethostname():
        return None  # cannot tell from here
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _run_row(r) -> dict:
    rid, job, started, finished, status, args, host, pid, log_path, summary = r
    if status == "running" and _alive(host, pid) is False:
        status = "interrupted"  # the process is gone without finishing (killed, crashed, machine slept)
    return {"id": rid, "job": job, "started_at": started.isoformat(), "finished_at": finished.isoformat() if finished else None,
            "duration_s": (finished - started).total_seconds() if finished else None, "status": status, "args": args,
            "log_path": log_path, "summary": summary}


_RUN_COLS = "id, job, started_at, finished_at, status, args, host, pid, log_path, summary"


def runs(q, limit: int = 40, job: str | None = None) -> list[dict]:
    runlog.init_schema()
    rows = q(f"""SELECT {_RUN_COLS} FROM job_runs {"WHERE job=%s" if job else ""} ORDER BY started_at DESC LIMIT %s""",
             ((job, limit) if job else (limit,)))
    out = [_run_row(r) for r in rows]
    if out:
        counts = q("""SELECT run_id, count(*) FILTER (WHERE status='ok'), count(*) FILTER (WHERE status='failed'),
                             count(*) FILTER (WHERE status='skipped'), count(*) FROM job_steps WHERE run_id = ANY(%s) GROUP BY run_id""",
                   ([r["id"] for r in out],))
        by = {c[0]: c[1:] for c in counts}
        for r in out:
            ok, failed, skipped, total = by.get(r["id"], (0, 0, 0, 0))
            r["steps"] = {"ok": ok, "failed": failed, "skipped": skipped, "total": total}
    return out


def jobs_overview(q) -> dict:
    """Every job (jobs/registry.py) with its latest step per market, and the latest run of each pipeline."""
    from jobs.registry import JOBS, MARKETS, PIPELINES
    runlog.init_schema()
    last = {(j, m): (s, t, d) for j, m, s, t, d in q(
        """SELECT DISTINCT ON (split_part(step, ':', 1), market) split_part(step, ':', 1), market, status,
                  COALESCE(finished_at, started_at), detail
           FROM job_steps WHERE started_at IS NOT NULL ORDER BY split_part(step, ':', 1), market, started_at DESC""")}
    cell = lambda r: None if not r else {"status": r[0], "at": r[1].isoformat() if r[1] else None, "detail": r[2]}
    jobs = [{"name": j.name, "layer": j.layer, "summary": j.summary, "cadence": j.cadence, "network": j.network,
             "per_market": j.per_market,
             "last": {m: cell(last.get((j.name, m))) for m in MARKETS} if j.per_market else {"all": cell(last.get((j.name, None)))}}
            for j in JOBS.values()]
    pipes = []
    for name, p in PIPELINES.items():
        for m in (MARKETS if name == "daily" else (None,)):
            rows = q(f"""SELECT {_RUN_COLS} FROM job_runs WHERE job=%s {"AND args->'markets' ? %s" if m else ""}
                         ORDER BY started_at DESC LIMIT 1""", (name, m) if m else (name,))
            pipes.append({"name": name, "market": m, "summary": p["summary"],
                          "jobs": [j if isinstance(j, str) else j[0] for j in p["jobs"]],
                          "last": _run_row(rows[0]) if rows else None})
    return {"jobs": jobs, "pipelines": pipes}


def run_detail(q, rid: int) -> dict | None:
    rows = q(f"SELECT {_RUN_COLS} FROM job_runs WHERE id=%s", (rid,))
    if not rows:
        return None
    r = _run_row(rows[0])
    steps = q("""SELECT seq, step, market, label, started_at, finished_at, status, detail, error, stats
                 FROM job_steps WHERE run_id=%s ORDER BY seq""", (rid,))
    r["steps"] = [{"seq": s[0], "step": s[1], "market": s[2], "label": s[3],
                   "started_at": s[4].isoformat() if s[4] else None, "finished_at": s[5].isoformat() if s[5] else None,
                   "duration_s": (s[5] - s[4]).total_seconds() if s[4] and s[5] else None,
                   "status": "interrupted" if s[6] == "running" and r["status"] == "interrupted" else s[6],
                   "detail": s[7], "error": s[8], "stats": s[9]} for s in steps]
    r["log_tail"] = log_tail(r["log_path"])
    return r


def log_tail(path: str | None, lines: int = LOG_TAIL_LINES) -> list[str] | None:
    """The end of a run's log file — only files inside the repository's logs/ directory."""
    if not path:
        return None
    try:
        p = os.path.realpath(path)
        if not p.startswith(os.path.realpath(paths.LOGS_DIR) + os.sep) or not os.path.exists(p):
            return None
        with open(p, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 200_000))
            text = f.read().decode("utf-8", "replace")
        return text.splitlines()[-lines:]
    except OSError:
        return None
