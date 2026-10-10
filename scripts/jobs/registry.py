"""Every offline job, in layers, and the pipelines that chain them.

Layers (each reads only what the layers above it produced):

  reference   which symbols exist and what they are          universe, names, classify, industries
  data        raw time series and company data (network)     prices, indexes, earnings, fundamentals
  analytics   market-wide measures from stored prices        breadth, sectors
  screening   stock selection from stored data               screens, strategies (one step per strategy), backtest, quality
  publish     what the web app shows                         report, ingest

Two rules keep the layers honest:
  * data jobs never screen, and analytics / screening never download prices
    (`strategies` runs inside `cache.offline()` and refuses to run on prices two or
    more trading days behind unless told to);
  * every job is idempotent — re-running costs little and changes nothing that
    is already current.

A job is per market unless `per_market=False`. Job functions receive a `Ctx`
and describe what they did through `ctx.step` (detail / stats / skip).
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger("jobs")

MARKETS = ("us", "india")
UNIVERSE_MAX_AGE_DAYS = 7      # `universe` re-fetches the list when older than this (or with --force)
INDUSTRY_MAX_AGE_DAYS = 30     # `industries` re-classifies when older than this (or with --force)
QUALITY_TOP = {"us": 500, "india": 300}   # `quality` scores the N most liquid companies (+ your tracked list)
QUALITY_MAX_AGE_DAYS = 30      # statements newer than this are not re-fetched
STALE_TRADING_DAYS = 2         # `strategies` refuses prices this many trading days behind (holidays make 1 ambiguous)


class StaleData(RuntimeError):
    pass


@dataclass
class Ctx:
    market: str | None
    opts: dict
    step: object = None            # runlog.Step: set .detail / .stats, or .skip(why)

    def opt(self, key, default=None):
        v = self.opts.get(key)
        return default if v is None else v


@dataclass
class Job:
    name: str
    layer: str
    summary: str
    cadence: str
    network: bool
    run: Callable[[Ctx], None] | None = None
    per_market: bool = True
    after: tuple = ()              # jobs it reads from: in a pipeline, it is skipped when one of them failed
    expand: Callable[[Ctx], list] | None = None   # -> [(step_name, label, fn)] for jobs with several steps
    markets: tuple = MARKETS

    @property
    def summary_short(self) -> str:
        return self.summary.split(":")[0]


# ------------------------------------------------------------------ reference

def _universe(ctx: Ctx) -> None:
    from swing_screener.marketdata import universe
    fetch = {"us": universe.fetch_us_universe_from_nasdaqtrader,
             "india": universe.fetch_india_universe_from_yfinance_screener}[ctx.market]
    max_age = ctx.opt("universe_days", UNIVERSE_MAX_AGE_DAYS)
    age = universe.universe_age_days(ctx.market)
    if not ctx.opt("force") and age is not None and (max_age < 0 or age <= max_age):
        ctx.step.skip(f"up to date: {len(universe.load_universe(ctx.market)):,} tickers, {age:.1f} days old")
        return
    fetch()  # also refreshes company names
    ctx.step.detail = f"refreshed: {len(universe.load_universe(ctx.market)):,} tickers" + (f" (was {age:.0f} days old)" if age else "")


def _names(ctx: Ctx) -> None:
    from swing_screener.marketdata import names
    ctx.step.detail = f"{names.refresh(ctx.market):,} company names stored"


def _classify(ctx: Ctx) -> None:
    if ctx.market == "us":
        # closed-end funds and income trusts are not flagged as ETFs in the Nasdaq listing: identify them by
        # name, industry and size (no network) and keep them out of breadth, sectors and movers
        from swing_screener.analytics import breadth
        from swing_screener.marketdata import db, subindustries
        breadth.init_schema()
        funds = subindustries.us_funds()
        with db.get_connection().cursor() as cur:
            cur.execute("DELETE FROM symbol_kind WHERE market='us' AND kind='FUND' AND NOT (symbol = ANY(%s))", (list(funds),))
        db.execute_values("""INSERT INTO symbol_kind (market, symbol, kind, sector) VALUES %s
                             ON CONFLICT (market, symbol) DO UPDATE SET kind=EXCLUDED.kind, checked_at=now()""",
                          [("us", s, "FUND", "Closed-end fund") for s in sorted(funds)])
        ctx.step.detail = f"{len(funds):,} closed-end funds / income trusts flagged (left out of breadth, sectors, movers)"
        return
    from swing_screener.analytics import breadth
    breadth.init_schema()
    r = breadth.classify(ctx.market)
    ctx.step.detail = ", ".join(f"{k} {v:,}" for k, v in r.items())
    ctx.step.stats = r


def _industries(ctx: Ctx) -> None:
    from swing_screener.marketdata import db, industries
    industries.init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT EXTRACT(EPOCH FROM now() - max(updated_at)) / 86400 FROM symbol_industry WHERE market=%s", (ctx.market,))
        age = cur.fetchone()[0]
    if not ctx.opt("force") and age is not None and age <= INDUSTRY_MAX_AGE_DAYS:
        ctx.step.skip(f"up to date ({age:.0f} days old; re-classified every {INDUSTRY_MAX_AGE_DAYS})")
        return
    ctx.step.detail = f"{industries.refresh(ctx.market):,} stocks classified"


def _group_research(ctx: Ctx) -> None:
    """Research: does group strength improve forward returns? (screens/group_research.py) — writes
    research/group-strength-study.md; the ingest job loads it into the Reports archive."""
    from swing_screener.config import MARKETS as MCFG
    from swing_screener.screens import group_research as gr
    results = {m: gr.run(m) for m in MCFG}
    gr.REPORT.write_text(gr.report(results))
    head = []
    for m, r in results.items():
        p = next(x for x in r["pairs"] if x["title"] == "Group strength alone").get("1M")
        if p:
            head.append(f"{m}: strong − weak group {p['mean']:+.2f}%/month (t {p['t']:.1f})")
    ctx.step.detail = f"{gr.REPORT.name} written · " + " · ".join(head)


def _subindustries(ctx: Ctx) -> None:
    """Official industry codes (BSE for India, Nasdaq for the US: marketdata/classcodes.py) for new listings
    and codes older than 90 days, then the sub-industry coverage of tradable stocks."""
    from swing_screener.marketdata import classcodes, subindustries
    from swing_screener.screens import snapshot
    snap = snapshot.load(ctx.market)
    syms = list(snap["symbol"]) if not snap.empty else []
    r = classcodes.refresh_india(syms, force=bool(ctx.opt("force"))) if ctx.market == "india" else classcodes.refresh_us()
    d = subindustries.load_detail(ctx.market)
    trad = set(snap.loc[snap["tradable"], "symbol"]) if not snap.empty else set()
    split = [d[s] for s in trad if s in d]
    other = sum(1 for x in split if x[2] == "other")
    sug = sum(1 for x in split if x[2] == "suggested")
    ctx.step.detail = (f"codes: {r['fetched']:,} fetched in {r['requests']:,} request(s) · tradable stocks in split groups: {len(split):,}, "
                       f"{len(split) - other:,} labelled ({sug} suggested, awaiting review), {other} unassigned")
    ctx.step.stats = {**r, "split": len(split), "other": other, "suggested": sug}


# ------------------------------------------------------------------ data

def _prices(ctx: Ctx) -> None:
    from swing_screener.marketdata import freshness
    from swing_screener.marketdata.refresh import refresh
    r = refresh(ctx.market, force=bool(ctx.opt("force")))
    if not r["updated"]:
        raise RuntimeError(f"no symbols updated ({len(r['failed'])} failed) — is the data source reachable?")
    st = freshness.price_status(ctx.market)
    ctx.step.detail = (f"{r['updated']:,} / {r['requested']:,} symbols · {len(r['failed'])} failed · "
                       f"{len(r['stale'])} lagging · {r['elapsed_s']:.0f}s · {freshness.describe(st)}")
    ctx.step.stats = {"requested": r["requested"], "updated": r["updated"], "failed": len(r["failed"]),
                      "lagging": len(r["stale"]), "latest": st["latest"], "lag": st["lag"]}


def _splits(ctx: Ctx) -> None:
    from swing_screener.marketdata import splits
    sus = splits.detect(ctx.market)
    if sus.empty:
        ctx.step.detail = "no split-shaped gaps since each symbol's last full fetch"
        ctx.step.stats = {"gaps": 0}
        return
    r = splits.repair(ctx.market, sus)
    ctx.step.detail = (f"{r['gaps']} split-shaped gap(s) in {r['symbols']} symbol(s): full history re-fetched for {r['fixed']}; "
                       f"{r['gaps'] - r['still_there']} repaired, {r['still_there']} still there (real moves or a source error)")
    ctx.step.stats = r


def _indexes(ctx: Ctx) -> None:
    from swing_screener.analytics import breadth
    from swing_screener.marketdata import index_data
    got = breadth.fetch_indexes(ctx.market)
    index_data.refresh(ctx.market)
    missing = [k for k, n in got.items() if not n]
    if len(missing) == len(got):
        raise RuntimeError("no index series could be fetched")
    ctx.step.detail = (f"{len(got) - len(missing)}/{len(got)} index & VIX series"
                       + (f" · missing {', '.join(missing)}" if missing else "") + " · total-return series refreshed")


def _screened_symbols(market: str, strategies: list[str] | None = None) -> list[str]:
    """Symbols in the latest screening run of each strategy (those that passed the loose pre-filter)."""
    from swing_screener.marketdata import db
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT DISTINCT h.symbol FROM universe_history h JOIN (
                         SELECT strategy, max(run_id) run_id FROM universe_history WHERE market=%s GROUP BY strategy) l
                       ON l.strategy=h.strategy AND l.run_id=h.run_id WHERE h.market=%s""" + (" AND h.strategy = ANY(%s)" if strategies else ""),
                    (market, market, strategies) if strategies else (market, market))
        return [r[0] for r in cur.fetchall()]


