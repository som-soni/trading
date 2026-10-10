"""Offline jobs: pull data, compute analytics, screen, publish — separately or as pipelines.

    python -m jobs list                                    every job and pipeline, with its last run per market
    python -m jobs run prices --market india               just pull data
    python -m jobs run breadth sectors --market us         just analytics (stored data only)
    python -m jobs run screens strategies --market us --strategies all
    python -m jobs run daily --market india                a pipeline (see `list`)
    python -m jobs run daily --market us --from strategies resume a pipeline part-way
    python -m jobs run weekly                              both markets when --market is omitted
    python -m jobs run postmarket --days 60                post-market analysis, backfilling 60 sessions
    python -m jobs status                                  how current every dataset is (the web app's Data status page)

The queue (jobs/queue.py) — what the portal and the schedules use; one worker runs it:
    python -m jobs worker                                  run the queue (keep it running; see --launchd)
    python -m jobs enqueue strategies --market india       add a run to the queue (same arguments as `run`)
    python -m jobs queue                                   what is running, waiting and recently finished
    python -m jobs cancel 42                               cancel a waiting item / stop the running one
    python -m jobs schedules                               the schedules (edit them in the portal: System → Schedules)

Options for `run`: --force (refresh even when current), --allow-stale (screen on old prices),
--strategies a,b|all (default: the default strategy), --universe-days N, --quality-top N.
Run from scripts/ with PYTHONPATH=.
"""

import argparse
import datetime as dt
import logging
import sys

from .registry import JOBS, MARKETS, PIPELINES


