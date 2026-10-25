"""Every offline job, in layers, and the pipelines that chain them.

Layers (each reads only what the layers above it produced):

  reference   which symbols exist and what they are          universe, names, classify, industries
  data        raw time series and company data (network)     prices, indexes, earnings, fundamentals, financials
  analytics   market-wide measures from stored prices        breadth, sectors
  screening   stock selection from stored data               screens, strategies (one step per strategy), backtest, quality, fundamental_scores
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
FINANCIALS_TOP = {"us": 1500, "india": 500}    # `financials` covers the N most liquid tradable stocks + every Stage-2 stock
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
    eod = r.get("eod") or {}
    eod_txt = ""
    if eod.get("source"):
        eod_txt = (f" · {eod['source']}: " + (f"error {eod['error'][:80]}" if eod.get("error") else
                   ", ".join(f"{x['day']} +{x['added']:,}" for x in eod["days"]) or "nothing missing")
                   + (f" (no file yet for {', '.join(eod['absent'])})" if eod.get("absent") else ""))
    ctx.step.detail = (f"{r['updated']:,} / {r['requested']:,} symbols · {len(r['failed'])} failed · "
                       f"{len(r['stale'])} lagging · {r['elapsed_s']:.0f}s · {freshness.describe(st)}{eod_txt}")
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


def _sessions(ctx: Ctx) -> None:
    from swing_screener.marketdata import sessions
    r = sessions.repair(ctx.market, apply=True)
    if not r["stray_sessions"]:
        ctx.step.detail = "no stray sessions: every stored date is priced for most of the market"
    else:
        ctx.step.detail = (f"{len(r['stray_sessions'])} stray session(s) removed ({', '.join(r['stray_sessions'])}): "
                           f"{r['bars_removed']} bar(s) in {r['symbols']} symbol(s)")
    ctx.step.stats = {"stray_sessions": len(r["stray_sessions"]), "bars_removed": r["bars_removed"], "symbols": r["symbols"]}


def _fno_bhav(ctx: Ctx) -> None:
    """NSE's daily derivatives bhavcopy (marketdata/derivatives.py): every index future and option
    that traded, with its settle price and open interest. India only — US options history is not
    freely available. Index derivatives only by default (~4,000-7,500 rows a day against 31,000-47,000
    for everything); stock options are thin outside the top names and a backtest on thin strikes
    flatters itself. Stage 1 of research/fno-scope.md: stored and reconciled, not yet traded."""
    from swing_screener.marketdata import derivatives
    if ctx.market != "india":
        ctx.step.skip("NSE derivatives are India only")
        return
    # scheduled runs look back `recent_days` only; the full history (from FIRST_DAY) is a one-off run without it
    start = (dt.date.fromisoformat(str(ctx.opt("start"))) if ctx.opt("start") else
             dt.date.today() - dt.timedelta(days=int(ctx.opt("recent_days"))) if ctx.opt("recent_days") else None)
    out = derivatives.ingest(ctx.market, start=start,
                             instruments=() if ctx.opt("all_instruments") else derivatives.INDEX_INSTRUMENTS)
    ctx.step.detail = (f"{out['rows']:,} contract rows from {out['sessions']} sessions"
                       + (f" · {out['no_file']} days had no file" if out["no_file"] else ""))
    ctx.step.stats = out


def _indexes(ctx: Ctx) -> None:
    from swing_screener.analytics import breadth
    from swing_screener.marketdata import index_data, macro
    got = breadth.fetch_indexes(ctx.market)
    index_data.refresh(ctx.market)
    mac = macro.refresh(ctx.market)
    missing = [k for k, n in got.items() if not n]
    if len(missing) == len(got):
        raise RuntimeError("no index series could be fetched")
    mac_missing = [k for k, n in mac.items() if not n]
    ctx.step.detail = (f"{len(got) - len(missing)}/{len(got)} index & VIX series"
                       + (f" · missing {', '.join(missing)}" if missing else "")
                       + f" · {len(mac) - len(mac_missing)}/{len(mac)} macro series ({', '.join(mac)})"
                       + (f" · missing {', '.join(mac_missing)}" if mac_missing else "")
                       + " · total-return series refreshed")
    ctx.step.stats = {"indexes": len(got) - len(missing), "macro": len(mac) - len(mac_missing)}


def _rates(ctx: Ctx) -> None:
    """Policy rates and bill / bond yields with long history (marketdata/rates.py): FRED for the US, RBI's
    homepage for India. Writes only new or changed values and names any policy-rate change it sees."""
    from swing_screener.marketdata import rates
    out = rates.refresh(ctx.market)
    ok = [k for k in out["written"] if k not in out["failed"]]
    if not ok:
        raise RuntimeError("no rate series could be fetched: " + "; ".join(f"{k}: {v}" for k, v in out["failed"].items()))
    n = sum(out["written"].values())
    ctx.step.detail = (f"{len(ok)} series · {n:,} new or changed values"
                       + (f" · changed: {'; '.join(out['changes'])}" if out["changes"] else "")
                       + (f" · failed: {', '.join(out['failed'])}" if out["failed"] else ""))
    ctx.step.stats = {"series": len(ok), "written": n, "changes": len(out["changes"]), "failed": len(out["failed"])}


def _funds(ctx: Ctx) -> None:
    """Mutual fund NAVs (marketdata/funds.py): every direct-plan growth option from AMFI for India, a
    curated list from Yahoo for the US. One small request for the days since the last stored NAV, plus any
    month of history not yet stored — so the first run is the (long, resumable) backfill."""
    from swing_screener.marketdata import funds
    r = funds.refresh(ctx.market, progress=ctx.step.progress)
    if not r["funds"]:
        raise RuntimeError("no fund NAVs could be fetched" + (f" (failed: {', '.join(r['failed'])})" if r["failed"] else ""))
    newest = r["newest"].date().isoformat() if r["newest"] is not None else "none"
    ctx.step.detail = (f"{r['funds']:,} funds · {r['written']:,} NAVs written"
                       + (f" ({r['backfilled']:,} from history)" if r["backfilled"] else "")
                       + f" · newest {newest}"
                       + (f" · failed: {', '.join(r['failed'])}" if r["failed"] else ""))
    ctx.step.stats = {"funds": r["funds"], "written": r["written"], "backfilled": r["backfilled"], "failed": len(r["failed"])}


def _indicators(ctx: Ctx) -> None:
    """Growth, inflation, consumption, housing and credit indicators (marketdata/indicators.py): CPI,
    GDP, industrial production, durable goods, retail and vehicle sales, housing starts/permits, the
    mortgage rate, bank credit and the Baa credit spread — from FRED's free CSV endpoint; for India also
    MoSPI's IIP API (general index, consumer durables/non-durables) and Vahan vehicle registrations."""
    from swing_screener.marketdata import indicators
    out = indicators.refresh(ctx.market)
    ok = [k for k in out["written"] if k not in out["failed"]]
    if not ok:
        raise RuntimeError("no indicator series could be fetched: " + "; ".join(f"{k}: {v}" for k, v in out["failed"].items()))
    n = sum(out["written"].values())
    ctx.step.detail = (f"{len(ok)} series · {n:,} new or changed values"
                       + (f" · failed: {', '.join(out['failed'])}" if out["failed"] else ""))
    ctx.step.stats = {"series": len(ok), "written": n, "failed": len(out["failed"])}


