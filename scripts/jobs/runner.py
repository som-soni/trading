"""Run jobs and pipelines: expand them into steps, record every step in the run log, keep going on failure.

`run(["daily"], markets=["india"], opts)` plans every step up front (the web app's Status page shows the
steps still to come), runs them in order, and:

  * records each step's result (`swing_screener/runlog.py`);
  * skips a step whose inputs failed in this run (a job's `after`), so nothing is built on a failed input;
  * honours `--from JOB` to resume a pipeline part-way;
  * writes a log file per run under logs/jobs/, whose tail the Status page shows.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field

from swing_screener import paths, runlog

from .registry import JOBS, MARKETS, PIPELINES, Ctx

logger = logging.getLogger("jobs")
MARKET_NAME = {"us": "US", "india": "India", None: ""}


@dataclass
class Entry:
    job: str
    market: str | None
    step: str
    label: str
    fn: object
    opts: dict = field(default_factory=dict)


def _job_list(targets: list[str]) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    for t in targets:
        if t in PIPELINES:
            out += [j if isinstance(j, tuple) else (j, {}) for j in PIPELINES[t]["jobs"]]
        elif t in JOBS:
            out.append((t, {}))
        else:
            raise SystemExit(f"unknown job or pipeline '{t}'. Jobs: {', '.join(JOBS)}. Pipelines: {', '.join(PIPELINES)}")
    return out


def plan(targets: list[str], markets: list[str], opts: dict) -> list[Entry]:
    """Per-market jobs run market by market (all of US, then all of India); market-wide jobs run once, at the end."""
    jobs = _job_list(targets)
    entries: list[Entry] = []
    for m in markets:
        for name, jopts in jobs:
            job = JOBS[name]
            if not job.per_market or m not in job.markets:
                continue
            ctx = Ctx(m, {**opts, **jopts})
            steps = job.expand(ctx) if job.expand else [(name, job.summary_short, job.run)]
            for step, label, fn in steps:
                entries.append(Entry(name, m, step, f"{MARKET_NAME[m]} {label}", fn, jopts))
    for name, jopts in jobs:
        job = JOBS[name]
        if not job.per_market and not any(e.job == name for e in entries) and job.run:
            label = job.summary_short
            entries.append(Entry(name, None, name, label[:1].upper() + label[1:], job.run, jopts))
    return entries


def _log_file(name: str):
    d = paths.LOGS_DIR / "jobs"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{dt.datetime.now():%Y-%m-%d_%H%M%S}_{name}.log"
    h = logging.FileHandler(p)
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(h)
    return p, h


def run(targets: list[str], markets: list[str] | None = None, opts: dict | None = None, from_job: str | None = None) -> int:
    """Run jobs / pipelines. Returns 0 when every step succeeded or was deliberately skipped, else 1."""
    opts = opts or {}
    for t in targets:   # a pipeline's defaults fill options the request left unset
        for k, v in (PIPELINES.get(t, {}).get("defaults") or {}).items():
            if opts.get(k) in (None, False, [], ""):
                opts[k] = v
    markets = markets or list(MARKETS)
    entries = plan(targets, markets, opts)
    if from_job:
        order = [n for n, _ in _job_list(targets)]
        if from_job not in order:
            raise SystemExit(f"--from {from_job}: not part of {' + '.join(targets)} ({', '.join(order)})")
        start = order.index(from_job)
        resumed = [e for e in entries if order.index(e.job) < start]
        entries = [e for e in entries if order.index(e.job) >= start]
        logger.info("resuming from %s: skipping %d earlier step(s)", from_job, len(resumed))
    name = "+".join(targets)
    log_path, handler = _log_file(name.replace("+", "_"))
    logger.info("=== %s · markets %s · %s ===", name, ",".join(markets), {k: v for k, v in opts.items() if v})
    failed: set[tuple[str, str | None]] = set()
    try:
        with runlog.run(name, args={"targets": targets, "markets": markets, **{k: v for k, v in opts.items() if v},
                                    **({"from": from_job} if from_job else {})},
                        plan=[(e.step, e.market, e.label) for e in entries], log_path=log_path) as r:
            for e in entries:
                job = JOBS[e.job]
                blocked = [d for d in job.after if (d, e.market) in failed or (d, None) in failed]
                print(f"\n── {e.label} " + "─" * max(4, 60 - len(e.label)))
                with r.step(e.step, e.market, e.label) as s:
                    if blocked:
                        s.skip(f"skipped: {', '.join(blocked)} failed in this run")
                    else:
                        e.fn(Ctx(e.market, {**opts, **e.opts}, s))
                if not s.ok:
                    failed.add((e.job, e.market))
                status = s.status or ("ok" if s.ok else "FAILED")
                print(f"   {status}: {s.detail or ''}")
    finally:
        logging.getLogger().removeHandler(handler)
        handler.close()
    print(f"\n{name}: {'all steps done' if not failed else 'failed: ' + ', '.join(f'{j}/{m}' if m else j for j, m in sorted(failed, key=str))}"
          f"\nLog: {log_path}")
    return 1 if failed else 0