def _earnings(ctx: Ctx) -> None:
    from swing_screener.marketdata import earnings
    from swing_screener.screening import watchlist
    syms = set(_screened_symbols(ctx.market))
    for lst in watchlist.lists():
        syms |= {i["symbol"] for i in watchlist.items(lst["id"]) if i["market"] == ctx.market}
    got = earnings.load_earnings_days_away(ctx.market, sorted(syms))  # re-checks entries older than a week
    ctx.step.detail = f"{len(syms):,} screened / watchlisted symbols checked · {len(got):,} with a known next date"


def _fundamentals(ctx: Ctx) -> None:
    from swing_screener.marketdata import fundamentals
    from swing_screener.strategies import _REGISTRY
    wanting = [k for k, s in _REGISTRY.items() if getattr(s, "wants_live_fundamentals", False)]
    syms = _screened_symbols(ctx.market, wanting)
    if not syms:
        ctx.step.skip("no screened symbols for strategies that use live fundamentals (" + ", ".join(wanting) + ")")
        return
    got = fundamentals.load_fundamentals(ctx.market, syms)  # re-fetches entries older than a week
    ctx.step.detail = f"{len(got):,} / {len(syms):,} symbols have fundamentals (for {', '.join(wanting)})"


# ------------------------------------------------------------------ analytics

