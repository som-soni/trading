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
from ..config import MARKETS
from ..marketdata.freshness import expected_session, lag as _lag

MARKET_NAME = {k: c.name for k, c in MARKETS.items()}
BENCH_SERIES = {"us": "SPX", "india": "NIFTY50"}
# (ok within, warn within) days for datasets that are not refreshed every trading day
AGE_LIMITS = {"universe": (8, 15), "industries": (35, 60), "names": (60, 120), "quality": (8, 32), "earnings": (8, 15),
              "rates": (4, 8),   # rates: FRED publishes a day late, so a session check would warn every day
              # judged from the job's own run log (their data is monthly, fortnightly or per company):
              "indicators": (4, 8), "news": (4, 8), "financials": (8, 15), "estimates": (8, 15), "fpi_sectors": (8, 15)}
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
            "text": f"{age:.0f} day{'' if round(age) == 1 else 's'} old (refresh every ~{ok - 1} days)" + (f" · {note}" if note else "")}


def _snapshot_item(market: str, expected) -> dict:
    """The screens' stock snapshot: which session it covers, and whether anything it copied
    from has changed since it was built.

    Two different faults, so both are reported. Being behind the session means prices moved
    on; a changed input means the present-only columns (fundamentals, peer RS, earnings) are
    out of date even though the date looks right — which is invisible from the data itself,
    because the snapshot stores whatever those sources said at build time.
    """
    from ..screens import snapshot
    ds = snapshot.dates(market)
    d = ds[-1] if ds else None
    held = f"{len(ds)} stored, back to {ds[0].isoformat()}" if ds else ""
    item = _session_item("screens_snapshot", "Stock snapshot (screens)", d, expected)
    stale = snapshot.stale_inputs(market) if d else []
    if stale:
        fields = sorted({f for x in stale for f in x["fields"]})
        note = (", ".join(x["label"] for x in stale)
                + f" changed after it was built, so {len(fields)} field(s) may be out of date — rerun the `screens` job")
        # the session can be current while the snapshot is still wrong, so do not leave the text
        # saying "up to date": the date is not what is behind here, the copied-in sources are
        item["text"] = f"covers the latest session, but {note}" if item["status"] == "ok" else f"{item['text']} · {note}"
        item["status"] = "warn" if item["status"] == "ok" else item["status"]
        item["stale_inputs"] = stale
    if held:
        item["text"] += f" · {held}"
    return item


def _job_item(q, key: str, label: str, step: str, market: str, note: str = "") -> dict:
    """Freshness of a dataset whose own dates cannot show it (monthly indicators, per-company filings):
    when its job last succeeded, flagged when the latest run of that job failed."""
    ok = q("""SELECT max(finished_at) FROM job_steps WHERE step=%s AND (market=%s OR market IS NULL OR market='all')
              AND status='ok'""", (step, market))[0][0]
    item = _age_item(key, label, ok, note)
    last = q("""SELECT status, left(coalesce(error, detail, ''), 120) FROM job_steps WHERE step=%s
                AND (market=%s OR market IS NULL OR market='all') AND status IN ('ok', 'failed', 'skipped')
                ORDER BY finished_at DESC NULLS LAST LIMIT 1""", (step, market))
    if last and last[0][0] == "failed":
        item["status"] = "warn" if item["status"] == "ok" else item["status"]
        item["text"] += f" · latest run failed: {last[0][1]}"
    item["text"] = item["text"].replace(" old (", " since the job last succeeded (", 1)
    return item


def _mtime(p) -> dt.datetime | None:
    return dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc) if p.exists() else None


def freshness(q, price_day) -> dict:
    """q: the server's query helper; price_day(market) -> (latest complete session, partial newer day or None, rows)."""
    out = {}
    for m in tuple(MARKETS):
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
        from ..marketdata import rates
        rk = [r.key for r in rates.RATES.get(m, []) if r.kind == "bond"]
        if rk:
            rd = q("SELECT max(date) FROM index_series WHERE market=%s AND series = ANY(%s)", (m, rk))[0][0]
            items.append(_age_item("rates", "Interest rates & yields", rd))
        runs = q("SELECT strategy, max(run_id) FROM universe_history WHERE market=%s GROUP BY strategy", (m,))
        last = max((r[1] for r in runs), default=None)
        last_d = dt.date.fromisoformat(last[:10]) if last else None
        latest = sorted(s for s, r in runs if r[:10] == (last or "")[:10])
        items.append(_session_item("screening", "Screening", last_d, exp,
                                   f"strategies run that day: {', '.join(latest)}" if latest else ""))
        items.append(_snapshot_item(m, exp))
        sd = q("SELECT max(date) FROM sector_daily WHERE market=%s", (m,))[0][0]
        items.append(_session_item("sectors", "Sector ranking (Sectors, themes)", sd, exp))
        pm = q("SELECT max(date) FROM postmarket_daily WHERE market=%s", (m,))[0][0]
        items.append(_session_item("postmarket", "Post-market analysis", pm, exp))
        nav = q("SELECT max(date) FROM fund_nav WHERE market=%s", (m,))[0][0]
        if nav:
            items.append(_session_item("funds", "Mutual fund NAVs", nav, exp))
        if q("SELECT 1 FROM index_series WHERE market=%s AND series='FII_NET' LIMIT 1", (m,)):
            fl = q("SELECT max(date) FROM index_series WHERE market=%s AND series='FII_NET'", (m,))[0][0]
            items.append(_session_item("flows", "FII / DII flows", fl, exp))
        if q("SELECT to_regclass('derivatives_bhav') IS NOT NULL")[0][0] and q("SELECT 1 FROM derivatives_bhav WHERE market=%s LIMIT 1", (m,)):
            fo = q("SELECT max(trade_date) FROM derivatives_bhav WHERE market=%s", (m,))[0][0]
            items.append(_session_item("fno", "F&O prices & open interest", fo, exp))
        items.append(_job_item(q, "indicators", "Economic indicators (Macro)", "indicators", m))
        items.append(_job_item(q, "news", "News & events", "news", m))
        items.append(_job_item(q, "financials", "Company financials", "financials", m))
        items.append(_job_item(q, "estimates", "Analyst estimates", "estimates", m))
        from ..marketdata import fpi_sectors
        if m == fpi_sectors.MARKET and q("SELECT to_regclass('fpi_sector_flows') IS NOT NULL")[0][0]:
            items.append(_job_item(q, "fpi_sectors", "FPI flows by sector (Macro)", "fpi_sectors", m))
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


