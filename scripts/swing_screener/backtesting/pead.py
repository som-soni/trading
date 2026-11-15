"""Post-earnings announcement drift — the first EVENT-DRIVEN mechanism measured here.

Ball and Brown (1968) found that prices keep moving in the direction of an earnings surprise for
weeks after it is announced, and Bernard and Thomas (1989, 1990) standardised the measurement.
This is the oldest documented anomaly in the list and the only one in this repository whose signal
comes from a FILING rather than from prices.

The Learn guide states the expected answer up front -- "in large US stocks the drift has mostly
disappeared since the 2000s", visible in India on a short sample -- so this is a test of a
prediction, not an open search.

WHERE THE SURPRISE COMES FROM. `financials.load`: each quarter as first reported, the US from the
SEC's XBRL data (2009 on), India from the exchange's filings, its five-year window plus the
point-in-time history before it (`quarterly_results_history`, 2009 on). Each is dated by its RELEASE
(`announcement_dates`: the 8-K with Item 2.02, the NSE broadcast or results board meeting -- the
loader `earnings_gaps` reads), not by the 10-Q/10-K filing, which came 3 or more days later for
about half the US results. Inside the 2013-2021 window that is about 33,000 US results across 1,600
companies and 3,100 Indian ones across 310 at the screener's floors (`in_universe`).

THE UNIVERSE IS POINT IN TIME (`in_universe`): an event counts only if its company was liquid at the
month-end before it, read from stored prices, so the set does not grow when another job fetches
more companies. Mode 2 (`SURPRISE_MODE`) reads no figures at all: every recorded announcement.

YEAR-AGO FIGURES COME FROM A SELF-JOIN, not from the `net_income_prior` column, for two reasons.
India's copy of that column is 100% NULL (0 of 7,155 rows) so it cannot serve both markets. And
where the US does have it, it disagrees with the self-join on 3.8% of pairs (2,671 of 70,596),
because `net_income_prior` is the comparative figure AS RESTATED in the current filing while the
self-join returns what was actually published a year ago. The originally published number is the
point-in-time correct one, and it is the one available in both markets.

THE SEASON RANK IS AN EXPANDING WINDOW, DELIBERATELY. The guide asks for growth "in the top fifth
of all companies reporting that season", but a company's rank against the full season is not
knowable when it reports -- most of the season has not reported yet. Ranking against the whole
season would be lookahead of exactly the kind that makes a backtest unreproducible in life. This
ranks against the filings already IN that season, so the first few filings of a season are ranked
against a small sample and the last are ranked against nearly all of it. That is the information a
trader actually has.
"""
from __future__ import annotations

import argparse
import logging

import pandas as pd

from ..config import MARKETS
from ..marketdata import asof
from ..marketdata import cache, corporate_actions, financials, universe
from ..strategies.base import PortfolioStrategy
from . import metrics, spec

logger = logging.getLogger("backtest")

# ---- the surprise (guide §3)
MIN_YOY_GROWTH = 25.0        # percent, year on year, on net profit
MIN_REVENUE_GROWTH = 10.0    # so the profit rise is not only cost cuts or one-offs
MIN_ACCELERATION = 0.0       # this quarter's YoY growth must exceed last quarter's
SEASON_RANK_TOP = 20.0       # percent: growth must be in the top fifth of the season so far
MIN_QUARTERS = 8             # of results history, for SUE's denominator

# ---- the event date
ANNOUNCE_MAX_DAYS = 120      # a recorded announcement dates a quarter only this many days after it ended, at most

# ---- the price reaction (mode 1)
REACTION_DAYS = 2            # close before the results to the close after
MIN_REACTION = 0.0           # percent, against the index: the market must agree
MAX_REACTION = 20.0          # above this it is an episodic pivot, a different setup

# ---- the mode: which surprise is bought
SURPRISE_MODE = 1            # 1 the guide's growth screen; 2 the price reaction alone; 3 SUE and reaction deciles
REACTION_TOP_PCT = 10.0      # modes 2-3: the reaction is in this top % by the PREVIOUS quarter's cutoff
SUE_TOP_PCT = 20.0           # mode 3: SUE is in this top % by the previous quarter's cutoff
REACTION_ENTRY_LAG = 2       # modes 2-3: buy at the close this many sessions after the reaction day
REACTION_MIN_TURNOVER_CR = 5.0   # mode 2, India: 20-session traded value before the results, in Rs crore
MIN_CUTOFF_EVENTS = 20       # modes 2-3: a quarter's cutoff needs this many events in the quarter before

# ---- the trade
HOLD_SESSIONS = 60           # the drift window Bernard and Thomas measured
MAX_POSITIONS = 15
POSITION_PCT = 8.0           # <= 10% of capital each, per the guide
STOP_ON_REACTION_LOW = 1     # mode 1: a close below the reaction-day low rejects the surprise (0 = no stop)

MODE_NAMES = {1: "growth screen", 2: "price reaction", 3: "SUE and reaction deciles"}


def liquidity_floor(cfg, mode: int | None = None) -> float:
    """The 20-session traded-value floor, in the market's currency: the screener's, except the price-reaction
    mode in India, whose drift lives below it (REACTION_MIN_TURNOVER_CR)."""
    mode = SURPRISE_MODE if mode is None else mode
    if mode == 2 and getattr(cfg, "currency_code", "") == "INR":
        return REACTION_MIN_TURNOVER_CR * 1e7
    return float(cfg.screener.min_dollar_volume)


def announcement_dates(market: str, q: pd.DataFrame) -> pd.Series:
    """The day each quarter's results were released: the earliest recorded announcement (`financials.announcements`,
    the loader earnings_gaps reads -- SEC 8-K Item 2.02, NSE broadcasts and results board meetings) after the
    quarter ended, within ANNOUNCE_MAX_DAYS and not after the filing; else the filing date itself."""
    import bisect
    ann = financials.announcements(market, first_per_quarter=False)
    out = []
    for sym, pe, filed in zip(q["symbol"], q["period_end"], q["filed"]):
        hi = pe + pd.Timedelta(days=ANNOUNCE_MAX_DAYS)
        if filed == filed and filed is not None:
            hi = min(hi, filed)
        ds = ann.get(sym) or []
        k = bisect.bisect_right(ds, pe.date())
        d = ds[k] if k < len(ds) and ds[k] <= hi.date() else None
        out.append(pd.Timestamp(d) if d is not None else filed)
    return pd.to_datetime(pd.Series(out, index=q.index))


def _split_ratio(market: str, sym: pd.Series, d_old: pd.Series, d_new: pd.Series) -> pd.Series:
    """Per row, the product of the splits between `d_old` and `d_new` (spec.split_factor_after): divide a per-share
    figure published on `d_old` by it to put it on the share basis of `d_new`."""
    dates = pd.DatetimeIndex(sorted(set(d_old.dropna()) | set(d_new.dropna())))
    ones = pd.Series(1.0, index=sym.index)
    if not len(dates):
        return ones
    k = spec.split_factor_after(market, dates, sorted(set(sym)))
    if k.empty or not len(k.columns):
        return ones
    ks = k.stack()

    def look(d):
        return pd.Series(ks.reindex(pd.MultiIndex.from_arrays([d, sym])).to_numpy(), index=sym.index).fillna(1.0)
    return (look(d_old) / look(d_new)).fillna(1.0)