def _breadth(ctx: Ctx) -> None:
    from swing_screener.analytics import breadth
    from swing_screener.marketdata import db
    breadth.init_schema()
    n = breadth.compute(ctx.market)
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT max(date) FROM breadth_daily WHERE market=%s", (ctx.market,))
        last = cur.fetchone()[0]
    ctx.step.detail = f"{n} day(s) written · latest {last}"


SECTOR_DAILY_SCHEMA = """
CREATE TABLE IF NOT EXISTS sector_daily (
    market VARCHAR(16) NOT NULL, date DATE NOT NULL, level TEXT NOT NULL, grp TEXT NOT NULL,
    sector TEXT, n INT, rs INT, rs_prev INT, quadrant TEXT,
    ew_1m DOUBLE PRECISION, ew_3m DOUBLE PRECISION, ew_6m DOUBLE PRECISION, ew_12m DOUBLE PRECISION,
    rel_3m DOUBLE PRECISION, above50 DOUBLE PRECISION, above200 DOUBLE PRECISION, highs INT, lows INT,
    PRIMARY KEY (market, date, level, grp)
);
"""


def _sectors(ctx: Ctx) -> None:
    """Rank sectors / industry groups and keep each day's ranking (`sector_daily`) — the history behind
    the playbook's "RS rating over time" and alerts. The web page computes its own live view."""
    from swing_screener.analytics import sectors
    from swing_screener.marketdata import db
    r = sectors.compute(ctx.market)
    if r.get("empty"):
        raise RuntimeError(f"no industry classification yet — run: jobs run industries --market {ctx.market}")
    with db.get_connection().cursor() as cur:
        cur.execute(SECTOR_DAILY_SCHEMA)
    rows = [(ctx.market, r["date"], level, g["group"], g["sector"], g["n"], g["rs"], g["rs_prev"], g["quadrant"],
             g["ew"]["1M"], g["ew"]["3M"], g["ew"]["6M"], g["ew"]["12M"], g["rel"]["3M"], g["above50"], g["above200"],
             g["highs"], g["lows"]) for level in ("industry", "sector", "sub") for g in r.get(level, [])]
    db.execute_values("""INSERT INTO sector_daily VALUES %s ON CONFLICT (market, date, level, grp) DO UPDATE SET
        sector=EXCLUDED.sector, n=EXCLUDED.n, rs=EXCLUDED.rs, rs_prev=EXCLUDED.rs_prev, quadrant=EXCLUDED.quadrant,
        ew_1m=EXCLUDED.ew_1m, ew_3m=EXCLUDED.ew_3m, ew_6m=EXCLUDED.ew_6m, ew_12m=EXCLUDED.ew_12m, rel_3m=EXCLUDED.rel_3m,
        above50=EXCLUDED.above50, above200=EXCLUDED.above200, highs=EXCLUDED.highs, lows=EXCLUDED.lows""", rows)
    top = ", ".join(g["group"] for g in r["industry"][:3])
    ctx.step.detail = (f"{len(r['sector'])} sectors, {len(r['industry'])} industry groups, {len(r.get('sub', []))} sub-industries "
                       f"ranked for {r['date']} · leading: {top}")