def _last_runs() -> dict:
    """(job, market) -> (status, finished_at, detail) of the most recent step for that job."""
    from swing_screener import runlog
    from swing_screener.marketdata import db
    runlog.init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT DISTINCT ON (split_part(step, ':', 1), market) split_part(step, ':', 1), market, status,
                              COALESCE(finished_at, started_at), detail
                       FROM job_steps WHERE started_at IS NOT NULL
                       ORDER BY split_part(step, ':', 1), market, started_at DESC""")
        return {(j, m): (s, t, d) for j, m, s, t, d in cur.fetchall()}


def cmd_list() -> None:
    last = _last_runs()
    fmt = lambda r: "—" if not r else f"{r[0]:8s} {r[1]:%d %b %H:%M}"
    print(f"{'JOB':16s}{'LAYER':11s}{'NET':5s}{'CADENCE':9s}{'US LAST RUN':24s}{'INDIA LAST RUN':24s}WHAT")
    for j in JOBS.values():
        cols = [fmt(last.get((j.name, m))) for m in MARKETS] if j.per_market else [fmt(last.get((j.name, None))), ""]
        print(f"{j.name:16s}{j.layer:11s}{'yes' if j.network else 'no':5s}{j.cadence:9s}{cols[0]:24s}{cols[1]:24s}{j.summary}")
    print("\nPIPELINES")
    for name, p in PIPELINES.items():
        jobs = " → ".join(j if isinstance(j, str) else f"{j[0]}(force)" for j in p["jobs"])
        print(f"  {name:9s}{p['summary']}\n  {'':9s}{jobs}")


def cmd_status() -> None:
    from swing_screener.marketdata import freshness
    from swing_screener.web import status as st

    def q(sql, params=()):
        from swing_screener.marketdata import db
        with db.get_connection().cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def price_day(m):
        s = freshness.price_status(m)
        return s["latest"], s["partial"], s["rows"]

    f = st.freshness(q, price_day)
    mark = {"ok": "✓", "warn": "!", "stale": "✗", "missing": "?"}
    for m in MARKETS:
        print(f"\n{f[m]['name']} — expected trading day {f[m]['expected']}")
        for i in f[m]["items"]:
            d = (i["date"] or "—")[:10]
            print(f"  {mark[i['status']]} {i['label']:36s} {d:11s} {i['text']}")
    runs = st.runs(q, 8)
    if runs:
        print("\nRecent runs")
        for r in runs:
            took = f"{r['duration_s']:.0f}s" if r["duration_s"] is not None else ""
            print(f"  #{r['id']:<5d} {r['started_at'][:16].replace('T', ' ')}  {r['job']:14s} {r['status']:12s} {took:>7s}  {r['summary'] or ''}")


def cmd_schedules() -> None:
    from . import queue
    w = queue.worker_status()
    print(f"Worker: {'running (pid %s)' % w['pid'] if w['alive'] else 'NOT running — start it: python -m jobs worker (or --launchd to keep it running)'}\n")
    print(f"{'ID':4s}{'ON':4s}{'WHEN':28s}{'NEXT':20s}WHAT")
    for x in queue.schedules():
        when = f"day {x['monthday']} monthly" if x["monthday"] else x["days"]
        nxt = x["next_slot"][:16].replace("T", " ") if x["next_slot"] else "—"
        print(f"{x['id']:<4d}{'yes' if x['enabled'] else 'no':4s}{when + ' ' + x['at_time']:28s}{nxt:20s}{x['name']}  "
              f"(python -m jobs {' '.join(queue.command_for(x['targets'], x['market'], x['opts']))})")


def cmd_queue() -> None:
    from . import queue
    q = queue.items(10)
    w = queue.worker_status()
    print(f"Worker: {'running' if w['alive'] else 'NOT running'}")
    row = lambda x: f"  #{x['id']:<5d} {x['status']:10s} {(x['created_at'] or '')[:16].replace('T', ' ')}  {x['requested_by']:12s} {x['command']}"
    print("Running:"), print(row(q["running"]) if q["running"] else "  —")
    print("Waiting:"), [print(row(x)) for x in q["queued"]] or print("  —")
    print("Recent:"), [print(row(x)) for x in q["recent"]]


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m jobs", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="jobs, pipelines and their last runs")
    sub.add_parser("status", help="how current every dataset is")
    sub.add_parser("schedules", help="the schedules and the next time each runs")
    sub.add_parser("schedule", help="(old name of `schedules`)")
    sub.add_parser("queue", help="what is running, waiting and recently finished")
    c = sub.add_parser("cancel", help="cancel a waiting queue item, or stop the running one")
    c.add_argument("item", type=int)
    w = sub.add_parser("worker", help="run the job queue")
    w.add_argument("--launchd", action="store_true", help="print a macOS launchd agent that keeps the worker running")
    w.add_argument("--install", action="store_true", help="write that agent to ~/Library/LaunchAgents and load it")
    w.add_argument("--uninstall", action="store_true", help="unload and remove the agent")
    for name, helptext in (("run", "run jobs and/or pipelines now, in this terminal"), ("enqueue", "add jobs and/or pipelines to the queue")):
        _run_args(sub.add_parser(name, help=helptext))
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if a.cmd == "list":
        return cmd_list()
    if a.cmd == "status":
        return cmd_status()
    if a.cmd in ("schedule", "schedules"):
        return cmd_schedules()
    if a.cmd == "queue":
        return cmd_queue()
    if a.cmd == "cancel":
        from . import queue
        print(f"#{a.item}: {queue.cancel(a.item)}")
        return
    if a.cmd == "worker":
        return cmd_worker(a)
    opts, targets, markets = _opts(ap, a)
    if a.cmd == "enqueue":
        from . import queue
        it = queue.enqueue(targets, a.market, {**opts, "from": a.from_job, "no_ingest": a.no_ingest}, requested_by="command line")
        pos = queue.position(it["id"])
        w = queue.worker_status()
        print(f"#{it['id']} {'already queued' if it.get('duplicate') else 'queued'} — position {pos}: {it['command']}"
              + ("" if w["alive"] else "\nThe worker is not running: start it with  python -m jobs worker"))
        return

    import signal
    # Stop (from the web app) sends SIGTERM: turn it into SystemExit so the run log records the run as stopped
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(SystemExit(143)))
    from .runner import run
    if a.no_ingest:
        import jobs.registry as reg
        for p in reg.PIPELINES.values():
            p["jobs"] = [j for j in p["jobs"] if j != "ingest"]
        targets = [t for t in targets if t != "ingest"]
    sys.exit(run(targets, markets, opts, a.from_job))


def cmd_worker(a) -> None:
    import subprocess
    from . import worker
    if a.launchd:
        print(worker.launchd_plist())
        print(f"<!-- install with: python -m jobs worker --install   (writes {worker.launchd_path()}) -->")
        return
    if a.install:
        p = worker.launchd_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(worker.launchd_plist())
        subprocess.run(["launchctl", "unload", str(p)], capture_output=True)
        subprocess.run(["launchctl", "load", "-w", str(p)], check=True)
        print(f"Installed and started: {p}\nThe worker now starts at login and restarts if it stops. Logs: logs/worker.log")
        return
    if a.uninstall:
        p = worker.launchd_path()
        subprocess.run(["launchctl", "unload", "-w", str(p)], capture_output=True)
        p.unlink(missing_ok=True)
        print(f"Removed {p}")
        return
    sys.exit(worker.run_forever())


def _run_args(r) -> None:
    r.add_argument("targets", nargs="+", help="job or pipeline names")
    r.add_argument("--market", default="all", choices=["all", *MARKETS])
    r.add_argument("--strategies", default=None, help="comma-separated strategies for `strategies`, or 'all'")
    r.add_argument("--from", dest="from_job", default=None, help="resume a pipeline from this job")
    r.add_argument("--force", action="store_true", help="refresh even when the data looks current")
    r.add_argument("--allow-stale", action="store_true", help="let `strategies` run on prices 2+ trading days old")
    r.add_argument("--universe-days", type=float, default=None, help="max universe-list age before `universe` re-fetches it")
    r.add_argument("--quality-top", type=int, default=None, help="how many of the most liquid companies `quality` scores")
    r.add_argument("--no-ingest", action="store_true", help="leave out the `ingest` job")
    r.add_argument("--days", type=int, default=None, help="`postmarket`: also analyse this many latest sessions (backfill)")
    r.add_argument("--start", default=None, help="`backtest`: simulate from this date (YYYY-MM-DD, default 2013-01-01)")
    r.add_argument("--sample", type=int, default=None, help="`backtest`: a seeded random subset of N candidates (faster, unbiased)")
    r.add_argument("--accept-labels", default=None, metavar="LABELS",
                   help="`backtest`: which decision labels count as tradeable, comma separated "
                        "(e.g. 'TRADE - HIGH CONFIDENCE,TRADE ON TRIGGER'). Overrides the strategy's "
                        "own backtest_args; the run gets its own report directory.")
    r.add_argument("--max-base", type=int, default=None, metavar="N",
                   help="`backtest`: trade only the first N bases of a stock's advance.")
    r.add_argument("--symbols", default=None, metavar="A,B,C",
                   help="`backtest`: restrict the run to these symbols, e.g. --symbols NVDA,MU,GOOG. "
                        "The report names them, and the run gets its own directory.")
    r.add_argument("--bt", action="append", default=None, metavar="'--flag VALUE'",
                   help="`backtest`: extra arguments passed straight through to the backtest, quoted, "
                        "e.g. --bt '--fail-days 0'. Repeatable. For the exit-policy and simulator flags "
                        "that have no dedicated option here; they are appended last, so they win.")
    r.add_argument("--const", action="append", default=None, metavar="NAME=VALUE",
                   help="`backtest`: override a numeric module constant, e.g. --const MIN_STRUCTURAL_R=0. "
                        "Repeatable. The variant gets its own fingerprint, cache and run directory.")
    r.add_argument("--vcp", action="append", default=None, metavar="KEY=VALUE",
                   help="`backtest`: override a VcpParams field, e.g. --vcp base_min_days=5. "
                        "Repeatable. The variant gets its own fingerprint, cache and run directory.")


def _opts(ap, a):
    """the run options, targets and markets of a `run` / `enqueue` command"""
    from swing_screener.strategies import list_strategies
    strategies = None
    if a.strategies:
        strategies = ["all"] if a.strategies.strip() == "all" else [s.strip() for s in a.strategies.split(",") if s.strip()]
        bad = [s for s in strategies if s != "all" and s not in list_strategies()]
        if bad:
            ap.error(f"unknown strategies {bad}; choose from {list_strategies()}")
    opts = {"strategies": strategies, "force": a.force, "allow_stale": a.allow_stale,
            "universe_days": a.universe_days, "quality_top": a.quality_top, "days": a.days,
            "start": a.start, "sample": a.sample, "vcp": a.vcp, "const": a.const, "bt": a.bt, "symbols": a.symbols, "max_base": a.max_base,
            "accept_labels": a.accept_labels}
    unknown = [t for t in a.targets if t not in JOBS and t not in PIPELINES]
    if unknown:
        ap.error(f"unknown job or pipeline {unknown}. Jobs: {', '.join(JOBS)}. Pipelines: {', '.join(PIPELINES)}")
    markets = list(MARKETS) if a.market == "all" else [a.market]
    return opts, a.targets, markets


if __name__ == "__main__":
    main()