def load_filings(market: str) -> pd.DataFrame:
    """One row per stored quarter with a release date, with the year-ago comparatives joined on, SUE computed and
    the results date set (`announced`).

    The quarters are `financials.load`'s: the stored window plus India's point-in-time history before it
    (`quarterly_results_history`, from 2009), each as first reported, inside a backtest stage only what was filed by
    its end. The event is the RELEASE, not the filing: the market reacts to the results announcement, and the 10-Q /
    10-K comes days to weeks later (`announcement_dates`).
    """
    rows = financials.load(market)
    recs = [(sym, r["period_end"], r["filed"], r["net_income"], r["revenue"], r["eps"])
            for sym, rs in rows.items() for r in rs]
    q = pd.DataFrame(recs, columns=["symbol", "period_end", "filed", "net_income", "revenue", "eps"])
    if q.empty:
        return q
    q["period_end"] = pd.to_datetime(q["period_end"]).astype("datetime64[ns]")
    q["filed"] = pd.to_datetime(q["filed"]).astype("datetime64[ns]")
    for c in ("net_income", "revenue", "eps"):
        q[c] = pd.to_numeric(q[c], errors="coerce")
    q["announced"] = announcement_dates(market, q)
    # the year-ago quarter: the company's own quarter that ended 330-400 days earlier (closest to a year), as first
    # published -- not the restated comparative in the new filing
    q["announced"] = q["announced"].astype("datetime64[ns]")
    q["target"] = q["period_end"] - pd.Timedelta(days=365)
    y = q[["symbol", "period_end", "filed", "announced", "net_income", "revenue", "eps"]].rename(columns={
        "period_end": "pe_ya", "filed": "filed_ya", "announced": "ann_ya", "net_income": "ni_year_ago",
        "revenue": "rev_year_ago", "eps": "eps_year_ago"})
    ev = pd.merge_asof(q.sort_values("target"), y.sort_values("pe_ya"), left_on="target", right_on="pe_ya",
                       by="symbol", direction="nearest", tolerance=pd.Timedelta(days=35))
    ev = ev[ev["announced"].notna()]
    if asof.end() is not None:   # a backtest stage's boundary: results after it have not happened
        ev = ev[ev["announced"] <= asof.end()]

    # A growth rate off a loss is not a growth rate: the guide requires the year-ago profit to be
    # positive, and without that filter a swing from -1cr to +1cr reads as -200% and a swing from
    # +1cr to -1cr reads the same, which is worse than useless for ranking.
    ev = ev[(ev["ni_year_ago"] > 0) & ev["net_income"].notna()].copy()
    ev["yoy"] = (ev["net_income"] / ev["ni_year_ago"] - 1) * 100
    ev["rev_growth"] = ((ev["revenue"] / ev["rev_year_ago"] - 1) * 100).where(
        ev["rev_year_ago"] > 0)
    ev = ev.sort_values(["symbol", "period_end"])
    ev["accel"] = ev.groupby("symbol")["yoy"].diff()
    ev["quarters"] = ev.groupby("symbol").cumcount() + 1

    # SUE: the EPS change divided by its own standard deviation over the trailing 8 quarters --
    # Bernard and Thomas's measure, on split-adjusted EPS: the year-ago EPS is put on the current
    # quarter's share basis (the splits between the two publications), so a split is not a surprise.
    # Shifted so the current quarter is not inside its own denominator.
    pub = ev["filed"].fillna(ev["announced"])
    pub_ya = ev["filed_ya"].fillna(ev["ann_ya"]).fillna(ev["pe_ya"] + pd.Timedelta(days=financials.FILING_LAG_DAYS))
    ev["eps_year_ago"] = ev["eps_year_ago"] / _split_ratio(market, ev["symbol"], pub_ya, pub)
    ev["eps_chg"] = ev["eps"] - ev["eps_year_ago"]
    sd = (ev.groupby("symbol")["eps_chg"]
            .transform(lambda s: s.shift().rolling(MIN_QUARTERS, min_periods=4).std()))
    ev["sue"] = ev["eps_chg"] / sd.replace(0, pd.NA)
    ev["sue"] = pd.to_numeric(ev["sue"], errors="coerce")
    keep = ["symbol", "period_end", "filed", "announced", "net_income", "ni_year_ago", "revenue", "rev_year_ago",
            "eps", "eps_year_ago", "yoy", "rev_growth", "accel", "quarters", "eps_chg", "sue"]
    return ev[keep].sort_values(["announced", "symbol"]).reset_index(drop=True)


_LIQUID_MONTHS: dict = {}


def in_universe(market: str, ev: pd.DataFrame, floor: float) -> pd.Series:
    """Point in time: an event counts only if its company was liquid (20-session traded value >= `floor`) at the
    month-end before its results (`universe.month_end_turnover`, the measure the financials backfill fetches by).
    So the set ranked and traded is fixed by prices up to each date, not by which companies some job fetched
    later -- a re-run reproduces."""
    if ev.empty:
        return pd.Series(dtype=bool)
    since = (ev["announced"].min() - pd.DateOffset(months=1)).strftime("%Y-%m-01")
    syms = tuple(sorted(ev["symbol"].unique()))
    ck = (market, float(floor), since, asof.end_date(), syms)
    if ck not in _LIQUID_MONTHS:   # one query per process and boundary: the chart layer asks per symbol
        liq = universe.month_end_turnover(market, floor, since=since, symbols=syms)
        _LIQUID_MONTHS.clear()
        _LIQUID_MONTHS[ck] = set(zip(liq["symbol"], liq["month"]))
    keys = _LIQUID_MONTHS[ck]
    prev = ev["announced"].dt.to_period("M") - 1
    return pd.Series([(s, m) in keys for s, m in zip(ev["symbol"], prev)], index=ev.index)


def load_events(market: str, mode: int | None = None) -> pd.DataFrame:
    """The events the mode trades, one row each, keyed by `announced` (the results release).

    Modes 1 and 3: the stored quarters (`load_filings`) of companies in the point-in-time universe
    (`in_universe` at the screener's floor); mode 1 adds the season rank. Mode 2: every recorded results
    announcement (`financials.announcements`, earliest record per quarter) -- it needs no figures, so every
    listed company with an announcement and prices is in it.
    """
    mode = SURPRISE_MODE if mode is None else mode
    cfg = MARKETS[market]
    if mode == 2:
        ann = financials.announcements(market)
        ev = pd.DataFrame([(s, pd.Timestamp(d)) for s, ds in ann.items() for d in ds], columns=["symbol", "announced"])
        if asof.end() is not None:
            ev = ev[ev["announced"] <= asof.end()]
        for c in ("period_end", "filed"):
            ev[c] = pd.NaT
        for c in ("yoy", "sue", "rev_growth", "accel", "season_pct"):
            ev[c] = float("nan")
        return ev.sort_values(["announced", "symbol"]).reset_index(drop=True)
    ev = load_filings(market)
    if ev.empty:
        return ev
    ev = ev[in_universe(market, ev, liquidity_floor(cfg, mode))].copy()
    # Season rank, expanding WITHIN the season (see the module docstring: ranking against the full
    # season is lookahead). The season is the period_end, so all filings for the same quarter are
    # ranked against each other in the order they were released.
    ev = ev.sort_values(["period_end", "announced", "symbol"])
    ev["season_pct"] = (ev.groupby("period_end")["yoy"]
                          .transform(lambda s: s.expanding().rank(pct=True) * 100))
    return ev.sort_values(["announced", "symbol"]).reset_index(drop=True)


def load_event_prices(market: str, symbols) -> dict:
    """Full OHLCV per symbol, for the symbols that actually have events.

    Not `baseline.load_prices`: that returns close/turnover/SMA200 frames and this strategy needs
    the reaction day's LOW for its stop and the volume for the reaction day.

    `tr_close` is the close back-adjusted for credited special dividends and demergers: the reaction
    is measured on it, so an ex-date inside the window is not read as the market's verdict.
    `turnover20` is the liquidity floor's 20-day traded value (corporate_actions.traded_value), so a
    payout's pre-ex sessions are not valued at the pre-ex price.
    """
    out = {}
    symbols = list(symbols)
    cr = corporate_actions.credits(market, symbols)
    by = {s: g for s, g in cr.groupby("symbol")} if len(cr) else {}
    for s in symbols:
        d = cache.load_cached(market, s)
        if d is None or len(d) < 60:
            continue
        out[s] = d.assign(tr_close=corporate_actions.back_adjust_ohlc(d[["close"]], by.get(s))["close"],
                          # the liquidity floor's 20-day traded value, every session on today's price basis
                          turnover20=corporate_actions.traded_value(d["close"], d["volume"], by.get(s)))
    return out


def filter_checks(r, min_yoy: float | None = None, season_top: float | None = None) -> list[tuple]:
    """The filing's results filters (mode 1), each (name, its value, the limit, passed) -- a filing qualifies only
    when every one passes. The chart's Trade setups layer lists them as its gates."""
    min_yoy = MIN_YOY_GROWTH if min_yoy is None else min_yoy
    season_top = SEASON_RANK_TOP if season_top is None else season_top
    return [("Profit growth (YoY)", r.yoy, f"at least {min_yoy:g}%", r.yoy >= min_yoy),
            ("Season rank", r.season_pct, f"top {season_top:g}% of the season so far", (r.season_pct or 0) >= 100 - season_top),
            ("Acceleration", r.accel, f"growth above last quarter's (+{MIN_ACCELERATION:g} points)", (r.accel or -1) > MIN_ACCELERATION),
            ("Revenue growth (YoY)", r.rev_growth, f"at least {MIN_REVENUE_GROWTH:g}%", (r.rev_growth or -1) >= MIN_REVENUE_GROWTH)]


def _traded_ok(df, d_entry, sym, split_k, floor_price) -> bool:
    entry_px = float(df.loc[d_entry, "close"])
    traded_px = entry_px * (float(split_k.at[d_entry, sym]) if split_k is not None and sym in split_k.columns else 1.0)
    return entry_px == entry_px and traded_px >= floor_price