def _step_prior_s(q, job: str, step: str, market: str | None, exclude_run_id: int, limit: int = 10) -> float | None:
    """Median duration of the last `limit` successful runs of this job's step (same step+market),
    as a rough prior for a step that has not — or has not yet — reported a progress fraction."""
    rows = q("""SELECT EXTRACT(EPOCH FROM (s.finished_at - s.started_at)) FROM job_steps s JOIN job_runs r ON r.id = s.run_id
                WHERE r.job=%s AND s.step=%s AND s.market IS NOT DISTINCT FROM %s AND s.status='ok' AND s.run_id != %s
                ORDER BY s.finished_at DESC LIMIT %s""", (job, step, market, exclude_run_id, limit))
    durations = [row[0] for row in rows if row[0] is not None]
    return float(np.median(durations)) if durations else None


def _estimate_remaining(elapsed_s: float, done: int | None, total: int | None, prior_s: float | None) -> float | None:
    """Seconds remaining for a step that has been running for `elapsed_s`. Blends the step's own
    progress fraction (once it has one) with `prior_s` — how long past runs of the same step took —
    so the estimate starts as a historical guess and tightens toward the live figure as `done/total`
    moves. Returns None when there is nothing to estimate from yet (first-ever run, no fraction)."""
    if done and total and done > 0:
        frac = min(done / total, 1.0)
        frac_remaining = max(elapsed_s / frac - elapsed_s, 0.0)
        if prior_s is None:
            return frac_remaining
        return (1 - frac) * max(prior_s - elapsed_s, 0.0) + frac * frac_remaining
    return max(prior_s - elapsed_s, 0.0) if prior_s is not None else None


def run_detail(q, rid: int) -> dict | None:
    rows = q(f"SELECT {_RUN_COLS} FROM job_runs WHERE id=%s", (rid,))
    if not rows:
        return None
    r = _run_row(rows[0])
    steps = q("""SELECT seq, step, market, label, started_at, finished_at, status, detail, error, stats,
                        progress_done, progress_total
                 FROM job_steps WHERE run_id=%s ORDER BY seq""", (rid,))
    now = dt.datetime.now(dt.timezone.utc)
    out_steps, run_eta, run_eta_known = [], 0.0, False
    for s in steps:
        status = "interrupted" if s[6] == "running" and r["status"] == "interrupted" else s[6]
        step_row = {"seq": s[0], "step": s[1], "market": s[2], "label": s[3],
                    "started_at": s[4].isoformat() if s[4] else None, "finished_at": s[5].isoformat() if s[5] else None,
                    "duration_s": (s[5] - s[4]).total_seconds() if s[4] and s[5] else None,
                    "status": status, "detail": s[7], "error": s[8], "stats": s[9]}
        if status == "running" and s[4]:
            prior = _step_prior_s(q, r["job"], s[1], s[2], rid)
            step_row["eta_s"] = eta = _estimate_remaining((now - s[4]).total_seconds(), s[10], s[11], prior)
            if eta is not None:
                run_eta += eta
                run_eta_known = True
        elif status == "pending":
            prior = _step_prior_s(q, r["job"], s[1], s[2], rid)
            if prior is not None:
                run_eta += prior
                run_eta_known = True
        out_steps.append(step_row)
    r["steps"] = out_steps
    if r["status"] == "running":
        r["eta_s"] = run_eta if run_eta_known else None
    r["log_tail"] = log_tail(r["log_path"])
    return r


def run_eta(q, rid: int) -> float | None:
    """Just the run-level ETA from run_detail() — for callers (the queue panel) that only need the
    number, not the full step/log detail, so the estimate stays computed in exactly one place."""
    r = run_detail(q, rid)
    return r.get("eta_s") if r else None


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