# ------------------------------------------------------------------ screening

def _check_prices(market: str, allow_stale: bool) -> str:
    from swing_screener.marketdata import freshness
    st = freshness.price_status(market)
    if st["latest"] is None:
        raise StaleData(f"no prices stored for {market} — run: jobs run prices --market {market}")
    if st["lag"] >= STALE_TRADING_DAYS and not allow_stale:
        raise StaleData(f"{freshness.describe(st)}. Run `jobs run prices --market {market}` first, "
                        f"or pass --allow-stale to screen anyway.")
    return freshness.describe(st)


def _screens(ctx: Ctx) -> None:
    """The day's stock snapshot (screens/snapshot.py): every field the screens filter on; screens query it live."""
    from swing_screener.screens import definitions, snapshot
    df = snapshot.build(ctx.market)
    counts = {k: int(definitions.mask(df, v["conditions"]).sum()) for k, v in {**definitions.builtin(), **definitions.presets()}.items()}
    ctx.step.detail = (f"snapshot of {len(df):,} stocks ({int(df['tradable'].sum()):,} tradable) for {df.attrs.get('date', '')} · "
                       + " · ".join(f"{k} {v}" for k, v in counts.items()))
    ctx.step.stats = {"stocks": len(df), "tradable": int(df["tradable"].sum()), **counts}


def _screen_history(ctx: Ctx) -> None:
    """Month-end snapshots for the screen study (screens/snapshot.py --backfill): builds any of the last
    `years` (default 5) years' month-ends that are missing. The daily job keeps each month's last session
    itself, so after the first run this is a cheap gap check; studies are then computed on demand."""
    from swing_screener.screens import snapshot, study
    n = snapshot.backfill(ctx.market, float(ctx.opt("years") or 5), bool(ctx.opt("force")))
    ctx.step.detail = f"{n} month-end snapshots built · {len(study.month_end_dates(ctx.market))} month-ends available to the study"
    ctx.step.stats = {"built": n}