def qualify(r, df: pd.DataFrame | None, bench: pd.Series | None, start_ts, pos_of, split_k, floor_price: float,
            liq_floor: float, min_yoy: float | None = None, season_top: float | None = None) -> tuple:
    """Mode 1: one filing through the rules: (its candidate, "", what was seen) or (None, the `dropped` key that
    refused it -- "" for an entry before the start -- , what was seen). `seen` carries the reaction window's
    dates and figures as far as they were reached, for the chart's Trade setups layer."""
    seen: dict = {}
    if not all(ok for *_x, ok in filter_checks(r, min_yoy, season_top)):
        return None, "filters", seen
    if df is None:
        return None, "no_bar", seen
    # the reaction window: the close BEFORE the results to the close REACTION_DAYS after
    idx = df.index
    after = idx[idx >= r.announced]
    before = idx[idx < r.announced]
    if len(after) < REACTION_DAYS + 1 or len(before) < 1:
        return None, "no_bar", seen
    d_prev, d_react = before[-1], after[min(REACTION_DAYS - 1, len(after) - 1)]
    seen.update(d_prev=d_prev, d_react=d_react)
    tc = df["tr_close"] if "tr_close" in df else df["close"]   # ratio only: no future action leaks
    p0, p1 = float(tc.loc[d_prev]), float(tc.loc[d_react])
    if p0 <= 0 or p1 != p1:
        return None, "no_bar", seen
    stock_ret = (p1 / p0 - 1) * 100
    if bench is not None:
        b = bench.reindex(idx).ffill()
        bret = (float(b.loc[d_react]) / float(b.loc[d_prev]) - 1) * 100
    else:
        bret = 0.0
    reaction = stock_ret - bret
    seen.update(reaction=reaction, stock_ret=stock_ret)
    if not (MIN_REACTION < reaction <= MAX_REACTION):
        return None, "reaction", seen
    # entry is the session AFTER the reaction window closes
    later = idx[idx > d_react]
    if not len(later):
        return None, "no_bar", seen
    d_entry = later[0]
    seen.update(d_entry=d_entry)
    if d_entry < start_ts or d_entry not in pos_of:
        return None, "", seen
    if not _traded_ok(df, d_entry, r.symbol, split_k, floor_price):
        return None, "liquidity", seen
    turnover = float(df["turnover20"].loc[d_entry])
    if turnover != turnover or turnover < liq_floor:
        return None, "liquidity", seen
    return {"symbol": r.symbol, "yoy": r.yoy, "sue": r.sue, "reaction": reaction,
            "price": float(df.loc[d_entry, "close"]), "stop": float(df.loc[d_react, "low"]),
            "filed": r.announced, "period_end": r.period_end, "entry_date": d_entry}, "", seen


def reaction_context(df: pd.DataFrame | None, bench: pd.Series | None) -> dict | None:
    """One company's series for `measure_reaction`, computed once rather than per event."""
    if df is None:
        return None
    idx = df.index
    tc = (df["tr_close"] if "tr_close" in df else df["close"]).astype(float).to_numpy()
    b = bench.reindex(idx).ffill().to_numpy(dtype=float) if bench is not None else None
    tv = (df["turnover20"] if "turnover20" in df else df["close"].mul(df["volume"]).rolling(20).mean()).to_numpy(dtype=float)
    return {"idx": idx, "vol": df["volume"].to_numpy(dtype=float), "tc": tc, "b": b, "tv": tv}


def measure_reaction(announced, ctx: dict | None) -> dict | None:
    """Modes 2-3: the results-day reaction, as the review's event study measured it. The announcement session is
    the first on or after the release date; the reaction day is the higher-volume of it and the next (a release
    after the close moves the next session); the reaction is the stock's total return minus the index's from the
    close before the announcement session to the reaction day's close; the buy is REACTION_ENTRY_LAG sessions
    after the reaction day; the turnover is the 20-session average traded value at the close before the
    announcement session. None when the bars are not there."""
    if ctx is None:
        return None
    idx, vol, tc, b = ctx["idx"], ctx["vol"], ctx["tc"], ctx["b"]
    i = int(idx.searchsorted(announced))
    if i < 1 or i + 1 >= len(idx):
        return None
    k = i if vol[i] >= vol[i + 1] else i + 1
    e = k + REACTION_ENTRY_LAG
    if e >= len(idx):
        return None
    p0, p1 = tc[i - 1], tc[k]
    if not p0 > 0 or p1 != p1:
        return None
    bret = 0.0
    if b is not None:
        b0, b1 = b[i - 1], b[k]
        bret = (b1 / b0 - 1) * 100 if b0 == b0 and b1 == b1 and b0 > 0 else float("nan")
    return {"d_ann": idx[i], "d_prev": idx[i - 1], "d_react": idx[k], "d_entry": idx[e],
            "stock_ret": (p1 / p0 - 1) * 100, "reaction": (p1 / p0 - 1) * 100 - bret,
            "turnover": float(ctx["tv"][i - 1])}


def prior_quarter_cutoffs(dates: pd.Series, values: pd.Series, top_pct: float) -> pd.Series:
    """Per event, the (100 - top_pct)th percentile of `values` over the events of the PREVIOUS calendar quarter
    (by `dates`) -- known before any event of this quarter happens. NaN when that quarter had fewer than
    MIN_CUTOFF_EVENTS events."""
    q = dates.dt.to_period("Q")
    g = values.groupby(q)
    cut = g.quantile(1 - top_pct / 100).where(g.count() >= MIN_CUTOFF_EVENTS)
    return (q - 1).map(cut).astype(float)


