"""Every offline job, in layers, and the pipelines that chain them.

Layers (each reads only what the layers above it produced):

  reference   which symbols exist and what they are          universe, names, classify, industries
  data        raw time series and company data (network)     prices, indexes, earnings, fundamentals
  analytics   market-wide measures from stored prices        breadth, sectors
  screening   stock selection from stored data               screen (one step per strategy), quality
  publish     what the web app shows                         report, ingest

Two rules keep the layers honest:
  * data jobs never screen, and analytics / screening never download prices
    (`screen` runs inside `cache.offline()` and refuses to run on prices two or
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
STALE_TRADING_DAYS = 2         # `screen` refuses prices this many trading days behind (holidays make 1 ambiguous)


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
        ctx.step.skip("not needed: the US universe list already excludes ETFs and funds")
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
             g["highs"], g["lows"]) for level in ("industry", "sector") for g in r[level]]
    db.execute_values("""INSERT INTO sector_daily VALUES %s ON CONFLICT (market, date, level, grp) DO UPDATE SET
        sector=EXCLUDED.sector, n=EXCLUDED.n, rs=EXCLUDED.rs, rs_prev=EXCLUDED.rs_prev, quadrant=EXCLUDED.quadrant,
        ew_1m=EXCLUDED.ew_1m, ew_3m=EXCLUDED.ew_3m, ew_6m=EXCLUDED.ew_6m, ew_12m=EXCLUDED.ew_12m, rel_3m=EXCLUDED.rel_3m,
        above50=EXCLUDED.above50, above200=EXCLUDED.above200, highs=EXCLUDED.highs, lows=EXCLUDED.lows""", rows)
    top = ", ".join(g["group"] for g in r["industry"][:3])
    ctx.step.detail = f"{len(r['industry'])} industry groups, {len(r['sector'])} sectors ranked for {r['date']} · leading: {top}"


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


def _screen_steps(ctx: Ctx) -> list:
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
        return (f"screen:{key}", f"screening · {key}", fn)
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
    Job("prices", "data", "prices: daily bars for the whole universe", "daily", True, _prices, after=("universe",)),
    Job("indexes", "data", "index & VIX series: benchmarks, volatility, total-return series", "daily", True, _indexes),
    Job("earnings", "data", "earnings dates: next report date for screened and watchlisted stocks", "weekly", True, _earnings),
    Job("fundamentals", "data", "live fundamentals: sales/earnings growth for strategies that use them", "weekly", True, _fundamentals),
    Job("breadth", "analytics", "market breadth: advancers, highs/lows, % above averages", "daily", False, _breadth, after=("prices",)),
    Job("sectors", "analytics", "sector ranking: RS ratings, rotation, breadth per group (kept daily)", "daily", False, _sectors,
        after=("prices", "industries")),
    Job("screen", "screening", "screening: every strategy over stored prices", "daily", False, after=("prices",), expand=_screen_steps),
    Job("quality", "screening", "quality scores: fetch statements and score companies", "weekly", True, _quality),
    Job("report", "publish", "consolidated report: the daily review across strategies and markets", "daily", False, _report,
        per_market=False, after=("screen",)),
    Job("ingest", "publish", "load reports into the web app", "daily", False, _ingest, per_market=False),
]}

# A pipeline is an ordered list of jobs, optionally with per-job options.
PIPELINES: dict[str, dict] = {
    "daily": {"summary": "after each market's close: prices, indexes, breadth, sectors, screening, report",
              "jobs": ["universe", "prices", "indexes", "breadth", "sectors", "screen", "report", "ingest"]},
    "weekly": {"summary": "reference data, earnings dates, fundamentals, quality scores",
               "jobs": [("universe", {"force": True}), "names", "classify", "earnings", "fundamentals", "quality"]},
    "monthly": {"summary": "re-classify industries (Sectors page)", "jobs": [("industries", {"force": True})]},
}