BACKTEST_START = "2013-01-01"   # `backtest` simulates from here unless the request sets `start`


def _backtest_steps(ctx: Ctx) -> list:
    """One step per picked strategy. Each runs the full walk-forward backtest with that strategy's
    documented arguments (`Strategy.backtest_args` — its real exit policy, the same command the
    Strategies page shows), reports live progress to the run log, and leaves the report for the
    `ingest` job to load. Offline and slow: it reads stored prices only."""
    from swing_screener.strategies import DEFAULT_STRATEGY, list_strategies
    keys = ctx.opt("strategies") or [DEFAULT_STRATEGY]
    if keys == ["all"]:
        keys = list_strategies()

    def one(key):
        def fn(c: Ctx) -> None:
            import shlex
            from swing_screener.backtesting import backtest as bt
            from swing_screener.marketdata import cache
            from swing_screener.strategies import get_strategy
            cls = type(get_strategy(key))
            start = str(c.opt("start") or BACKTEST_START)
            argv = ["--market", c.market, "--start", start, "--strategy", key] + shlex.split(cls.backtest_args or "")
            if c.opt("sample"):
                argv += ["--sample", str(int(c.opt("sample")))]
            for kv in (c.opt("vcp") or []):
                argv += ["--vcp", str(kv)]
            if c.opt("accept_labels"):
                # after backtest_args on purpose: argparse keeps the last --accept-labels
                argv += ["--accept-labels", str(c.opt("accept_labels"))]
            argv += ["--no-ingest"]   # the pipeline's own ingest job loads the report
            bt.on_progress = c.step.progress
            try:
                with cache.offline():   # stored prices only — the `prices` job downloads
                    r = bt.main(argv)
            finally:
                bt.on_progress = None
            if r:
                p = r["perf"]
                c.step.detail = (f"{r['trades']} trades · CAGR {p.cagr_pct:+.2f}% · max DD {p.max_drawdown_pct:.1f}% · "
                                 f"avg {p.avg_r:+.2f}R · {r['run_dir']}")
                c.step.stats = {"trades": r["trades"], "cagr_pct": round(p.cagr_pct, 2),
                                "max_drawdown_pct": round(p.max_drawdown_pct, 1), "avg_r": round(p.avg_r, 3),
                                "start": start, "run_dir": str(r["run_dir"])}
        return (f"backtest:{key}", f"backtest · {key}", fn)
    return [one(k) for k in keys]


def _strategy_steps(ctx: Ctx) -> list:
    from swing_screener.strategies import DEFAULT_STRATEGY, list_strategies
    keys = ctx.opt("strategies") or [DEFAULT_STRATEGY]
    if keys == ["all"]:
        keys = list_strategies()

    def one(key):
        def fn(c: Ctx) -> None:
            from swing_screener.marketdata import cache
            from swing_screener.screening import pipeline
            note = _check_prices(c.market, bool(c.opt("allow_stale")))
            with cache.offline():  # stored prices only — the `prices` job downloads
                df = pipeline.run(c.market, refresh_universe=False, strategy_key=key)
            trade = int((df["tradeable"] == True).sum()) if "tradeable" in df else 0  # noqa: E712
            watch = int((df["watchlist_candidate"] == True).sum()) if "watchlist_candidate" in df else 0  # noqa: E712
            c.step.detail = f"{len(df):,} screened · {trade} tradeable · {watch} watchlist · {note}"
            c.step.stats = {"screened": len(df), "tradeable": trade, "watchlist": watch}
        return (f"strategy:{key}", f"strategy · {key}", fn)
    return [one(k) for k in keys]