def run(market: str, start: str, hold_sessions: int | None = None,
        max_positions: int | None = None, position_pct: float | None = None,
        min_yoy: float | None = None, season_top: float | None = None,
        cost_bps: float = 10.0, use_stop: bool | None = None,
        preloaded: tuple | None = None, trace: list | None = None):
    """Walk the results calendar, buy the confirmed surprises, hold for the drift window.

    `trace`, when given, receives (event row, candidate or None, refusing key, what was seen) for every
    event -- the chart's Trade setups layer reads why each was or was not bought. Defaults are read from the
    module constants at call time, so a `--const` override reaches them."""
    mode = int(SURPRISE_MODE)
    hold_sessions = HOLD_SESSIONS if hold_sessions is None else hold_sessions
    max_positions = MAX_POSITIONS if max_positions is None else max_positions
    position_pct = POSITION_PCT if position_pct is None else position_pct
    min_yoy = MIN_YOY_GROWTH if min_yoy is None else min_yoy
    season_top = SEASON_RANK_TOP if season_top is None else season_top
    # the literature's drift (modes 2-3) has no stop and no early exit: the clock is the exit
    use_stop = (bool(STOP_ON_REACTION_LOW) if use_stop is None else use_stop) and mode == 1
    cfg = MARKETS[market]
    start_ts = pd.Timestamp(start)

    if preloaded is not None:
        ev, prices, bench = preloaded
    else:
        ev = load_events(market)
        prices = load_event_prices(market, sorted(ev["symbol"].unique()))
        braw = cache.load_cached(market, cfg.benchmark_ticker)
        bench = braw["close"].astype(float) if braw is not None else None
    if ev.empty or not prices:
        raise SystemExit(f"{market}: no results events with prices")

    floor_price = cfg.screener.min_price
    liq_floor = liquidity_floor(cfg, mode)

    # The trading calendar is the benchmark's, so a symbol that did not trade on a session cannot
    # silently shift the holding clock: HOLD_SESSIONS counts market sessions, not the symbol's own.
    cal = bench.index if bench is not None else next(iter(prices.values())).index
    cal = pd.DatetimeIndex([d for d in cal if d >= start_ts - pd.Timedelta(days=400)])
    pos_of = {d: i for i, d in enumerate(cal)}
    # The price floor reads the price traded on the buy day. The stored close is back-adjusted for
    # every later split, so a $10 floor on it dropped the later multi-baggers' early filings.
    # Every entry date is a calendar session (pos_of), so the factor frame is indexed on `cal`.
    split_k = spec.split_factor_after(market, cal, list(prices)) if floor_price and len(cal) else None

    # qualify each event ONCE, up front: the decision uses only that event's own row, the previous
    # quarter's cutoffs and prices up to the entry bar, so there is nothing to recompute per day.
    cand: dict = {}
    dropped = {"filters": 0, "no_bar": 0, "reaction": 0, "liquidity": 0}
    if mode == 1:
        for r in ev.itertuples():
            c, why, seen = qualify(r, prices.get(r.symbol), bench, start_ts, pos_of, split_k, floor_price, liq_floor,
                                   min_yoy, season_top)
            if trace is not None:
                trace.append((r, c, why, seen))
            if c is None:
                if why:
                    dropped[why] += 1
                continue
            cand.setdefault(c["entry_date"], []).append(c)
    else:
        ctxs = {sym: reaction_context(prices.get(sym), bench) for sym in ev["symbol"].unique()}
        seen_of = {r.Index: measure_reaction(r.announced, ctxs.get(r.symbol)) for r in ev.itertuples()}
        ok = [k for k, s in seen_of.items() if s is not None and s["reaction"] == s["reaction"]
              and s["turnover"] == s["turnover"] and s["turnover"] >= liq_floor]
        pool = ev.loc[ok].copy()
        pool["d_ann"] = [seen_of[k]["d_ann"] for k in ok]
        pool["reaction"] = [seen_of[k]["reaction"] for k in ok]
        pool["react_cut"] = prior_quarter_cutoffs(pool["d_ann"], pool["reaction"], REACTION_TOP_PCT)
        if mode == 3:
            has = pool["sue"].notna()
            pool["sue_cut"] = float("nan")
            pool.loc[has, "sue_cut"] = prior_quarter_cutoffs(pool.loc[has, "d_ann"], pool.loc[has, "sue"], SUE_TOP_PCT)
        for r in ev.itertuples():
            s = seen_of.get(r.Index)
            c, why = None, ""
            if s is None or s["reaction"] != s["reaction"]:
                why = "no_bar"
            elif r.Index not in pool.index:
                why = "liquidity"
            else:
                p = pool.loc[r.Index]
                if mode == 3 and not (p["sue"] == p["sue"] and p["sue_cut"] == p["sue_cut"] and p["sue"] >= p["sue_cut"]):
                    why = "filters"
                elif not (p["react_cut"] == p["react_cut"] and s["reaction"] >= p["react_cut"]):
                    why = "reaction"
                elif s["d_entry"] < start_ts or s["d_entry"] not in pos_of:
                    why = ""
                elif not _traded_ok(prices[r.symbol], s["d_entry"], r.symbol, split_k, floor_price):
                    why = "liquidity"
                else:
                    df = prices[r.symbol]
                    c = {"symbol": r.symbol, "yoy": r.yoy, "sue": r.sue, "reaction": s["reaction"],
                         "price": float(df.loc[s["d_entry"], "close"]), "stop": None,
                         "filed": r.announced, "period_end": r.period_end, "entry_date": s["d_entry"]}
            if trace is not None:
                trace.append((r, c, why, s or {}))
            if c is None:
                if why:
                    dropped[why] += 1
                continue
            cand.setdefault(c["entry_date"], []).append(c)

    # the next results date per symbol, so a position can be closed when it reports again (mode 1)
    next_filing = {}
    for sym, g in ev.groupby("symbol"):
        next_filing[sym] = sorted(g["announced"].tolist())

    cash = float(cfg.account_size)
    open_pos: dict[str, dict] = {}
    trades, equity, cash_log, held_log, costs_total = [], [], [], [], 0.0

    def px_on(sym, d):
        df = prices[sym]
        hit = df.index[df.index <= d]
        return float(df.loc[hit[-1], "close"]) if len(hit) else float("nan")

    # a special dividend or demerger while held: the cash, and the stop moved down by it
    credits = corporate_actions.Credits.for_market(market, list(prices))
    credit_after = start_ts - pd.Timedelta(days=1)

    def rank_key(c):
        sue = c["sue"] if c["sue"] == c["sue"] and c["sue"] is not None else 0
        if mode == 2:
            return (-c["reaction"],)
        if mode == 3:
            return (-sue, -c["reaction"])
        return (-sue, -c["yoy"])

    for i, d in enumerate(cal):
        if d < start_ts:
            continue
        for sym, c in credits.on(d, credit_after, open_pos).items():
            p = open_pos[sym]
            cash += p["units"] * c
            p["credited"] += p["units"] * c
            if p["stop"] is not None:
                p["stop"] -= c
        credit_after = d
        # ---- exits first, so freed capital can be redeployed the same session
        for sym in list(open_pos):
            p = open_pos[sym]
            price = px_on(sym, d)
            if price != price:
                continue
            nxt = [f for f in next_filing.get(sym, []) if f > p["filed"]] if mode == 1 else []
            reason = None
            if use_stop and p["stop"] is not None and price < p["stop"]:
                reason = "STOP"
            elif nxt and d >= nxt[0]:
                reason = "NEXT_RESULTS"
            elif i - p["i"] >= hold_sessions:
                reason = "DRIFT_WINDOW"
            if reason is None:
                continue
            gross = p["units"] * price
            fee = gross * cost_bps / 10_000
            cash += gross - fee
            costs_total += fee
            trades.append({
                "symbol": sym, "entry_date": p["date"], "entry_price": round(p["price"], 4),
                "exit_date": d, "exit_price": round(price, 4), "shares": round(p["units"], 4),
                "exit_reason": reason, "pnl": round(gross - fee - p["cost"] + p["credited"], 2),
                "credited": round(p["credited"], 2),
                "notional": round(p["cost"], 2), "costs": round(fee + p["fee"], 2),
                "holding_days": (d - p["date"]).days,
                "r_multiple": round((gross - fee + p["credited"]) / p["cost"] - 1, 4),
                "announced": p["filed"], "reaction": round(p["reaction"], 3),
            })
            del open_pos[sym]

        # ---- entries: strongest surprise first when several land the same session
        todays = [c for c in cand.get(d, []) if c["symbol"] not in open_pos]
        todays.sort(key=rank_key)
        for c in todays:
            if len(open_pos) >= max_positions:
                break
            if c["symbol"] in open_pos:
                # two events of one company resolving to the same entry session (an amended
                # or duplicate filing): the stronger, sorted first, is bought; the other would
                # overwrite that live position, spending its cash twice and dropping it from equity
                continue
            book = cash + sum(p["units"] * px_on(s, d) for s, p in open_pos.items())
            spend = min(book * position_pct / 100, cash)
            if spend <= 0:
                break
            fee = spend * cost_bps / 10_000
            cash -= spend
            costs_total += fee
            open_pos[c["symbol"]] = {
                "units": (spend - fee) / c["price"], "price": c["price"], "date": d,
                "cost": spend - fee, "fee": fee, "i": i, "stop": c["stop"], "filed": c["filed"], "credited": 0.0,
                "reaction": c["reaction"]}

        val = cash + sum(p["units"] * px_on(s, d) for s, p in open_pos.items())
        equity.append((d, val))
        cash_log.append((d, cash))
        held_log.append((d, len(open_pos)))

    eq = pd.Series(dict(equity)).sort_index()
    return (pd.DataFrame(trades), eq, pd.Series(dict(held_log)).sort_index(),
            pd.Series(dict(cash_log)).sort_index(), costs_total, dropped, len(cand))