def _flows(ctx: Ctx) -> None:
    """FII/DII daily net institutional equity flows (marketdata/flows.py): NSE's provisional cash-market
    activity. India only; an unofficial, scraped endpoint, so a fetch failure is recorded but does not
    fail the job — the same tolerance the RBI rate scrape already gets."""
    if ctx.market != "india":
        ctx.step.skip("FII/DII flows are India only")
        return
    from swing_screener.marketdata import flows
    out = flows.refresh(ctx.market)
    ok = [k for k in out["written"] if k not in out["failed"]]
    if not ok:
        raise RuntimeError("no flow series could be fetched: " + "; ".join(f"{k}: {v}" for k, v in out["failed"].items()))
    ctx.step.detail = f"{len(ok)} series" + (f" · failed: {', '.join(out['failed'])}" if out["failed"] else "")
    ctx.step.stats = {"series": len(ok), "failed": len(out["failed"])}


def _fpi_sectors(ctx: Ctx) -> None:
    """Fortnightly FPI net equity investment by sector (marketdata/fpi_sectors.py): NSDL's FPI Monitor
    reports. India only; scraped static pages, so a report that fails is recorded but does not fail the
    job, and it is tried again next run — the same tolerance the RBI rate scrape gets."""
    if ctx.market != "india":
        ctx.step.skip("NSDL sector-wise FPI flows are India only")
        return
    from swing_screener.marketdata import fpi_sectors
    out = fpi_sectors.refresh(ctx.market, progress=ctx.step.progress)
    if not out["written"] and out["failed"]:
        raise RuntimeError("no NSDL sector report could be read: " + "; ".join(f"{k}: {v}" for k, v in list(out["failed"].items())[:5]))
    ctx.step.detail = (f"{out['written']} fortnights · {out['rows']:,} sector rows"
                       + (f" · newest {out['newest']}" if out["newest"] else "")
                       + (f" · failed: {', '.join(out['failed'])}" if out["failed"] else ""))
    ctx.step.stats = {"fortnights": out["written"], "rows": out["rows"], "failed": len(out["failed"])}


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