def _quality(ctx: Ctx) -> None:
    from fundamentals import quality
    from swing_screener.marketdata import db
    quality.init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT market, symbol FROM quality_watch WHERE market=%s ORDER BY added_at", (ctx.market,))
        todo = list(cur.fetchall())
    top = int(ctx.opt("quality_top", QUALITY_TOP[ctx.market]))
    want = len(todo) + top
    todo += [(ctx.market, s) for s in quality.candidates(ctx.market, top)]
    seen, unique = set(), []
    for t in todo:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    r = quality.run(ctx.market, unique, QUALITY_MAX_AGE_DAYS, 0.5, want)
    ctx.step.detail = ", ".join(f"{k.replace('_', ' ')} {v:,}" for k, v in r.items())
    ctx.step.stats = r


# ------------------------------------------------------------------ publish

def _postmarket(ctx: Ctx) -> None:
    """The day's post-market analysis (analytics/postmarket.py), stored per day; `--days N` backfills."""
    from swing_screener.analytics import postmarket
    days = int(ctx.opt("days", 1))
    done = postmarket.run(ctx.market, days=days, force=bool(ctx.opt("force")))
    if not done:
        ctx.step.skip(f"already stored for the last {days} session(s)")
        return
    with postmarket.db.get_connection().cursor() as cur:
        cur.execute("SELECT payload->'tone'->>'label', payload->'counts' FROM postmarket_daily WHERE market=%s AND date=%s",
                    (ctx.market, done[-1]))
        tone, counts = cur.fetchone()
    ctx.step.detail = (f"{len(done)} day(s) analysed, latest {done[-1]} · tone {tone} · "
                       f"{counts['up']:,} up / {counts['down']:,} down · {counts['new_highs']} new highs, {counts['new_lows']} lows")