PEAD_DOC = {
    "key": "pead",
    "name": "Post-earnings drift",
    "description": "Buy a confirmed earnings surprise -- profit growth of at least {MIN_YOY_GROWTH}% year on year, "
                   "accelerating, revenue up at least {MIN_REVENUE_GROWTH}%, in the top {SEASON_RANK_TOP}% of the season so far, and the market "
                   "agreeing over the first {REACTION_DAYS} sessions -- and hold for {HOLD_SESSIONS} sessions.",
    "status": (
        "FAILS ITS PASS CRITERIA IN BOTH MARKETS (v1.6, OPTIMISE stage, 2013-2021, IN-SAMPLE, runs of 2026-11-15; "
        "criteria fixed before the runs). India's price reaction (mode 2) is a real but floor-sensitive lead: at a "
        "Rs 5 crore floor it made 21.89% a year against the Smallcap 250's ~16.4% total return (price 15.44% plus a "
        "flat 0.83% dividend accrual, an approximation) and the Nifty 500's ~14.5%, 479 trades, 64.3% won, 94% "
        "invested, max drawdown -54.8% against the index's -60.8%, 7 of 9 years up, 2021 39% of P&L. Per trade it "
        "beat the Nifty 500 by +2.99% over the hold (t 3.2, 479 trades), in line with the review's event study "
        "(+2.27% over 60 sessions, t 3.6, 1,216 events). The robustness half of the gate fails: at a Rs 10 crore "
        "floor it made 15.72% (-0.7 against the Smallcap 250 total return, +0.28 against its price index), 446 "
        "trades. The edge lives in the least liquid names, where costs bite hardest, and the drawdown is the "
        "index's own. "
        "US SUE + reaction (mode 3) fails: 9.47% a year against 11.40% for SPY held at the book's own exposure (86% "
        "invested) and 14.01% for SPY, 432 trades, 63.2% won, max drawdown -46.9% against -34.1%, no year above "
        "33% of P&L. Retiring the US version is the owner's call. "
        "The default growth screen, with the v1.6 data fixes, is worse than before: US 1.98% a year against SPY's "
        "14.01% (7.40% at its 76% exposure), 953 trades, 28.4% won, max drawdown -32.7% -- v1.5's 6.55% was "
        "flattered by dating events by the later filing; India 0.51% against the Smallcap 250's 15.44%, 173 "
        "trades, 26.0% won, 13% invested, because its Rs 50 crore floor leaves too few companies. "
        "The Learn guide predicted the US half before any code existed: the drift has mostly gone from large US "
        "stocks since the 2000s."
    ),
    # Every rule below was checked against run() and load_events() above. There is no spec with row
    # ids; the Learn guide research/learn-strat-pead.md §3 is the specification, cited by section.
    "thesis": "Ball and Brown (1968) found prices keep drifting in the direction of an earnings surprise for "
              "weeks afterwards, and Bernard and Thomas (1989) argued investors under-react because they do "
              "not fully grasp that quarterly earnings are serially correlated -- a good quarter predicts the "
              "next one more strongly than people price in. The trade is the oldest documented anomaly in "
              "the Learn module and the only one here whose signal comes from a filing rather than a price.",
    "how_it_works": (
        "The idea. Buy a company whose quarterly profit jumped, ranked near the top of its season, after "
        "the market has confirmed the news, and hold it through the weeks of drift that follow. The rules "
        "are the testable form of the Learn guide on post-earnings drift (its section 3). There is no spec "
        "with row ids, so each rule names the guide rule it implements and says where it differs.",
        "Step 1 — the surprise (Entry: the results). Each quarter's results are tested once, on the day they "
        "were released, on four numbers from the company's own results: profit growth, its season rank, its "
        "acceleration and revenue growth.",
        "Step 2 — the market agrees (Entry: the reaction). Over the first sessions after the release the "
        "stock must beat the index, but not by too much.",
        "Step 3 — the buy (Entry: the buy). At the close of the next session, a fixed {POSITION_PCT}% of the "
        "account, strongest surprise first.",
        "Step 4 — the sale (Exit). A close below the reaction low, the next results, or {HOLD_SESSIONS} "
        "market sessions, whichever comes first. Every sale is at a close.",
        "Data. The event is the RESULTS RELEASE, not the quarter end or the later filing: the market reacts "
        "to the announcement. In the US it is the 8-K with Item 2.02 a company files the day it releases "
        "results; in India, the exchange broadcast or the results board meeting, whichever came first. Where "
        "no announcement is recorded within {ANNOUNCE_MAX_DAYS} days of the quarter end, the date the "
        "figures were first filed is used. The figures are each quarter as first reported: in India the "
        "exchange's filings back to 2009, in the US the SEC's XBRL data back to 2009. Analysts' forecasts "
        "are not used.",
        "The universe, point in time. A company's results count only if its 20-day average traded value was "
        "above the liquidity floor at the month-end before them. So the set ranked and traded on a date is "
        "fixed by prices up to that date, not by which companies have data today, and a re-run gives the "
        "same result. The run directory keeps the event list it used (events.csv).",
        "Modes (SURPRISE_MODE, now {SURPRISE_MODE}). Mode 1 is the growth screen described here, the "
        "guide's rules. Mode 2 buys the price reaction alone: every company with recorded announcements, the "
        "top {REACTION_TOP_PCT}% of results-day reactions, a ₹{REACTION_MIN_TURNOVER_CR} crore floor in "
        "India. Mode 3 is Bernard and Thomas's measure: standardised surprise (SUE) in the top "
        "{SUE_TOP_PCT}% and the reaction in the top {REACTION_TOP_PCT}%. Modes 2 and 3 have no stop and no "
        "early exit. Their rules are listed after mode 1's below. They are experiments, run with "
        "`--const SURPRISE_MODE=2` (or 3).",
        "Running it. `python3 -m swing_screener.backtesting.pead --market us --start 2013-01-01`. The "
        "options are the holding period, the number of positions, the position size, the minimum growth, "
        "the season rank, the cost per side and `--const NAME=VALUE` for any constant (the mode).",
    ),
    "entry_rules": (
        "The results: profit growth. Net profit is at least {MIN_YOY_GROWTH}% above the same quarter a year "
        "earlier.\n\n"
        "- **Year-ago quarter:** the company's stored quarter that ended 330 to 400 days before this one, "
        "as it was first published then (not the restated figure in the new filing).\n"
        "- **Year-ago profit:** must be above zero. A filing with a year-ago loss, or no year-ago quarter, "
        "is never tested.\n\n"
        "**Guide (§3 Setup):** the same.",
        "The results: season rank. The growth is in the top {SEASON_RANK_TOP}% of its season so far.\n\n"
        "- **Season:** the results of every company in the universe for a quarter ending on the same date.\n"
        "- **So far:** the results are ranked by growth among that season's results released on or before "
        "their own date (same-day releases in alphabetical order). The first filer of a season ranks top by "
        "definition, so it always passes.\n\n"
        "**Guide (§3 Setup):** top fifth of all companies reporting that season. Differs: the full season "
        "is not known on the day a company reports, so ranking against it would be lookahead.",
        "The results: acceleration. This quarter's growth is more than {MIN_ACCELERATION} points above the "
        "growth of the company's previous stored quarter (the previous one that had a year-ago quarter "
        "with a profit). A company with no such previous quarter fails.\n\n"
        "**Guide (§3 Setup):** acceleration above zero — the same.",
        "The results: revenue growth. Revenue is at least {MIN_REVENUE_GROWTH}% above the same quarter a year "
        "earlier, so the profit rise is not only cost cuts or one-off gains. A filing with no positive "
        "year-ago revenue fails.\n\n"
        "**Guide (§3 Setup):** the same.",
        "The reaction. The stock beats the benchmark index by more than {MIN_REACTION}% and at most "
        "{MAX_REACTION}%.\n\n"
        "- **Span:** from the close of the last session before the release date to the close "
        "{REACTION_DAYS} sessions later, counting the first session on or after the release date as the "
        "first.\n"
        "- **Measure:** the stock's return minus the index's return over the same span, in % points.\n"
        "- **Ceiling:** a bigger jump is an episodic pivot, which the Earnings gaps strategy trades.\n\n"
        "**Guide (§3 Setup and Entry):** the same.",
        "The buy. At the close of the session after the reaction span — the third session counting the "
        "release day. There is no trigger and no limit order: the event has already happened.\n\n"
        "**Guide (§3 Entry):** the close of the second session after the results — the same session.",
        "Tradable on the buy day. The close must be at or above the market's price floor -- read as the price "
        "traded that day, the stored close multiplied back by every later split -- and the 20-day "
        "average traded value (close × volume) at or above its liquidity floor — the screener's floors "
        "($10 and $10 million in the US; no price floor and ₹50 crore in India, as configured in October "
        "2026). Every session of that average is valued on the buy day's price basis: after a credited "
        "special dividend or demerger the shares traded before the ex-date count at the price less the "
        "payout, as a split's would (v1.5).\n\n"
        "**Guide (§3 Universe):** $5 or ₹50 and $5 million or ₹5 crore. Differs: the market's own floors "
        "are used, and they are higher.",
        "Size. Each buy spends {POSITION_PCT}% of the account (cash plus open positions at the day's close), "
        "or the cash left if that is less. Fractional shares are allowed. It is not sized from the stop, so "
        "the amount lost at the stop varies from trade to trade.\n\n"
        "**Guide (§3 Position size):** either risk 0.5% per trade sized from the stop, or equal weights of "
        "at most 10% with no stop. Differs: this mixes the two — equal weights, and a stop as well.",
        "Positions and ties. At most {MAX_POSITIONS} positions, one per company. When more results "
        "qualify on a session than there are free slots, the largest standardised surprise (SUE) is "
        "bought first, then the highest growth; the rest are dropped, not kept for later. Two filings "
        "by one company reaching their buy on the same session (an amended or duplicate filing) buy once, "
        "the first in that order.\n\n"
        "- **SUE:** the change in EPS against the same quarter a year earlier, divided by the standard "
        "deviation of that change over the previous {MIN_QUARTERS} quarters (at least 4 needed; with "
        "fewer it counts as 0). EPS is split-adjusted: the year-ago EPS is divided by the splits between "
        "the two publications. In mode 1 it only ranks; it is not a filter.\n\n"
        "**Guide (§3 Setup):** SUE is one of the three surprise measures. The guide's minimum of "
        "{MIN_QUARTERS} quarters of history is not enforced.",
        "Costs. {cost_bps} basis points of the amount traded, on each side. No slippage is added on top.",
        "Mode 2 — the price reaction (`--const SURPRISE_MODE=2`). No results figures are read. Every recorded "
        "results announcement is an event, and the rules above are replaced by these:\n\n"
        "- **Announcement session:** the first session on or after the release date.\n"
        "- **Reaction day:** the announcement session or the next, whichever traded more shares (a release "
        "after the close moves the next session).\n"
        "- **Reaction:** the stock's total return minus the benchmark index's from the close before the "
        "announcement session to the reaction day's close.\n"
        "- **Floor:** the 20-day average traded value at the close before the announcement session is at "
        "least ₹{REACTION_MIN_TURNOVER_CR} crore in India (the screener's floor elsewhere).\n"
        "- **Cutoff:** the reaction is at or above the {REACTION_TOP_PCT}% cutoff (the top tenth) of the "
        "reactions of the PREVIOUS calendar quarter's events above the floor. That quarter is over before "
        "this one starts, so the cutoff is known. A quarter whose previous quarter had fewer than "
        "{MIN_CUTOFF_EVENTS} events buys nothing.\n"
        "- **Buy:** at the close {REACTION_ENTRY_LAG} sessions after the reaction day, the timing the "
        "event study measured. The price floor still applies.\n"
        "- **Ties:** the largest reaction first.\n\n"
        "**Research:** Chan, Jegadeesh and Lakonishok (1996) and Brandt et al. (2008) find the "
        "announcement return predicts a drift of its own. Not in the guide.",
        "Mode 3 — SUE and reaction deciles (`--const SURPRISE_MODE=3`). The results of mode 1's universe "
        "that have a year-ago quarter with a profit (as mode 1 needs), with none of mode 1's four filters. "
        "A company is bought when both hold:\n\n"
        "- **SUE** is at or above the cutoff of the previous calendar quarter's top {SUE_TOP_PCT}%.\n"
        "- **The reaction** (mode 2's measure and floor) is at or above the previous quarter's top "
        "{REACTION_TOP_PCT}% cutoff.\n\n"
        "It buys at mode 2's timing, the largest SUE first.\n\n"
        "**Research:** Bernard and Thomas (1989, 1990) rank on SUE deciles. The reaction filter is "
        "Chan, Jegadeesh and Lakonishok's second signal.",
    ),
    "exit_rules": (
        "Each session after the buy, the position is checked at the close against these rules, in this "
        "order, and the first that applies sells everything at that close. Exits are settled before the "
        "day's buys, so cash freed by a sale can be spent the same session.",
        "Stop (mode 1, when STOP_ON_REACTION_LOW is 1; it is {STOP_ON_REACTION_LOW}). A close below the low of "
        "the last session of the reaction span (the session before the buy). It is not a standing order: nothing sells during the day, and the sale is at the close, "
        "which can be well below the stop.\n\n"
        "**Guide (§3 Initial stop):** a close below the reaction-day low — the same.",
        "Next results (mode 1). The close of the first session on or after the company's next results "
        "release date. That is the release day itself, not the day before, so the results' own reaction is "
        "held whenever it comes before that close. Only results that have a year-ago quarter with a profit "
        "are in that list, so a next release without one is missed.\n\n"
        "**Guide (§3 Exits):** just before the next results date. Differs: the sale comes on, not "
        "before, the release date (see Caveats).",
        "Drift window. After {HOLD_SESSIONS} sessions, counted in the benchmark's trading sessions rather "
        "than the stock's own, so a halted or thin stock cannot stretch its holding period.\n\n"
        "**Guide (§3 Exits):** the same.\n\n"
        "Modes 2 and 3 use this exit only: no stop and no next-results sale, as the research measured the "
        "drift.",
        "No target, and no rank exit. The thesis is a drift over weeks, so the clock is the exit. The "
        "guide's rank exit — sell if the next quarter's growth falls out of the top two-fifths — is not "
        "implemented. A position open when the backtest ends is valued at its last close.",
    ),
    "caveats": (
        "**The universe is point in time from v1.6, but only as wide as the stored filings.** Before v1.6 "
        "the events were every company the `financials` job had fetched -- today's most liquid names plus "
        "today's Stage-2 stocks -- so the set knew which stocks went on to trend and grew after each run: "
        "the v1.4 US optimise run (915 trades, 6.98%) re-ran as 931 trades and 6.51% on the same code. Now "
        "an event counts only if its company was liquid at the month-end before it, and the filings are "
        "fetched for every stock liquid at some month-end since 2013 (the `financials_backfill` job), so a "
        "re-run reproduces. Stocks delisted before today are still missing (the price store keeps today's "
        "listings), which flatters every figure a little.",
        "**A release can be missing from the record.** About 8% of US results have no 8-K with Item 2.02 "
        "on file; those, and Indian quarters with no broadcast or board meeting recorded, are dated by "
        "the filing, which can come days or weeks after the news. The 8-K carries a date, not a time, so "
        "a release after the close is read on the next session only in modes 2 and 3 (the higher-volume "
        "day).",
        "**The next-results exit does not avoid the results gap.** It sells at the close of the release day, "
        "so whenever the results come out before that close the position holds through their reaction. "
        "The guide's intent is to sell before.",
        "**The 'R' figures in this strategy's reports are returns, not risk multiples.** A trade's R is its "
        "profit divided by the amount invested (0.05 = 5%), because positions are sized as a share of the "
        "account, not from the stop.",
        "**India's growth screen draws from few companies.** At the screener's ₹50 crore floor the point-in-"
        "time universe holds about 310 companies over 2010-2021 (3,146 results in 2013-2021), and the "
        "review's event study found the drift below that floor, not above it -- which is why mode 2 has its "
        "own ₹{REACTION_MIN_TURNOVER_CR} crore floor. Small Indian stocks cost more to trade than the "
        "{cost_bps} basis points assumed: about 27 a side would take roughly half a point off a 60-session "
        "drift.",
        "**Low win rate with positive skew means the confidence interval is wide.** Under 30% of trades "
        "make money in both markets, so the result rests on the few largest drifts. Anything built on this "
        "should be judged on many more events than are available here.",
        "**Restatements are deliberately ignored.** Year-ago figures come from what was published a year "
        "ago, not from the current filing's restated comparative. The two disagree on 3.8% of US pairs "
        "(2,671 of 70,596); the originally published number is the one a trader had, and it is the only one "
        "India stores at all.",
        "**Analyst estimates exist but are not usable here.** The fetch keeps four quarters of consensus and "
        "surprise per company, which is enough for a live view and nowhere near enough for a backtest, so "
        "surprise is measured from the company's own history instead -- as the guide specifies.",
    ),
}