def _news_symbols(market: str) -> list[str]:
    """What the morning news run covers: every watchlist, plus the names a strategy marks tradeable or
    on watch in its latest run. Not the whole screened set (~2,000 names a day would be hours of
    polite requests); any other stock is fetched on demand when its chart opens."""
    from swing_screener.marketdata import db
    from swing_screener.screening import watchlist
    syms = set()
    for lst in watchlist.lists():
        syms |= {i["symbol"] for i in watchlist.items(lst["id"]) if i["market"] == market}
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT DISTINCT h.symbol FROM universe_history h JOIN (
                         SELECT strategy, max(run_id) run_id FROM universe_history WHERE market=%s GROUP BY strategy) l
                       ON l.strategy=h.strategy AND l.run_id=h.run_id
                       WHERE h.market=%s AND (h.tradeable OR (h.full_row->>'watchlist_candidate')::boolean)""", (market, market))
        syms |= {r[0] for r in cur.fetchall()}
    return sorted(syms)


def _news(ctx: Ctx) -> None:
    from swing_screener.marketdata import news
    if ctx.opt("symbols"):
        syms = [s.strip().upper() for s in str(ctx.opt("symbols")).split(",") if s.strip()]
    else:
        syms = _news_symbols(ctx.market)
    if not syms:
        ctx.step.skip("no watchlisted or picked symbols to fetch news for")
        return
    r = news.refresh(ctx.market, syms, force=bool(ctx.opt("force")), progress=ctx.step.progress)
    ctx.step.detail = (f"{r['fetched']:,} / {r['requested']:,} symbols fetched ({r['skipped_fresh']:,} still fresh) · "
                       f"{r['headlines']:,} headlines · {r['events']:,} events · {r['failed']} failed")
    ctx.step.stats = r


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


THEME_HISTORY_YEARS = 3     # how far back a theme's weekly RS rating is rebuilt


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
    # themes, keyed by id (a rename keeps the history) with the name in `sector`; only those with enough members
    rows += [(ctx.market, r["date"], "theme", str(g["theme_id"]), g["group"], g["n"], g["rs"], g["rs_prev"], g["quadrant"],
              g["ew"]["1M"], g["ew"]["3M"], g["ew"]["6M"], g["ew"]["12M"], g["rel"]["3M"], g["above50"], g["above200"],
              g["highs"], g["lows"]) for g in r.get("theme", []) if g.get("ew")]
    db.execute_values("""INSERT INTO sector_daily VALUES %s ON CONFLICT (market, date, level, grp) DO UPDATE SET
        sector=EXCLUDED.sector, n=EXCLUDED.n, rs=EXCLUDED.rs, rs_prev=EXCLUDED.rs_prev, quadrant=EXCLUDED.quadrant,
        ew_1m=EXCLUDED.ew_1m, ew_3m=EXCLUDED.ew_3m, ew_6m=EXCLUDED.ew_6m, ew_12m=EXCLUDED.ew_12m, rel_3m=EXCLUDED.rel_3m,
        above50=EXCLUDED.above50, above200=EXCLUDED.above200, highs=EXCLUDED.highs, lows=EXCLUDED.lows""", rows)
    # keep the rebuilt RS history current: today's industry / sub-industry ratings, and each theme's
    # weekly rating over the last THEME_HISTORY_YEARS (only the dates not stored yet are computed)
    from swing_screener.analytics import group_history
    import pandas as pd
    day = pd.Timestamp(r["date"]).date()
    group_history.ensure(ctx.market, [day])
    weekly = [d.date() for d in pd.date_range(end=pd.Timestamp(day), periods=52 * THEME_HISTORY_YEARS, freq="W-FRI")]
    n_theme = group_history.ensure_themes(ctx.market, weekly + [day])
    top = ", ".join(g["group"] for g in r["industry"][:3])
    ctx.step.detail = (f"{len(r['sector'])} sectors, {len(r['industry'])} industry groups, {len(r.get('sub', []))} sub-industries, "
                       f"{len(r.get('theme', []))} themes ranked for {r['date']} · leading: {top}"
                       + (f" · {n_theme} theme history rows added" if n_theme else ""))


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


def _last_ok(step: str, market: str | None):
    """When `step` last finished OK for `market` (None: a market-wide step), from the run log (job_steps).
    A step name ending in ':' matches every step with that prefix (e.g. "strategy:")."""
    from swing_screener.marketdata import db
    op, name = ("LIKE", step + "%") if step.endswith(":") else ("=", step)
    with db.get_connection().cursor() as cur:
        cur.execute(f"SELECT max(finished_at) FROM job_steps WHERE step {op} %s AND market IS NOT DISTINCT FROM %s "
                    "AND status='ok'", (name, market))
        return cur.fetchone()[0]


def _newer(step: str, market: str | None, than: str, than_market: str | None) -> bool:
    """Whether `step` last succeeded after `than` did — e.g. a strategy ran since the last report."""
    a, b = _last_ok(step, market), _last_ok(than, than_market)
    return bool(a and (b is None or a > b))


def _strategy_current(market: str, key: str) -> bool:
    """A strategy's setups are current when it last ran after the last successful price load."""
    ran, priced = _last_ok(f"strategy:{key}", market), _last_ok("prices", market)
    return bool(ran and priced and ran >= priced)


