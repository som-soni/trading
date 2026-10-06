"""Offline jobs: pull data, compute analytics, screen, publish — separately or as pipelines.

    python -m jobs list                                    every job and pipeline, with its last run per market
    python -m jobs run prices --market india               just pull data
    python -m jobs run breadth sectors --market us         just analytics (stored data only)
    python -m jobs run screen --market us --strategies all
    python -m jobs run daily --market india                a pipeline (see `list`)
    python -m jobs run daily --market us --from screen     resume a pipeline part-way
    python -m jobs run weekly                              both markets when --market is omitted
    python -m jobs status                                  how current every dataset is (the web app's Data status page)
    python -m jobs schedule                                suggested crontab lines

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
    print(f"{'JOB':13s}{'LAYER':11s}{'NET':5s}{'CADENCE':9s}{'US LAST RUN':24s}{'INDIA LAST RUN':24s}WHAT")
    for j in JOBS.values():
        cols = [fmt(last.get((j.name, m))) for m in MARKETS] if j.per_market else [fmt(last.get((j.name, None))), ""]
        print(f"{j.name:13s}{j.layer:11s}{'yes' if j.network else 'no':5s}{j.cadence:9s}{cols[0]:24s}{cols[1]:24s}{j.summary}")
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


def cmd_schedule() -> None:
    from swing_screener import paths
    base = f"cd {paths.SCRIPTS_DIR} && PYTHONPATH=. {sys.executable} -m jobs run"
    log = f">> {paths.LOGS_DIR}/cron.log 2>&1"
    tz = dt.datetime.now().astimezone().tzname()
    print(f"# Times are this machine's local time ({tz}); they assume India Standard Time — adjust if not.")
    print(f"# India: NSE closes 15:30 IST, data settles by ~17:30.   US: NYSE closes 01:30/02:30 IST.")
    print(f"30 18 * * 1-5  {base} daily --market india --strategies all {log}")
    print(f"0 7 * * 2-6    {base} daily --market us --strategies all {log}")
    print(f"0 10 * * 6     {base} weekly {log}")
    print(f"0 9 1 * *      {base} monthly {log}")
    print("\n# Install with:  crontab -e   (paste the lines above)")


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m jobs", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="jobs, pipelines and their last runs")
    sub.add_parser("status", help="how current every dataset is")
    sub.add_parser("schedule", help="suggested crontab lines")
    r = sub.add_parser("run", help="run jobs and/or pipelines")
    r.add_argument("targets", nargs="+", help="job or pipeline names")
    r.add_argument("--market", default="all", choices=["all", *MARKETS])
    r.add_argument("--strategies", default=None, help="comma-separated strategies for `screen`, or 'all'")
    r.add_argument("--from", dest="from_job", default=None, help="resume a pipeline from this job")
    r.add_argument("--force", action="store_true", help="refresh even when the data looks current")
    r.add_argument("--allow-stale", action="store_true", help="let `screen` run on prices 2+ trading days old")
    r.add_argument("--universe-days", type=float, default=None, help="max universe-list age before `universe` re-fetches it")
    r.add_argument("--quality-top", type=int, default=None, help="how many of the most liquid companies `quality` scores")
    r.add_argument("--no-ingest", action="store_true", help="leave out the `ingest` job")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if a.cmd == "list":
        return cmd_list()
    if a.cmd == "status":
        return cmd_status()
    if a.cmd == "schedule":
        return cmd_schedule()

    from .runner import run
    from swing_screener.strategies import list_strategies
    strategies = None
    if a.strategies:
        strategies = ["all"] if a.strategies.strip() == "all" else [s.strip() for s in a.strategies.split(",") if s.strip()]
        bad = [s for s in strategies if s != "all" and s not in list_strategies()]
        if bad:
            ap.error(f"unknown strategies {bad}; choose from {list_strategies()}")
    opts = {"strategies": strategies, "force": a.force, "allow_stale": a.allow_stale,
            "universe_days": a.universe_days, "quality_top": a.quality_top}
    targets = a.targets
    if a.no_ingest:
        import jobs.registry as reg
        for p in reg.PIPELINES.values():
            p["jobs"] = [j for j in p["jobs"] if j != "ingest"]
        targets = [t for t in targets if t != "ingest"]
    markets = list(MARKETS) if a.market == "all" else [a.market]
    sys.exit(run(targets, markets, opts, a.from_job))


if __name__ == "__main__":
    main()