class PeadStrategy(PortfolioStrategy):
    """Post-earnings announcement drift, as the Learn guide states it.

    Registered despite failing, because this is the only EVENT-DRIVEN mechanism measured here and a
    negative result on the oldest documented anomaly in the list is worth keeping visible.
    """

    key = PEAD_DOC["key"]
    doc = PEAD_DOC
    family = "pead"
    version = "1.7"
    changelog = (
        ("1.7", "2026-11-15",
         "Mode 2 only (SURPRISE_MODE=2; modes 1 and 3 are unchanged): every US 8-K with Item 2.02 is an event on its "
         "own date. financials.announcements grouped them by period end, which for an 8-K is only the calendar "
         "quarter before its filing, so an early-quarter update hid the results three weeks later (AbbVie, every "
         "quarter of 2024; 11,878 US groups spanned more than 14 days). India is unchanged."),
        ("1.6", "2026-11-14",
         "Data paths fixed (2026-11-14 review, P1, B2, B3 and the universe); the rules are unchanged in mode 1. "
         "(1) Results are dated by the RELEASE -- the earliest recorded announcement after the quarter end "
         "(SEC 8-K Item 2.02, NSE broadcast or results board meeting, through financials.announcements, the loader "
         "earnings_gaps reads), within ANNOUNCE_MAX_DAYS and not after the filing -- not by the 10-Q/10-K, which "
         "came 3 or more days later for 48% of US results. (2) The quarters are financials.load's, so India reads its "
         "2009-2021 history: 3,146 Indian results in 2013-2021 where v1.4 had 32 and no trade. (3) SUE is on "
         "split-adjusted EPS. (4) The universe is point in time: a result counts only if its company was liquid "
         "at the month-end before it (universe.month_end_turnover, the measure the financials backfill fetches by), "
         "so a re-run reproduces; v1.4's re-run moved from 915 trades to 931 on the same code. "
         "(5) Two experiments behind SURPRISE_MODE, rules fixed before any run: 2 = the price reaction alone "
         "(top REACTION_TOP_PCT% by the previous quarter's cutoff, a REACTION_MIN_TURNOVER_CR crore floor in India, "
         "no stop, HOLD_SESSIONS); 3 = SUE and reaction deciles with prior-quarter cutoffs, no stop. "
         "STOP_ON_REACTION_LOW is now 1/0, so it is in the fingerprint and can be overridden. India is judged against "
         "the Smallcap 250 (benchmark_key). Pass criteria for modes 2 and 3, written before the runs: excess over the "
         "Smallcap 250 (India) total return above 0 with at least 300 trades, the same at a 10 crore floor; US mode "
         "3, excess over SPY held at the book's own exposure above 0, at least 250 trades, no year above 40% of P&L."),
        ("1.5", "2026-11-14",
         "The turnover floor values every session of its 20-day window on today's price basis (corporate_actions.traded_value), the fix from the momentum_baseline India review of 2026-11-14. A credited special dividend or demerger drops the price but not the shares traded before it, so the plain mean of close x volume kept the pre-ex sessions at the pre-ex price for 20 sessions. AURUM (ex-Majesco) went ex a 98.8% special dividend on 2020-12-23 (Rs 717 -> 8.88); on 2020-12-31 the floor read Rs 121 cr a day while the stock traded Rs 8 lakh, in a locked upper circuit. Pre-ex sessions are now scaled by the same ratio as the price, and only for actions up to the session (point in time), as a split already is: AURUM reads Rs 1.4 cr there. A session whose window spans no credited ex-date is unchanged to the bit. Effect, in memory on the US optimise stage: one buy is no longer taken, BBW on 2021-12-13 ($10.45M stale against $9.90M corrected, after a special dividend), 6.51% -> 6.55% CAGR, drawdown -23.2% unchanged, 931 -> 930 trades. Bumped by hand: no numeric constant moved."),
        ("1.4", "2026-10-31",
         "One position per company, as the entry rules already said. Two filings by one company "
         "that reached their buy on the same session (an amended or duplicate filing; 129 such "
         "same-day pairs are stored) both bought: the second overwrote the first, so its cash "
         "was spent twice and the first position vanished from equity. The second is now "
         "skipped. Stored runs are stale: equity, trades and every figure can move."),
        ("1.3", "2026-10-29",
         "The price floor on the buy day reads the price traded then. The US $10 price floor reads the price the stock traded at that day: the stored close multiplied back by every later split Yahoo records (backtesting/spec.traded_close, the RS rating's fix in 1d16854). Stored closes are back-adjusted for every later split, so the floor had dropped the later multi-baggers from their early years -- NFLX's October 2009 close is stored as $0.72 against the ~$50 it traded at, NVDA read under $10 until mid-2020. On 2016-06-30 the US floor admits 2,092 stocks instead of 2,382: 47 that later split (NVDA, CMG, ANET, CPRT ...) come in, 337 that later reverse-split, and so really traded under $10, go out. India has no price floor and is unchanged."),
        ("1.2", "2026-10-26",
         "The reaction window reads total return: the stock's move over the first sessions after a "
         "filing is measured on closes back-adjusted for credited special dividends and demergers "
         "(corporate_actions.back_adjust), so an ex-date inside the window is not taken for the market's "
         "verdict on the results. Fills, the stop and turnover still read traded prices."),
        ("1.1", "2026-10-25",
         "Backtest mechanics, no rule changed: special dividends and demergers are credited (marketdata/corporate_actions.py). On the ex-date a held position receives the cash, where the stored close only falls by it -- AURUM's 98% special dividend on 2020-12-23 was booked as a -98% loss, about 10% of the India vol-scaled book. Ordinary dividends stay out of strategy and benchmark. Stored prices were also corrected where the source left a split unadjusted before its year-start (MOTILALOFS and GPIL 2024-01-01, PARAS 2025-01-01 and others) or carried a stray bar (marketdata/splits.py correct)."),
        ("1.0", "2026-10-18",
                  "First version. Validated against the guide's worked example before being measured: "
                  "Polycab's June 2023 quarter reads +81.69% year on year against the guide's +81.7%, "
                  "the March quarter +30.56% against +30.6%, and the acceleration +51.13 points against "
                  "+51. Surprise is computed from a self-join to the company's own year-ago filing rather "
                  "than from net_income_prior, which India stores as 100% NULL and which disagrees with "
                  "the self-join on 3.8% of US pairs because it carries restatements."),)
    name = PEAD_DOC["name"]
    description = PEAD_DOC["description"]
    status = PEAD_DOC["status"]
    thesis = PEAD_DOC["thesis"]
    how_it_works = tuple(PEAD_DOC["how_it_works"])
    caveats = tuple(PEAD_DOC["caveats"]) + (corporate_actions.CAVEAT_HELD,)
    entry_rules = tuple(PEAD_DOC["entry_rules"])
    exit_rules = tuple(PEAD_DOC["exit_rules"])

    benchmark_key = {"india": "NIFTYSMALLCAP250"}
    behaviour = "event_driven"
    #: Ranked against the other companies reporting the same season, so cross-sectional -- but the
    #: pool is one season's filings rather than the whole tape on a date.
    selection = "cross_sectional"
    style = "event"
    horizon = "swing"
    runner = "pead"

    hold_sessions = HOLD_SESSIONS
    max_positions = MAX_POSITIONS
    position_pct = POSITION_PCT
    min_yoy = MIN_YOY_GROWTH
    season_top = SEASON_RANK_TOP
    cost_bps = 10.0

    param_docs = (
        ("Holding period", "hold_sessions", "Market sessions held before the time exit."),
        ("Positions", "max_positions", "Concurrent holdings; the guide suggests 10-20."),
        ("Position size", "position_pct", "Percent of the book per holding, at most 10%."),
        ("Minimum growth", "min_yoy", "Year-on-year net profit growth required."),
        ("Season rank", "season_top", "Growth must be in this top percent of the season so far."),
        ("Mode", "SURPRISE_MODE", "1 growth screen (the guide), 2 price reaction alone, 3 SUE and reaction deciles."),
        ("Reaction cutoff", "REACTION_TOP_PCT", "Modes 2-3: the reaction is in this top percent of the previous quarter's."),
        ("India floor, mode 2", "REACTION_MIN_TURNOVER_CR", "Mode 2: 20-day traded value before the results, Rs crore."),
        ("Cost per side", "cost_bps", "Basis points per side."),
    )

    @classmethod
    def setups_live(cls, raw: pd.DataFrame, cfg, symbol: str, years: int | None = 5, anchors=None) -> list[dict]:
        """The chart's Trade setups layer: each of this symbol's filings through `qualify` (inside `run`, which
        traces them), with the trade `run` makes of it on this one symbol (backtesting/portfolio_setups.py).
        The season rank is the market's own, from every filing (`load_events`)."""
        from . import portfolio_setups as pset
        market = pset.market_of(cfg)
        if int(SURPRISE_MODE) != 1:   # the layer draws the growth screen's gates; the other modes are experiments
            return []
        ev = load_events(market)
        ev = ev[(ev["symbol"] == symbol) & (ev["announced"] <= raw.index[-1])] if len(ev) else ev
        braw = cache.load_cached(market, cfg.benchmark_ticker)
        prices = load_event_prices(market, [symbol])
        if ev.empty or symbol not in prices or braw is None:
            return []
        df = prices[symbol].loc[: raw.index[-1]]
        start = pset.since(df, years)
        trace: list = []
        trades = run(market, str(start.date()), preloaded=(ev, {symbol: df}, braw["close"].astype(float)), trace=trace)[0]
        by_entry = {pd.Timestamp(t["entry_date"]): t for t in trades.to_dict("records")}
        pos = lambda d: int(df.index.searchsorted(d))
        traded = pset.anchor_bars(df, anchors)   # a run buys at the close of the session after the reaction
        steps = ("filters", "no_bar", "reaction", "liquidity")
        words = {"filters": "the results missed a filter", "no_bar": "no prices around the results",
                 "reaction": f"reaction not {MIN_REACTION:g}% to {MAX_REACTION:g}% over the index",
                 "liquidity": "too little traded, or under the price floor"}
        pct = lambda v: "—" if v is None or v != v else f"{v:+.1f}%"
        out = []
        for r, c, why, seen in trace:
            if c is None and not why:
                continue   # an entry before the window
            at = seen.get("d_entry") or seen.get("d_react") or r.announced
            k = min(pos(at), len(df) - 1)
            if df.index[k] < start:
                continue
            st = pset.ordered([(x,) for x in steps], why)
            checks = [("results", n, pct(v) if "rank" not in n else (f"top {100 - v:.0f}%" if v == v and v is not None else "—"), lim, ok)
                      for n, v, lim, ok in filter_checks(r)]
            if why == "filters":
                first = next(n for n, _v, _l, ok in filter_checks(r) if not ok)
                reason = f"{first.split(' (')[0].lower()} below its limit"
            else:
                reason = words.get(why, why)
            checks += [("reaction", "Reaction over the index", pct(seen.get("reaction")),
                        f"above {MIN_REACTION:g}%, at most {MAX_REACTION:g}%, over {REACTION_DAYS} sessions", st[2] if st[0] else None),
                       ("liquidity", "Liquidity", "passed" if st[3] else "—", "the market's price and traded-value floors", st[3] if st[2] else None)]
            gates = pset.rows(checks, fmt=lambda v: str(v))
            setup = pset.rows([("filed", "Results released", str(pd.Timestamp(r.announced).date()), f"quarter to {pd.Timestamp(r.period_end).date()}", True)])
            shapes = []
            if seen.get("d_prev") is not None:
                w = df.loc[seen["d_prev"]: seen["d_react"]]
                shapes = [{"shape": "box", "from": str(seen["d_prev"].date()), "to": str(seen["d_react"].date()),
                           "top": float(w["high"].max()), "bottom": float(w["low"].min()), "role": "base",
                           "label": f"results reaction {pct(seen.get('stock_ret'))} ({pct(seen.get('reaction'))} over the index)"},
                          {"shape": "level", "bars": 10, "to": str(seen["d_react"].date()), "price": float(df.at[seen["d_prev"], "close"]),
                           "role": "support", "label": f"close before the results {float(df.at[seen['d_prev'], 'close']):,.2f}"}]
            trade = by_entry.get(pd.Timestamp(c["entry_date"])) if c else None
            if trade is not None:
                trade = {**trade, "initial_stop": c["stop"]}
            oc = pset.outcome(df, "long", trade, "not bought: a stronger filing that session, or the book was full")
            out.append(pset.episode(
                df, [k], k, name="Confirmed results surprise", side="long", kind="pass" if c else "fail", why=reason,
                gates=gates, setup_rows=setup, shapes=shapes,
                text=(f"Results released {pd.Timestamp(r.announced).date()}: profit {pct(r.yoy)} year on year, revenue {pct(r.rev_growth)}."),
                entry=c["price"] if c else None, stop=c["stop"] if c else None, stop_on_close=bool(STOP_ON_REACTION_LOW),
                entry_text=" ".join(cls.render_doc(x) for x in cls.entry_rules), outcome_=oc if c else None,
                anchored=k in traded))
        return out