def _readiness(ctx: Ctx) -> None:
    """Before the open: is everything the day's decisions read in place? Prices for the last session, and
    every strategy's setups computed on them. Fails — red on the Data status page — when not, naming what
    is missing; a one-session lag only warns, since exchange holidays are not modelled."""
    from swing_screener.marketdata import freshness
    from swing_screener.strategies import list_strategies
    st = freshness.price_status(ctx.market)
    stale = [k for k in list_strategies() if not _strategy_current(ctx.market, k)]
    problems = []
    if st["latest"] is None or st["lag"] >= STALE_TRADING_DAYS:
        problems.append(freshness.describe(st))
    if stale:
        problems.append(f"setups not run on the latest prices: {', '.join(stale)}")
    ctx.step.stats = {"price_lag": st["lag"], "stale_strategies": len(stale)}
    if problems:
        raise StaleData("not ready for the open — " + "; ".join(problems))
    ctx.step.detail = (f"ready: {freshness.describe(st)}, setups current for all {len(list_strategies())} strategies"
                       + (" · one session behind — a holiday, or the close routine has not finished" if st["lag"] else ""))


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
    itself, so after the first run this is a cheap gap check; studies are then computed on demand. `--refill`
    recomputes the stored month-ends to add a field they were built without, keeping every stored value."""
    from swing_screener.screens import snapshot, study
    n = snapshot.backfill(ctx.market, float(ctx.opt("years") or 5), bool(ctx.opt("force")), bool(ctx.opt("refill")))
    ctx.step.detail = f"{n} month-end snapshots built · {len(study.month_end_dates(ctx.market))} month-ends available to the study"
    ctx.step.stats = {"built": n}


# A backtest's window comes from its STAGE -- swing_screener/backtesting/windows.py -- not a constant here.


def _backtest_steps(ctx: Ctx) -> list:
    """One step per picked strategy. Each runs the full walk-forward backtest with that strategy's
    documented arguments (`Strategy.backtest_args` — its real exit policy, the same command the
    Strategies page shows), reports live progress to the run log, and leaves the report for the
    `ingest` job to load. Offline and slow: it reads stored prices only."""
    from swing_screener.strategies import DEFAULT_STRATEGY, list_strategies, portfolio_strategies
    keys = ctx.opt("strategies") or [DEFAULT_STRATEGY]
    if keys == ["all"]:
        keys = list_strategies() + sorted(portfolio_strategies())

    def one(key):
        def fn(c: Ctx) -> None:
            # Every backtest runs inside a STAGE (backtesting/windows.py): a window to tune in, one to
            # verify in, and a read boundary between them, so an optimise run cannot see the years
            # kept back to judge it. The stage decides the dates; the body below only runs the strategy.
            from swing_screener.backtesting import windows
            from swing_screener.strategies import get_strategy as _get
            stage, start, end = windows.resolve(c.opt("stage"), c.opt("start"))
            spec = (portfolio_strategies()[key] if key in portfolio_strategies() else type(_get(key))).spec_id()
            repeat = windows.check(c.market, key, spec, c.opts) if stage == "verify" else False
            with windows.active(stage, start, end):
                out = _run(c, start)
            if out:
                # What this run changed about the strategy, beside its report, so the Strategies page can
                # tell the strategy as configured from an experiment on it. The run directory name alone
                # cannot: a `--bt` passthrough (a turnover floor, a rank buffer) moves no fingerprint, so
                # an experiment shares the spec_id of the real thing and read as its headline result.
                import json
                from pathlib import Path
                own = "" if key in portfolio_strategies() else (type(_get(key)).backtest_args or "")
                over = windows.overrides(c.opts, own)
                (Path(out) / "overrides.json").write_text(json.dumps(
                    {"overrides": over, "described": windows.describe(over), "stage": stage}, indent=1))
            if stage == "verify":
                windows.record(c.market, key, spec, c.opts, repeat, out)
            c.step.detail = f"[{stage} {start} → {end or 'latest'}] " + (c.step.detail or "")
            if c.step.stats is not None:
                c.step.stats.update(stage=stage, end=end)

        def _run(c: Ctx, start: str) -> str | None:
            import shlex
            from swing_screener.backtesting import backtest as bt
            from swing_screener.marketdata import cache
            from swing_screener.strategies import get_strategy

            # A PORTFOLIO strategy has no per-symbol screen to walk, so it is measured by the
            # baseline runner instead. Dispatching here rather than refusing is what lets the
            # Strategies page offer one Backtest button for every strategy it lists.
            if key in portfolio_strategies():
                # each portfolio strategy names the module that backtests it: a ranking strategy
                # goes to the baseline runner, an allocation rule to its own
                import importlib
                mod = getattr(portfolio_strategies()[key], "runner", "baseline")
                bl = importlib.import_module(f"swing_screener.backtesting.{mod}")
                # the stage decides the window for every strategy alike -- a strategy's own preferred
                # start would put different strategies on different windows and make them incomparable
                argv = ["--strategy", key, "--market", c.market, "--start", start, "--no-ingest"]
                for extra in (c.opt("bt") or []):
                    argv += shlex.split(str(extra))
                with cache.offline():   # stored prices only, like the gated backtest
                    r = bl.main(argv)
                if r:
                    pf = r["perf"]
                    c.step.detail = (f"{r['trades']} trades · CAGR {pf.cagr_pct:+.2f}% · "
                                     f"excess {pf.cagr_pct - (pf.benchmark_cagr_pct or 0):+.2f}% · "
                                     f"max DD {pf.max_drawdown_pct:.1f}% · {r['run_dir']}")
                return str(r["run_dir"]) if r else None

            cls = type(get_strategy(key))
            argv = ["--market", c.market, "--start", start, "--strategy", key] + shlex.split(cls.backtest_args or "")
            if c.opt("sample"):
                argv += ["--sample", str(int(c.opt("sample")))]
            for kv in (c.opt("vcp") or []):
                argv += ["--vcp", str(kv)]
            for kv in (c.opt("const") or []):
                argv += ["--const", str(kv)]
            if c.opt("symbols"):
                argv += ["--symbols", str(c.opt("symbols"))]
            if c.opt("max_base"):
                argv += ["--max-base", str(c.opt("max_base"))]
            if c.opt("min_dollar_volume"):
                argv += ["--min-dollar-volume", repr(float(c.opt("min_dollar_volume")))]
            if c.opt("pyramid"):
                argv += ["--pyramid", str(c.opt("pyramid"))]
            if c.opt("market_filter"):
                argv.append("--market-filter")
            if c.opt("pe"):
                argv.append("--pe")
            for _k in ("pe_window", "pe_warmup", "pe_pilot", "pe_press", "mkt_confirm", "top_dollar_volume"):
                if c.opt(_k) is not None:
                    argv += ["--" + _k.replace("_", "-"), str(c.opt(_k))]
            for extra in (c.opt("bt") or []):
                argv += shlex.split(str(extra))   # appended last, so a passthrough wins
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
            return str(r["run_dir"]) if r else None
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
            if c.opt("only_stale") and _strategy_current(c.market, key):
                c.step.skip("already ran on the latest prices")
                return
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


def _financials(ctx: Ctx) -> None:
    """Company financials for the Fundamentals page: the most liquid tradable stocks plus every stock passing
    the Trend Template in the latest snapshot (the technical leaders, whose businesses matter most); any other
    company is fetched when you open it (the page's "Fetch now", with --symbols).
    Only companies whose results may have changed are fetched (financials.due); --force fetches all."""
    from swing_screener.marketdata import financials
    from swing_screener.screens import definitions, snapshot
    financials.init_schema()
    if ctx.opt("symbols"):
        syms = [s.strip().upper() for s in str(ctx.opt("symbols")).split(",") if s.strip()]
    else:
        snap = snapshot.load(ctx.market)
        if snap.empty:
            ctx.step.skip("no stock snapshot yet: run `screens` first (the list is its most liquid and Stage-2 stocks)")
            return
        tradable = snap[snap["tradable"] == True]  # noqa: E712
        skip = financials.no_data(ctx.market)     # funds, ETFs: nothing filed at the last look
        liquid = [s for s in tradable.sort_values("value20", ascending=False)["symbol"] if s not in skip][:FINANCIALS_TOP[ctx.market]]
        stage2 = snap[definitions.mask(snap, definitions.builtin()["stage2"]["conditions"])]["symbol"]
        # groups split by revenue (marketdata/subindustries.py REVENUE_RULE_GROUPS) need every tradable member's results
        from swing_screener.marketdata import subindustries
        by_rev = tradable[tradable["industry"].isin(subindustries.REVENUE_RULE_GROUPS.get(ctx.market, ()))]["symbol"]
        syms = list(dict.fromkeys([*liquid, *(s for s in stage2 if s not in skip), *(s for s in by_rev if s not in skip)]))
    r = financials.run(ctx.market, syms, force=bool(ctx.opt("force")))
    ctx.step.detail = f"{len(syms):,} companies · " + ", ".join(f"{k.replace('_', ' ')} {v:,}" for k, v in r.items())
    ctx.step.stats = r


def _fundamental_scores(ctx: Ctx) -> None:
    from fundamentals import growth
    syms = [s.strip().upper() for s in str(ctx.opt("symbols")).split(",") if s.strip()] if ctx.opt("symbols") else None
    r = growth.run(ctx.market, syms)
    if not r["companies"]:
        ctx.step.skip("no quarterly results stored yet: run `financials` first")
        return
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
    if ctx.opt("only_new") and not any(_newer("strategy:", m, "report", None) for m in MARKETS):
        ctx.step.skip("no strategy has run since the last report")
        return
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
    if ctx.opt("only_new") and not _newer("report", None, "ingest", None):
        ctx.step.skip("no new report since the last load")
        return
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
    Job("sessions", "data", "stray sessions: remove bars the source dates on a holiday or weekend that most of the market "
        "did not trade, which would blank every symbol's 200-day average in a whole-market frame", "daily", False, _sessions,
        after=("prices",)),
    Job("indexes", "data", "index, VIX & macro series: benchmarks, volatility, total-return series, and rates, the dollar, "
        "oil, gold, copper and credit (marketdata/macro.py)", "daily", True, _indexes),
    Job("rates", "data", "interest rates: policy rate, bill and bond yields with long history — FRED (US), RBI (India) "
        "(marketdata/rates.py)", "daily", True, _rates),
    Job("funds", "data", "mutual fund NAVs: every direct-plan growth option from AMFI (India), a curated list (US); "
        "the first run backfills history (marketdata/funds.py)", "daily", True, _funds),
    Job("indicators", "data", "growth, inflation, consumption, housing and credit indicators: CPI, GDP, industrial "
        "production, durable goods, retail and vehicle sales, housing starts/permits, mortgage rate, bank credit, "
        "Baa credit spread — FRED; India IIP consumer groups (MoSPI) and vehicle registrations (Vahan) "
        "(marketdata/indicators.py)", "daily", True, _indicators),
    Job("flows", "data", "FII/DII daily net institutional equity flows: NSE's provisional cash-market activity "
        "(marketdata/flows.py, India only)", "daily", True, _flows),
    Job("fpi_sectors", "data", "FPI net equity investment by sector, per fortnight: NSDL's FPI Monitor reports "
        "(marketdata/fpi_sectors.py, India only)", "weekly", True, _fpi_sectors),
    Job("earnings", "data", "earnings dates: next report date for screened and watchlisted stocks", "weekly", True, _earnings),
    Job("fno_bhav", "data", "F&O bhavcopy: NSE index futures and options, settle and open interest (India)",
        "daily", True, _fno_bhav),
    Job("news", "data", "news & key events: headlines, filings, exchange announcements, earnings, dividends, splits "
        "for watchlisted and picked stocks (marketdata/news.py)", "daily", True, _news),
    Job("fundamentals", "data", "live fundamentals: sales/earnings growth for strategies that use them", "weekly", True, _fundamentals),
    Job("financials", "data", "company financials: quarterly and annual results, balance sheet, cash flow, shareholding "
        "(SEC / NSE filings) for the Fundamentals page", "weekly", True, _financials, after=("screens",)),
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
    Job("quality", "screening", "quality scores: fetch statements and score companies", "weekly", True, _quality),
    Job("fundamental_scores", "screening", "fundamentals: growth, margins and returns from the stored quarterly results, "
        "and each strategy's view of them (Minervini SEPA)", "weekly", False, _fundamental_scores, after=("financials",)),
    Job("postmarket", "publish", "post-market analysis: the day's tone, indices, breadth, sectors, movers, watchlists, screener changes",
        "daily", False, _postmarket, after=("prices",)),
    Job("readiness", "publish", "readiness check: before the open, prices for the last session and every strategy's setups "
        "computed on them", "daily, before the open", False, _readiness),
    Job("report", "publish", "consolidated report: the daily review across strategies and markets", "on demand", False, _report,
        per_market=False, after=("strategies",)),
    Job("ingest", "publish", "load reports into the web app", "on demand", False, _ingest, per_market=False),
]}

# A pipeline is an ordered list of jobs, optionally with per-job options, and `defaults` for options the
# request does not set. Scheduled (jobs/queue.py DEFAULT_SCHEDULES): close and open per market on that market's
# clock, weekly and monthly. `daily` (data only) is kept for running the data part alone.
# On demand (Run in the portal, or schedule them yourself): strategies; `quality` also runs alone this way.
PIPELINES: dict[str, dict] = {
    "close": {"summary": "the market close routine — the day's data, then every strategy's setups, the review report, "
                         "loaded into the app, so tomorrow's trades are ready without a manual run",
              "jobs": ["universe", "prices", "sessions", "indexes", "rates", "funds", "indicators", "flows", ("fno_bhav", {"recent_days": 10}), "breadth", "sectors",
                       "screens", "postmarket", "strategies", "report", "ingest"],
              "defaults": {"strategies": ["all"]}},
    "open": {"summary": "the market open routine — catch up any price load the close missed, refresh earnings dates and news, "
                        "re-run only the strategies left stale, then check everything is ready",
             # report and ingest only when a strategy actually re-ran: the report reads the last 30 hours,
             # so re-running it on a Monday morning would replace Friday's review with an empty one
             # funds again here: AMFI publishes the day's NAVs late in the evening, after India's close routine
             "jobs": ["prices", "funds", "earnings", "news", ("strategies", {"only_stale": True}), ("report", {"only_new": True}),
                      ("ingest", {"only_new": True}), "readiness"],
             "defaults": {"strategies": ["all"]}},
    "daily": {"summary": "after each market's close — data only: prices, indexes, rates, fund NAVs, breadth, sectors, the screens' snapshot, "
                         "post-market analysis",
              "jobs": ["universe", "prices", "sessions", "indexes", "rates", "funds", "indicators", "flows", ("fno_bhav", {"recent_days": 10}), "breadth", "sectors", "screens",
                       "postmarket"]},
    "strategies": {"summary": "on demand: today's setups for the chosen strategies (all by default), the daily review report, loaded into the app",
                   "jobs": ["strategies", "report", "ingest"], "defaults": {"strategies": ["all"]}},
    "backtest": {"summary": "on demand: backtest the chosen strategies over their full history and load the reports — slow (minutes to hours per strategy)",
                 "jobs": ["backtest", "ingest"]},
    "weekly": {"summary": "reference data: universe list, company names, fund labels, earnings dates, fundamentals, company financials "
                          "and their scores, quality scores; split & bonus repair",
               "jobs": [("universe", {"force": True}), "names", "classify", "splits", "earnings", "fundamentals", "financials", "fundamental_scores", "quality", "fpi_sectors"]},
    "monthly": {"summary": "re-classify industries and sub-industries, fill gaps in the month-end snapshot history, re-run the group-strength study",
                "jobs": [("industries", {"force": True}), "subindustries", "screen_history", "group_research", "ingest"]},
    "quality": {"summary": "on demand: fetch financial statements and score companies (the Quality screen) — slow, network-heavy",
                "jobs": ["quality"]},
    "company_financials": {"summary": "on demand: fetch new filings and recompute the Fundamentals page (the first run is slow); "
                                      "with --symbols, just those companies",
                           "jobs": ["financials", "fundamental_scores"]},
}


# ------------------------------------------------------------------ worker lanes (jobs/worker.py)
# The fast lane runs only these: short jobs that read stored data (seconds to a few minutes), so a
# page's screens rebuild or a setups refresh does not wait hours behind a backtest in the main lane.
# Anything not listed — backtests, downloads, month-end history, research — stays in the main lane.
FAST_JOBS = frozenset({"breadth", "sectors", "screens", "strategies", "postmarket", "report", "ingest", "readiness"})
# The backtest lane runs these: long jobs on stored data (minutes to many hours, no downloads), so a
# scheduled market routine in the main lane never waits behind one. Downloads stay in the main lane, so
# two lanes never hit the data sources at once.
RESEARCH_JOBS = frozenset({"backtest", "screen_history", "group_research"})
# short, idempotent publishing steps that may run in two lanes at once: they do not count as a clash, or a
# close routine ending in `ingest` would wait hours for a backtest that also ends in one
CLASH_EXEMPT = frozenset({"ingest", "report"})
# jobs that WRITE what the fast jobs read: while one runs for a market, no fast job starts for it
FEED_LAYERS = ("reference", "data")


def item_jobs(targets: list) -> list[str]:
    """The job names a queue item runs: its targets, with each pipeline expanded."""
    out = []
    for t in targets:
        if t in PIPELINES:
            out += [j if isinstance(j, str) else j[0] for j in PIPELINES[t]["jobs"]]
        else:
            out.append(t)
    return out


def fast_item(item: dict) -> bool:
    """Every job of the item is a fast one."""
    jobs = item_jobs(item["targets"])
    return bool(jobs) and all(j in FAST_JOBS for j in jobs)


def research_item(item: dict) -> bool:
    """A backtest-lane item: long research on stored data (publishing steps aside)."""
    jobs = [j for j in item_jobs(item["targets"]) if j not in CLASH_EXEMPT]
    return bool(jobs) and all(j in RESEARCH_JOBS for j in jobs)


def _markets_overlap(a: str | None, b: str | None) -> bool:
    return (a or "all") == "all" or (b or "all") == "all" or a == b


def clashes(item: dict, running: list) -> bool:
    """Starting `item` now would collide with a running item: the same job for the same market (two
    writers of one dataset), or — for a fast item — a data download in progress for that market (it
    would read a half-written update)."""
    mine = set(item_jobs(item["targets"])) - CLASH_EXEMPT
    for r in running:
        if not _markets_overlap(item.get("market"), r.get("market")):
            continue
        theirs = set(item_jobs(r["targets"])) - CLASH_EXEMPT
        if mine & theirs:
            return True
        if fast_item(item) and any(JOBS[j].layer in FEED_LAYERS for j in theirs if j in JOBS):
            return True
    return False


def choose_for(lane: str):
    """The claim policy of a lane, for queue.claim_next.

    main      the queue in order, leaving research items to the backtest lane while that lane is alive;
              it WAITS when its next item clashes rather than skip ahead (skipping could start a
              multi-hour job in front of a routine that only had to wait a minute)
    backtest  the first research item that does not clash
    fast      the first fast item that does not clash"""
    from . import queue

    def main(queued, running):
        bt_alive = queue.worker_status("backtest")["alive"]
        mine = [x for x in queued if not (bt_alive and research_item(x))]
        if not mine:
            return None
        return None if clashes(mine[0], running) else mine[0]

    def backtest(queued, running):
        return next((x for x in queued if research_item(x) and not clashes(x, running)), None)

    def fast(queued, running):
        return next((x for x in queued if fast_item(x) and not clashes(x, running)), None)
    return {"main": main, "fast": fast, "backtest": backtest}[lane]