def _report(ctx: Ctx) -> None:
    """The consolidated daily review, from each strategy's latest run per market (screened in the last day)."""
    import pandas as pd

    from swing_screener.config import MARKETS as MCFG
    from swing_screener.marketdata import db
    from swing_screener.paths import REPORTS_DIR
    from swing_screener.screening import candidates_report
    since = (dt.datetime.now() - dt.timedelta(hours=30)).strftime("%Y-%m-%d_%H%M%S")
    by_strategy: dict[str, dict] = {}
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT market, strategy, max(run_id) FROM universe_history WHERE run_id >= %s
                       GROUP BY market, strategy ORDER BY strategy, market""", (since,))
        latest = cur.fetchall()
        for market, strategy, run_id in latest:
            cur.execute("SELECT full_row FROM universe_history WHERE market=%s AND strategy=%s AND run_id=%s",
                        (market, strategy, run_id))
            recs = [r[0] for r in cur.fetchall()]
            df = pd.DataFrame(recs)
            df.attrs["market_name"] = MCFG[market].name
            by_strategy.setdefault(strategy, {})[market] = df
    if not by_strategy:
        ctx.step.skip("no screening runs in the last day")
        return
    today = str(dt.date.today())
    md = candidates_report.write_combined(REPORTS_DIR / "daily" / today, by_strategy, {}, today)
    from swing_screener.screening.daily import _print_cross_market_summary
    for key, by_market in by_strategy.items():
        _print_cross_market_summary(by_market, {}, key)
    ctx.step.detail = f"{md} · {len(latest)} strategy/market runs"


def _ingest(ctx: Ctx) -> None:
    from swing_screener.web.ingest import ingest
    r = ingest()
    ctx.step.detail = f"{r['runs']} report runs in the viewer"


# ------------------------------------------------------------------ registry

JOBS: dict[str, Job] = {j.name: j for j in [
    Job("universe", "reference", "universe list: the symbols each market screens (Nasdaq Trader / NSE)", "weekly", True, _universe),
    Job("names", "reference", "company names: from the exchanges' symbol lists", "weekly", True, _names),
    Job("classify", "reference", "stock vs fund labels: India ETFs/funds kept out of breadth", "weekly", True, _classify, after=("prices",)),
    Job("industries", "reference", "industry classification: sector, industry and market cap (Sectors page)", "monthly", True, _industries),
    Job("subindustries", "reference", "sub-industries: official industry codes (BSE / Nasdaq) and the sub-industry coverage", "monthly", True,
        _subindustries, after=("industries",)),
    Job("prices", "data", "prices: daily bars for the whole universe", "daily", True, _prices, after=("universe",)),
    Job("splits", "data", "splits & bonus issues: re-fetch the full history of stocks that split after their last full fetch",
        "weekly", True, _splits, after=("prices",)),
    Job("indexes", "data", "index & VIX series: benchmarks, volatility, total-return series", "daily", True, _indexes),
    Job("earnings", "data", "earnings dates: next report date for screened and watchlisted stocks", "weekly", True, _earnings),
    Job("fundamentals", "data", "live fundamentals: sales/earnings growth for strategies that use them", "weekly", True, _fundamentals),
    Job("breadth", "analytics", "market breadth: advancers, highs/lows, % above averages", "daily", False, _breadth, after=("prices",)),
    Job("sectors", "analytics", "sector ranking: RS ratings, rotation, breadth per group (kept daily)", "daily", False, _sectors,
        after=("prices", "industries")),
    Job("screens", "screening", "screens: the day's stock snapshot (~45 fields per stock) every screen queries", "daily", False, _screens,
        after=("prices",)),
    Job("screen_history", "screening", "screen history: month-end stock snapshots the screen study reads (fills gaps)", "monthly",
        False, _screen_history, after=("prices",)),
    Job("strategies", "screening", "strategies: today's setups — entry, stop, target and decision per strategy", "on demand", False,
        after=("prices",), expand=_strategy_steps),
    Job("backtest", "screening", "backtest: walk-forward simulation of a strategy's full history, with its documented exit policy (slow)",
        "on demand", False, after=("prices",), expand=_backtest_steps),
    Job("group_research", "screening", "research: does group strength improve forward returns? (writes research/group-strength-study.md)",
        "monthly", False, _group_research, per_market=False, after=("screen_history",)),
    Job("quality", "screening", "quality scores: fetch statements and score companies", "on demand", True, _quality),
    Job("postmarket", "publish", "post-market analysis: the day's tone, indices, breadth, sectors, movers, watchlists, screener changes",
        "daily", False, _postmarket, after=("prices",)),
    Job("report", "publish", "consolidated report: the daily review across strategies and markets", "on demand", False, _report,
        per_market=False, after=("strategies",)),
    Job("ingest", "publish", "load reports into the web app", "on demand", False, _ingest, per_market=False),
]}

# A pipeline is an ordered list of jobs, optionally with per-job options, and `defaults` for options the
# request does not set. Scheduled (jobs/queue.py DEFAULT_SCHEDULES): daily, weekly, monthly — data only.
# On demand (Run in the portal, or schedule them yourself): strategies, quality.
PIPELINES: dict[str, dict] = {
    "daily": {"summary": "after each market's close — data only: prices, indexes, breadth, sectors, the screens' snapshot, post-market analysis",
              "jobs": ["universe", "prices", "indexes", "breadth", "sectors", "screens", "postmarket"]},
    "strategies": {"summary": "on demand: today's setups for the chosen strategies (all by default), the daily review report, loaded into the app",
                   "jobs": ["strategies", "report", "ingest"], "defaults": {"strategies": ["all"]}},
    "backtest": {"summary": "on demand: backtest the chosen strategies over their full history and load the reports — slow (minutes to hours per strategy)",
                 "jobs": ["backtest", "ingest"]},
    "weekly": {"summary": "reference data: universe list, company names, fund labels, earnings dates, fundamentals; split & bonus repair",
               "jobs": [("universe", {"force": True}), "names", "classify", "splits", "earnings", "fundamentals"]},
    "monthly": {"summary": "re-classify industries and sub-industries, fill gaps in the month-end snapshot history, re-run the group-strength study",
                "jobs": [("industries", {"force": True}), "subindustries", "screen_history", "group_research", "ingest"]},
    "quality": {"summary": "on demand: fetch financial statements and score companies (the Quality screen) — slow, network-heavy",
                "jobs": ["quality"]},
}