def main(argv: list[str] | None = None) -> dict | None:
    """The runner. `--const NAME=VALUE` sets a module constant for this run only (the mode switch:
    `--const SURPRISE_MODE=2`), so it enters the run's spec id; the constants are restored afterwards, because
    the job worker runs several backtests in one process."""
    import sys
    from ..strategies.variants import apply_consts
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--const", action="append", default=None)
    known, _ = pre.parse_known_args(argv)
    mod = sys.modules[__name__]
    saved = {k: v for k, v in vars(mod).items() if k.isupper() and isinstance(v, (int, float)) and not isinstance(v, bool)}
    try:
        if known.const:
            apply_consts("pead", dict(kv.split("=", 1) for kv in known.const))
        return _main(argv)
    finally:
        for k, v in saved.items():
            setattr(mod, k, v)


def _main(argv: list[str] | None) -> dict | None:
    from ..paths import run_dir
    from .baseline import benchmark_for
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Post-earnings announcement drift")
    ap.add_argument("--strategy", default="pead")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True)
    ap.add_argument("--hold-sessions", type=int, default=HOLD_SESSIONS,
                    help="drift window: market sessions a position is held before the time exit")
    ap.add_argument("--max-positions", type=int, default=MAX_POSITIONS,
                    help="most positions held at once, one per company")
    ap.add_argument("--position-pct", type=float, default=POSITION_PCT,
                    help="percent of the account (cash plus positions) spent on each buy")
    ap.add_argument("--min-yoy", type=float, default=MIN_YOY_GROWTH,
                    help="mode 1: minimum net-profit growth, %% over the same quarter a year earlier")
    ap.add_argument("--season-top", type=float, default=SEASON_RANK_TOP,
                    help="mode 1: growth must rank in this top %% of the results for the same quarter so far")
    ap.add_argument("--cost-bps", type=float, default=PeadStrategy.cost_bps,
                    help="cost per side, basis points of the amount traded")
    ap.add_argument("--const", action="append", default=None, metavar="NAME=VALUE",
                    help="set a module constant for this run, e.g. SURPRISE_MODE=2 (it enters the spec id)")
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)

    cfg = MARKETS[a.market]
    mode = int(SURPRISE_MODE)
    ev = load_events(a.market)
    prices = load_event_prices(a.market, sorted(ev["symbol"].unique()))
    braw = cache.load_cached(a.market, cfg.benchmark_ticker)
    bench = braw["close"].astype(float) if braw is not None else None
    tdf, eq, held, csh, costs, dropped, days = run(
        a.market, a.start, hold_sessions=a.hold_sessions, max_positions=a.max_positions,
        position_pct=a.position_pct, min_yoy=a.min_yoy, season_top=a.season_top,
        cost_bps=a.cost_bps, preloaded=(ev, prices, bench))

    # judged against the strategy's own index for the market (benchmark_key: the Smallcap 250 in India), while
    # the reaction itself is read against the market's broad index
    btk, bname = benchmark_for("pead", a.market)
    rraw = cache.load_cached(a.market, btk)
    bc = rraw["close"].astype(float).reindex(eq.index).ffill() if rraw is not None else None

    # The universe control, computed and REPORTED rather than left to the reader: an equal-weight
    # buy-and-hold of every company with an event, so the strategy is judged against its own pool too.
    upx = pd.DataFrame({s: d["close"].astype(float) for s, d in prices.items()}).sort_index().ffill()
    upx = upx.loc[eq.index[0]:eq.index[-1]]
    yrs = max((upx.index[-1] - upx.index[0]).days / 365.25, 1e-9)
    firsts = upx.apply(lambda c: c.dropna().iloc[0] if c.notna().any() else float("nan"))
    basket = upx.div(firsts, axis=1).mean(axis=1)
    uni_cagr = ((basket.iloc[-1] / basket.iloc[0]) ** (1 / yrs) - 1) * 100
    # the index held at the book's own exposure: each session's index return times the share of the book
    # invested at the previous close -- what the same market exposure earned with no selection
    invested = (1 - csh / eq).clip(lower=0).shift().fillna(0)
    matched = None
    if bc is not None:
        mret = (bc.pct_change().fillna(0) * invested).add(1).cumprod()
        matched = ((mret.iloc[-1]) ** (1 / yrs) - 1) * 100

    floor = liquidity_floor(cfg, mode)
    notes = [
        f"Mode {mode}: {MODE_NAMES.get(mode, mode)}. {len(ev):,} results events for {ev['symbol'].nunique():,} companies; "
        f"{days:,} sessions produced at least one entry. Dropped: {dropped['filters']:,} failed the results filters, "
        f"{dropped['reaction']:,} the price reaction, {dropped['liquidity']:,} the price/turnover floors "
        f"({cfg.currency_symbol}{floor:,.0f} a day), {dropped['no_bar']:,} had no usable bar.",
        f"UNIVERSE CONTROL: an equal-weight buy-and-hold of these {len(prices):,} companies returned "
        f"{uni_cagr:.2f}% a year over the same dates."
        + (f" The benchmark held at this book's own daily exposure (average {invested.mean() * 100:.0f}% invested) "
           f"returned {matched:.2f}% a year." if matched is not None else ""),
        "Each event is dated by the results release (an 8-K with Item 2.02 in the US, the exchange broadcast or "
        "results board meeting in India), not the later 10-Q/10-K filing; year-ago figures come from the "
        "company's own filing a year earlier, and SUE is on split-adjusted EPS.",
        "The universe is point in time: an event counts only if its company was liquid at the month-end before "
        "its results, so the run does not depend on which companies were fetched later." if mode != 2 else
        "The universe is every company with a recorded results announcement and prices; an event counts only if "
        "its 20-session traded value before the results reached the floor.",
        f"Costs: {a.cost_bps:g}bps per side. Ordinary dividends are excluded on both the strategy and the benchmark; "
        "special dividends and demergers are credited to a holder.",
    ]
    perf = metrics.compute(equity=eq, positions_open=held, trades=tdf,
                           max_open_positions=a.max_positions, costs_paid=costs,
                           bench_close=bc, cash=csh, notes=notes)
    if bc is not None:
        for k, v in metrics.benchmark_stats(bc).items():
            setattr(perf, k, v)
    perf.benchmark_name = f"{bname} ({btk})"

    mode_part = "" if mode == 1 else (f"_mode{mode}_top{REACTION_TOP_PCT:g}"
                                      + (f"_floor{REACTION_MIN_TURNOVER_CR:g}cr" if floor != cfg.screener.min_dollar_volume else ""))
    name = (f"{a.start}_hold{a.hold_sessions}_top{a.max_positions}x{a.position_pct:g}pct"
            + (f"_yoy{a.min_yoy:g}_season{a.season_top:g}" if mode == 1 else mode_part)
            + f"_{a.cost_bps:g}bps_{PeadStrategy.spec_id()}")
    out = run_dir(a.market, a.strategy, name)
    tdf.to_csv(out / "trades.csv", index=False)
    pd.DataFrame({"equity": eq, "cash": csh, "positions_open": held,
                  "drawdown_pct": metrics.drawdown_series(eq) * 100}).to_csv(out / "equity.csv")
    # the event universe as this run saw it, so a later re-run can be compared event by event
    ev[[c for c in ("symbol", "period_end", "filed", "announced", "yoy", "sue", "season_pct") if c in ev]].to_csv(
        out / "events.csv", index=False)
    print()
    print(metrics.format_report(perf, cfg.currency_symbol, a.max_positions))
    print(f"\nUNIVERSE CONTROL: equal-weight buy-and-hold of the {len(prices):,} companies "
          f"= {uni_cagr:.2f}% CAGR vs this strategy's {perf.cagr_pct:.2f}%"
          + (f"; {bname} at the book's exposure {matched:.2f}%" if matched is not None else ""))
    try:
        from . import report as report_mod
        md = report_mod.write_report(
            out, f"{cfg.name} — post-earnings drift ({MODE_NAMES.get(mode, mode)}), {a.start} onward",
            perf, eq, held, tdf, cfg.currency_symbol, a.max_positions, bc,
            f"python3 -m swing_screener.backtesting.pead --market {a.market} --start {a.start}"
            + "".join(f" --const {kv}" for kv in (a.const or [])))
        print(f"Report -> {md}")
    except Exception as e:   # noqa: BLE001
        print(f"(markdown report not generated: {type(e).__name__}: {e})")
    if not a.no_ingest:
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return {"perf": perf, "run_dir": str(out), "trades": int(len(tdf)), "matched_cagr": matched}


if __name__ == "__main__":
    main()
