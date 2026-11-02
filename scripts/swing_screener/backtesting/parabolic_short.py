"""Kullamägi's parabolic short, on daily bars -- a short-only book with its own simulator.

THE SETUP. Kristjan Kullamägi ("3 timeless setups", qullamaggie.com, 8 Jan 2021, "The Parabolic
Short"): a stock up 50-100%+ in days or weeks if it is a larger company, 300-1000%+ if a smaller one,
usually after 3-5+ up days in a row. He shorts the opening-range low, the first red 5-minute candle,
or a failed bounce into VWAP, with the high of the day as the stop, and covers into the 10- and
20-day moving averages, "where these stocks usually bounce". No intraday data is stored, so every
intraday trigger becomes its daily stand-in, named below. The long side of the same idea -- the
first green day after a collapse -- is `strategies/parabolic_long.py`; the two share the first-day
reversal, the close entry, the day's extreme as the stop and the open fill on a gap.

WHY ITS OWN RUNNER. The per-symbol engine (`backtest.py`, `portfolio_sim.py`) is long-only in every
layer (plan geometry, fills, R, sizing), and every per-symbol strategy runs through it. This book
needs a handful of rules, so it is simulated here, the way `stage4_shorts` simulates its book, and
nothing a long strategy runs on moves.

THE COSTS ARE THE QUESTION. Parabolic small caps are the hardest stocks to borrow. No borrow data is
stored, so the fee is a named assumption (`BORROW_PCT`, a year, charged per night held) that the
queue runs at each of `BORROW_LEVELS` (`--borrow-pct`); unavailable locates are not modelled at all.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import MARKETS
from ..core import indicators as ind
from ..marketdata import cache, corporate_actions, universe
from ..strategies.base import PortfolioStrategy
from . import metrics
from .stage4_shorts import _stats

logger = logging.getLogger("backtest")

MIN_BARS = 120

# ---- the setup: a parabolic run that has just turned
RUN_MAX_BARS = 20             # the run is measured over at most this many sessions ("days or weeks")
MIN_UP_DAYS = 3               # consecutive up closes into the turn (he: "usually up 3-5+ days in a row")
#: The size proxy. Market cap is not stored, so size is read from traded value: the median of
#: close x volume over SIZE_BARS sessions, measured BEFORE the run window, so the spike's own volume
#: cannot lift a small company into the large tier. $100M a day was roughly the turnover of a
#: low-end S&P 500 member in 2013-2021; a stock trading that much before its run is "larger".
SIZE_BARS = 50
LARGE_TURNOVER = 100_000_000
MIN_RUN_PCT_LARGE = 50.0      # his "up 50-100%+" for a larger company: the low end
MIN_RUN_PCT_SMALL = 300.0     # his "up 300-1000%+" for a smaller one: the low end
LIQ_BARS = 20                 # 20-session mean traded value >= the market's floor (the shared floor)
MIN_STOP_PCT = 1.0            # skip a red day whose high is less than this % above its close
MAX_STOP_PCT = 30.0           # skip a red day whose high is more than this % above its close

# ---- the exits: cover into the averages, half at each, or at the time limit
TARGET_FAST = 10              # first tranche covers when the low reaches the prior session's EMA(10)
TARGET_SLOW = 20              # the rest when the low reaches the prior session's EMA(20)
FIRST_TRANCHE_PCT = 50.0      # share of the position covered at the fast average
TIME_STOP = 10                # sessions; whatever is left is covered at that close

# ---- size (his: risk 0.25-1% a trade, positions mostly 10-20%, never over 30% in one stock)
RISK_PCT = 0.5                # of equity per short, to the stop
MAX_POSITION_PCT = 20.0       # one short's notional
MAX_OPEN_RISK_PCT = 3.0       # open risk on all shorts together
MAX_GROSS_PCT = 100.0         # short notional on all positions together: no leverage

# ---- costs. The borrow fee is the assumption the result hangs on: run at each of BORROW_LEVELS.
COST_BPS = 25.0               # per side: spread and slippage on a fast, thin stock at the close
BORROW_PCT = 15.0             # a year, of the short notional: the base case, a moderate hard-to-borrow rate
BORROW_LEVELS = (0.0, 15.0, 100.0)   # none, moderate, punitive -- one queued run each
DIVIDEND_PCT = 0.5            # a year, paid while short: parabolic movers rarely pay ordinary dividends

# ---- the report: the long book the sleeve is compared with, and the index's worst months
LONG_BOOK = "momentum_dual_combo"
WORST_MONTHS = 12

# ---- the pass criterion, fixed before any result (see `status`)
PASS_MIN_TRADES = 50
PASS_MIN_AVG_R = 0.25
PASS_PUNITIVE_BORROW = 100.0


def symbol_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Everything the signal and the exits read, per daily bar, causal (each column uses its own bar
    and earlier ones; the targets are read from the PRIOR session's averages by the simulator)."""
    d = df[["open", "high", "low", "close", "volume"]].astype(float)
    out = d.copy()
    tv = d["close"] * d["volume"]
    out["liq"] = tv.rolling(LIQ_BARS, min_periods=LIQ_BARS).mean()
    out["size_tv"] = tv.shift(RUN_MAX_BARS + 1).rolling(SIZE_BARS, min_periods=SIZE_BARS).median()
    prev_close = d["close"].shift(1)
    out["run_pct"] = (prev_close / d["low"].shift(1).rolling(RUN_MAX_BARS, min_periods=RUN_MAX_BARS).min() - 1) * 100
    up = (d["close"] > prev_close).astype(int)
    streak = up.groupby((up == 0).cumsum()).cumsum()
    out["up_streak"] = streak.shift(1)
    out["ema_fast"] = ind.ema(d["close"], TARGET_FAST)
    out["ema_slow"] = ind.ema(d["close"], TARGET_SLOW)
    large = out["size_tv"] >= LARGE_TURNOVER
    need = np.where(large, MIN_RUN_PCT_LARGE, MIN_RUN_PCT_SMALL)
    out["tier"] = np.where(large, "large", "small")
    red = (d["close"] < d["open"]) & (d["close"] < prev_close)
    out["sig"] = (red & (out["up_streak"] >= MIN_UP_DAYS) & (out["run_pct"] >= need)
                  & out["size_tv"].notna())
    return out


def prepare(market: str) -> dict:
    """Load the universe once into per-symbol frames (only symbols that ever signal are kept)."""
    if market != "us":
        # Overnight shorts of Indian cash shares are not allowed; a short needs stock futures, which
        # most Indian parabolic movers do not have. See the caveats.
        raise SystemExit(f"{market}: parabolic_short runs on the US only (no overnight cash shorts in India)")
    cfg = MARKETS[market]
    braw = cache.load_cached(market, cfg.benchmark_ticker)
    if braw is None:
        raise SystemExit(f"{market}: no stored benchmark {cfg.benchmark_ticker}")
    bench = braw["close"].astype(float)
    skip = universe.non_stock_symbols(market)
    tickers = [t for t in universe.load_universe(market) if t not in skip and t != cfg.benchmark_ticker]
    frames = {}
    for i in range(0, len(tickers), 400):
        for sym, d in cache.load_many_cached(market, tickers[i:i + 400]).items():
            if d is None or len(d) < MIN_BARS:
                continue
            try:
                f = symbol_frame(d)
            except Exception as e:   # noqa: BLE001 -- one malformed history must not end the run
                logger.warning("%s: skipped (%s)", sym, e)
                continue
            if f["sig"].any():
                frames[sym] = f
        logger.info("%s: %d/%d symbols read, %d with a parabolic signal", market, min(i + 400, len(tickers)),
                    len(tickers), len(frames))
    return {"market": market, "bench": bench, "frames": frames, "n_universe": len(tickers),
            "credits": corporate_actions.Credits.for_market(market, list(frames))}


def candidates(prep: dict, start: pd.Timestamp) -> tuple[dict, dict]:
    """{signal date: [candidate, ...]}, the most extended run first."""
    floor = MARKETS[prep["market"]].screener.min_dollar_volume or 0
    out: dict = {}
    dropped = {"liquidity": 0, "stop_narrow": 0, "stop_wide": 0, "at_target": 0}
    for sym, f in prep["frames"].items():
        for d in f.index[f["sig"].values & (f.index >= start)]:
            r = f.loc[d]
            if not (r["liq"] >= floor):
                dropped["liquidity"] += 1
                continue
            close, stop = float(r["close"]), float(r["high"])
            pct = (stop / close - 1) * 100
            if pct < MIN_STOP_PCT:
                dropped["stop_narrow"] += 1
                continue
            if pct > MAX_STOP_PCT:
                dropped["stop_wide"] += 1
                continue
            if not (close > r["ema_fast"]):   # already at the first target: nothing to cover into
                dropped["at_target"] += 1
                continue
            out.setdefault(d, []).append({"symbol": sym, "stop": stop, "close": close, "tier": r["tier"],
                                          "run_pct": float(r["run_pct"]), "up_streak": int(r["up_streak"])})
    for d in out:
        out[d].sort(key=lambda c: -c["run_pct"])
    return out, dropped


def run(prep: dict, start: str, borrow_pct: float = BORROW_PCT, cands: tuple | None = None):
    """Simulate the short book. Returns (trades, equity, positions, gross short %, costs, dropped)."""
    cfg = MARKETS[prep["market"]]
    side = COST_BPS / 10_000
    carry_day = (borrow_pct + DIVIDEND_PCT) / 100 / 252
    start_ts = pd.Timestamp(start)
    sig, dropped = cands if cands is not None else candidates(prep, start_ts)
    frames = prep["frames"]
    cal = prep["bench"].index[prep["bench"].index >= start_ts]
    cash = float(cfg.account_size)
    open_pos: dict = {}
    trades, eq_log, held_log, gross_log = [], [], [], []
    costs_total = 0.0
    skipped = {"already_short": 0, "risk_budget": 0}
    last_close: dict = {}

    def buy_back(p, n_sh, price):
        nonlocal cash, costs_total
        fee = n_sh * price * side
        cash -= n_sh * price + fee
        costs_total += fee
        p["fee"] += fee
        p["covered_value"] += n_sh * price
        p["open_sh"] -= n_sh

    def close_trade(sym, p, d, reason):
        pnl = p["proceeds"] - p["covered_value"] - p["fee"] - p["carry"] - p["paid"]
        risk = p["shares"] * p["risk_ps"]
        trades.append({
            "symbol": sym, "direction": "short", "setup": p["tier"], "entry_date": p["date"],
            "entry_price": round(p["price"], 4), "initial_stop": round(p["stop0"], 4),
            "exit_date": d, "exit_price": round(p["covered_value"] / p["shares"], 4),
            "shares": round(p["shares"], 4), "exit_reason": reason, "first_target": p["t1"],
            "pnl": round(pnl, 2), "notional": round(p["proceeds"], 2), "costs": round(p["fee"], 2),
            "carry": round(p["carry"], 2), "paid": round(p["paid"], 2), "run_pct": round(p["run_pct"], 1),
            "up_streak": p["up_streak"], "holding_days": (d - p["date"]).days, "sessions": p["n"],
            "r_multiple": round(pnl / risk, 4) if risk > 0 else float("nan"),
            "mfe_r": round(p["mfe"] / p["risk_ps"], 3) if p["risk_ps"] > 0 else float("nan"),
        })
        del open_pos[sym]

    credits = prep.get("credits")
    credit_after = cal[0] - pd.Timedelta(days=1)
    for d in cal:
        # ---- a special dividend or demerger on a name held short: the short pays it, its stop moves down
        if credits is not None:
            for s, c in credits.on(d, credit_after, open_pos).items():
                p = open_pos[s]
                cash -= c * p["open_sh"]
                p["paid"] += c * p["open_sh"]
                p["stop"] -= c
                if s in last_close:
                    last_close[s] -= c
            credit_after = d
        # ---- the day's exits on positions entered before today: the stop first, then the targets
        closed_today = set()
        for s in list(open_pos):
            p = open_pos[s]
            f = frames[s]
            if d not in f.index:
                continue
            k = f.index.get_loc(d)
            b = f.iloc[k]
            p["n"] += 1
            hi, lo, cl, op = float(b["high"]), float(b["low"]), float(b["close"]), float(b["open"])
            if hi >= p["stop"]:
                # a squeeze that gaps up through the stop fills at the open, not at the stop
                buy_back(p, p["open_sh"], max(p["stop"], op))
                close_trade(s, p, d, "STOP")
                closed_today.add(s)
                continue
            p["mfe"] = max(p["mfe"], p["price"] - lo)
            prev = f.iloc[k - 1]
            fast, slow = float(prev["ema_fast"]), float(prev["ema_slow"])
            reason = None
            if not p["t1"] and lo <= fast:
                buy_back(p, p["shares"] * FIRST_TRANCHE_PCT / 100, min(op, fast))
                p["t1"] = True
                reason = "TARGET_FAST"
            if p["open_sh"] > 1e-9 and lo <= slow:
                buy_back(p, p["open_sh"], min(op, slow))
                reason = "TARGET_SLOW"
            elif p["open_sh"] > 1e-9 and p["n"] >= TIME_STOP:
                buy_back(p, p["open_sh"], cl)
                reason = "TIME"
            if p["open_sh"] <= 1e-9:
                close_trade(s, p, d, reason)
                closed_today.add(s)
        for s in open_pos:
            f = frames[s]
            if d in f.index:
                last_close[s] = float(f.at[d, "close"])
        # ---- entries at today's close, from today's signals
        liab = sum(p["open_sh"] * last_close.get(s, p["price"]) for s, p in open_pos.items())
        equity = cash - liab
        for c in sig.get(d, []):
            s = c["symbol"]
            if s in open_pos or s in closed_today:
                skipped["already_short"] += 1
                continue
            o, stop = c["close"], c["stop"]
            open_risk = sum(p["open_sh"] * max(p["stop"] - last_close.get(x, p["price"]), 0)
                            for x, p in open_pos.items())
            gross = sum(p["open_sh"] * last_close.get(x, p["price"]) for x, p in open_pos.items())
            budget = min(equity * RISK_PCT / 100, equity * MAX_OPEN_RISK_PCT / 100 - open_risk)
            shares = min(budget / (stop - o), (equity * MAX_GROSS_PCT / 100 - gross) / o,
                         equity * MAX_POSITION_PCT / 100 / o) if budget > 0 else 0
            if shares * o < equity * RISK_PCT / 100 * 0.25:   # too small to be worth a slot
                skipped["risk_budget"] += 1
                continue
            fee = shares * o * side
            cash += shares * o - fee
            costs_total += fee
            open_pos[s] = {"shares": shares, "open_sh": shares, "price": o, "proceeds": shares * o, "fee": fee,
                           "covered_value": 0.0, "date": d, "stop": stop, "stop0": stop, "risk_ps": stop - o,
                           "tier": c["tier"], "run_pct": c["run_pct"], "up_streak": c["up_streak"], "n": 0,
                           "carry": 0.0, "paid": 0.0, "mfe": 0.0, "t1": False}
            last_close[s] = o
        # ---- the night's borrow and dividend carry on what is still short
        for s, p in open_pos.items():
            ch = p["open_sh"] * last_close.get(s, p["price"]) * carry_day
            cash -= ch
            p["carry"] += ch
            costs_total += ch
        liab = sum(p["open_sh"] * last_close.get(s, p["price"]) for s, p in open_pos.items())
        val = cash - liab
        eq_log.append((d, val))
        held_log.append((d, len(open_pos)))
        gross_log.append((d, liab / val * 100 if val > 0 else float("nan")))
    for s in list(open_pos):   # valued at the last close, marked OPEN
        p = open_pos[s]
        buy_back(p, p["open_sh"], last_close.get(s, p["price"]))
        close_trade(s, p, cal[-1], "OPEN")
    eq = pd.Series(dict(eq_log)).sort_index()
    return (pd.DataFrame(trades), eq, pd.Series(dict(held_log)).sort_index(),
            pd.Series(dict(gross_log)).sort_index(), costs_total, {**dropped, **skipped})


# ------------------------------------------------------------------ the report's comparisons

def index_at_exposure(bench: pd.Series, gross: pd.Series) -> pd.Series:
    """The index held LONG at the book's own capital use: each session's index return times the
    previous session's gross short exposure. The yardstick for "what the same capital at work in the
    market made", not a hedge comparison."""
    b = bench.reindex(gross.index).ffill()
    w = (gross.shift(1).fillna(0) / 100).clip(lower=0)
    return (1 + b.pct_change().fillna(0) * w).cumprod()


def find_long_book(market: str, out_dir: Path) -> Path | None:
    """The newest stored `LONG_BOOK` run with this run's start and stage tag, or None."""
    tag = out_dir.name[out_dir.name.find("_stage-"):] if "_stage-" in out_dir.name else ""
    start = out_dir.name.split("_", 1)[0]
    root = out_dir.parent.parent / LONG_BOOK
    if not tag or not root.exists():
        return None
    runs = [p for p in root.iterdir() if p.name.endswith(tag) and p.name.startswith(start + "_")
            and (p / "equity.csv").exists()]
    return max(runs, key=lambda p: (p / "equity.csv").stat().st_mtime) if runs else None


def hedge_view(eq: pd.Series, bench: pd.Series, long_eq: pd.Series | None) -> dict:
    """Monthly: the book's return in the index's WORST_MONTHS worst months, and its correlation with
    the long book. Reported, never part of the pass criterion."""
    m = eq.resample("ME").last().pct_change().dropna()
    bm = bench.reindex(eq.index).ffill().resample("ME").last().pct_change().reindex(m.index)
    worst = bm.nsmallest(WORST_MONTHS).index
    out = {"worst_months_book_pct": round(float(m.reindex(worst).mean() * 100), 2),
           "worst_months_index_pct": round(float(bm.reindex(worst).mean() * 100), 2),
           "corr_index": round(float(m.corr(bm)), 3)}
    if long_eq is not None:
        lm = long_eq.resample("ME").last().pct_change().reindex(m.index)
        out["corr_long_book"] = round(float(m.corr(lm)), 3)
    return out


# ------------------------------------------------------------------ documentation

DOC = {
    "key": "parabolic_short",
    "name": "Parabolic short (Kullamägi)",
    "description": (
        "Short a stock that has gone parabolic -- up {MIN_RUN_PCT_LARGE}%+ (larger) or {MIN_RUN_PCT_SMALL}%+ "
        "(smaller) within {RUN_MAX_BARS} sessions after {MIN_UP_DAYS}+ up days -- at the close of its first "
        "red day, stop at that day's high, and cover into the {TARGET_FAST}- and {TARGET_SLOW}-day averages "
        "or after {TIME_STOP} sessions. US only; its own short simulator, run at several borrow fees."
    ),
    "status": (
        "NOT YET RUN. PASS CRITERION, fixed before any result (2026-11-02), judged on the optimise stage "
        "(in-sample, 2013-2021), US, the base rules at the base borrow fee ({BORROW_PCT}% a year): (1) at "
        "least {PASS_MIN_TRADES} closed trades; (2) an average of at least +{PASS_MIN_AVG_R}R a trade after "
        "costs, borrow and dividends; (3) a positive CAGR; and (4) at the punitive borrow fee "
        "({PASS_PUNITIVE_BORROW}% a year) a positive average R. All four or it fails. Its use as a hedge "
        "beside the long book (correlation with momentum_dual_combo, return in the index's worst months) is "
        "reported, not judged. Only a version that passes goes to verify, once."
    ),
    "thesis": (
        "A stock that has gone vertical in days is held by buyers who chased it, and the first day it "
        "closes red is the first sign the buying has run out. Short-term extremes tend to revert (De Bondt "
        "and Thaler 1985 at long horizons; Lehmann 1990 and Jegadeesh 1990 at one week to one month), and "
        "Kullamägi's claim is narrower: the reversion of a parabolic run reaches the 10- and 20-day "
        "averages often enough, from a stop at the day's high, to pay 5-10 times the risk. The danger is "
        "being early -- a squeeze can double a stock again -- which is why the setup waits for the first "
        "red day and the stop is the day's high."
    ),
    "how_it_works": (
        "The idea. Wait for a run so steep it cannot hold, short the first day it turns, and cover into "
        "the short averages where these stocks usually bounce. His triggers are intraday (the opening-range "
        "low, the first red 5-minute candle, a failed bounce into VWAP); none can be tested on daily bars, "
        "so the first red daily close stands in for all of them.",
        "Step 1 -- the run. The prior close is at least {MIN_RUN_PCT_LARGE}% above the lowest low of the "
        "{RUN_MAX_BARS} sessions before today for a larger company, {MIN_RUN_PCT_SMALL}% for a smaller one, "
        "and the prior {MIN_UP_DAYS} or more closes were each up.",
        "Step 2 -- the size. Market cap is not stored. A stock whose median traded value over the "
        "{SIZE_BARS} sessions BEFORE the run window was at least ${LARGE_TURNOVER} a day is larger; any "
        "other is smaller.",
        "Step 3 -- the turn. Today closes below its open and below the prior close: the first red day.",
        "Step 4 -- the short, at today's close, stop at today's high, sized to risk {RISK_PCT}% of equity.",
        "Step 5 -- the cover: {FIRST_TRANCHE_PCT}% when the low reaches the {TARGET_FAST}-day average, the "
        "rest at the {TARGET_SLOW}-day, whatever is left after {TIME_STOP} sessions at the close; the stop "
        "covers everything.",
        "Running it. `python -m jobs enqueue backtest --market us --strategies parabolic_short --stage "
        "optimise`, once per borrow level with `--bt '--borrow-pct N'` for N in {BORROW_LEVELS}.",
    ),
    "entry_rules": (
        "The run. The prior session's close is at least {MIN_RUN_PCT_LARGE}% (larger) or "
        "{MIN_RUN_PCT_SMALL}% (smaller) above the lowest low of the {RUN_MAX_BARS} sessions ending at the "
        "prior session.\n\n**Kullamägi:** up 50-100%+ in a few days or weeks for a larger cap, 300-1000%+ "
        "for a smaller one. Differs: the low end of each range, over a fixed window.",
        "The up days. The {MIN_UP_DAYS} or more sessions before today each closed above the session "
        "before.\n\n**Kullamägi:** usually up 3-5+ days in a row. Differs: a hard requirement, where he "
        "says usually -- some of his examples trend for weeks and then speed up.",
        "The size tiers. Larger: the median traded value (close x volume) over the {SIZE_BARS} sessions "
        "ending {RUN_MAX_BARS} sessions before today is at least ${LARGE_TURNOVER}. Smaller: below it. "
        "Measured before the run so the run's own volume cannot promote a small company.\n\n"
        "**Kullamägi:** larger vs smaller cap. Differs: traded value stands in for market cap, which is not "
        "stored.",
        "Liquid. The {LIQ_BARS}-session mean traded value is at or above the market's liquidity floor "
        "($10 million a day, as configured) -- the floor every other backtest uses.",
        "The first red day. Today's close is below today's open and below the prior close.\n\n"
        "**Kullamägi:** short the opening-range low on 1- or 5-minute candles, the first red 5-minute "
        "candle, or a failed bounce into VWAP. Differs: daily bars only, so the entry waits for the whole "
        "day to close red -- later and usually lower than his intraday entries, with a wider stop.",
        "The stop. Today's high. A red day whose high is less than {MIN_STOP_PCT}% above its close is "
        "skipped (the risk is a sliver and R becomes meaningless), and so is one more than {MAX_STOP_PCT}% "
        "above it. A red day that already closed at or below its {TARGET_FAST}-day average is skipped: "
        "there is nothing left to cover into.\n\n**Kullamägi:** the high of the day.",
        "The short. At today's close. Shares = {RISK_PCT}% of equity / (stop - close), cut so that one "
        "short's notional stays within {MAX_POSITION_PCT}% of equity, open risk on all shorts within "
        "{MAX_OPEN_RISK_PCT}% and short notional within {MAX_GROSS_PCT}%. Several on one day: the largest "
        "run first.\n\n**Kullamägi:** risk 0.25-1% a trade, positions mostly 10-20%, never over 30% "
        "overnight in one stock.",
        "Costs. {COST_BPS} bps a side; borrow at {BORROW_PCT}% a year in the base case and dividends at "
        "{DIVIDEND_PCT}% a year, both charged on the short notional for every night held. Each run states "
        "its borrow fee; the queue runs {BORROW_LEVELS}. No interest is credited on short proceeds.",
    ),
    "exit_rules": (
        "Each session after the entry the stop is checked first, then the targets, then the time limit. "
        "On a day that touches both the stop and a target, the stop is assumed to come first.",
        "Stop. The day's high at or above the stop covers everything at the stop -- or at the open, when "
        "the stock gaps up through it.\n\n**Kullamägi:** the high of the day; tight stops are the point.",
        "First target. When the day's low reaches the prior session's {TARGET_FAST}-day exponential "
        "average, {FIRST_TRANCHE_PCT}% is covered at that average (at the open if it opens below it).\n\n"
        "**Kullamägi:** cover into the 10- and 20-day averages. Differs: the split between the two is ours.",
        "Second target. When the low reaches the prior session's {TARGET_SLOW}-day exponential average, the "
        "rest is covered there (at the open if it opens below it).",
        "Time stop. After {TIME_STOP} sessions whatever is still short is covered at the close.\n\n"
        "**Kullamägi:** none stated; a parabolic short that has not come in within two weeks is no longer "
        "the trade he describes.",
        "A position open when the backtest ends is covered at its last close and marked OPEN.",
    ),
    "caveats": (
        "**BORROW IS ASSUMED, AND LOCATES ARE NOT MODELLED AT ALL.** Parabolic small caps are often hard "
        "or impossible to borrow, and their fees run to tens or hundreds of percent a year. No borrow data "
        "is stored: the fee is a flat {BORROW_PCT}% a year in the base case, and the queue reruns at "
        "{BORROW_LEVELS} so the sensitivity is visible. Every signal is assumed shortable -- the backtest "
        "shorts names a broker would have refused, so it overstates what could actually be traded.",
        "**Survivorship biases this one DOWNWARD.** The stored universe is today's lists, which leave out "
        "delisted companies, and many collapsed parabolics later delisted -- exactly the best shorts. The "
        "opposite of the long side's bias.",
        "**Daily bars, not his intraday entries.** He shorts the opening-range low, the first red 5-minute "
        "candle or a failed VWAP bounce, with the day's high only a few percent away. Waiting for a red "
        "daily close enters later, often after much of the day's fall, with a wider stop: fewer R per "
        "point of fall than he describes. His 5-10x risk cannot be read off this test.",
        "**The close entry assumes a fill at the close.** In practice a market-on-close order; on a thin, "
        "fast stock the auction price can differ from the last print. {COST_BPS} bps a side is charged for "
        "that and the spread.",
        "**Short-sale restriction (US Rule 201).** After a 10% fall from the prior close a stock may be "
        "shorted only on an uptick for the rest of that day and the next. A closing-auction entry is "
        "largely unaffected, but a real trader's intraday entries on a crashing red day often would be.",
        "**Gap risk.** A squeeze can open far above the stop; the stop then fills at the open, and a loss "
        "can be several R. Halts (common on these stocks) are not modelled.",
        "**India is not run.** Overnight short-selling of Indian cash shares is not permitted; a short "
        "needs stock futures, which only F&O-listed stocks have, and most Indian parabolic movers are not "
        "on that list.",
        "**Special dividends and demergers** are paid by a short on the ex-date and move its stop down by "
        "the payout; ordinary dividends are a flat {DIVIDEND_PCT}% a year, since stored prices are not "
        "dividend-adjusted.",
        "**The R figures are true risk multiples**: profit after costs, borrow and dividends over the "
        "initial risk to the stop.",
    ),
}


class ParabolicShortStrategy(PortfolioStrategy):
    """Kullamägi's parabolic short on daily bars, with its own short simulator."""

    key = DOC["key"]
    doc = DOC
    family = "parabolic_short"
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-02",
         "First version, from Kullamägi's 'The Parabolic Short' (qullamaggie.com, 8 Jan 2021) on daily bars: "
         "a size-tiered run-up with consecutive up days, short the first red day's close, stop at its high "
         "(gap fills at the open), cover half at the 10-day and the rest at the 20-day EMA or after a time "
         "limit. Its own short simulator (the per-symbol engine is long-only); borrow fee as a named "
         "assumption run at three levels. US only."),
    )
    name = DOC["name"]
    description = DOC["description"]
    status = DOC["status"]
    thesis = DOC["thesis"]
    how_it_works = tuple(DOC["how_it_works"])
    caveats = tuple(DOC["caveats"])
    entry_rules = tuple(DOC["entry_rules"])
    exit_rules = tuple(DOC["exit_rules"])

    behaviour = "mean_reversion"
    selection = "time_series"
    style = "pullback"
    runner = "parabolic_short"

    param_docs = (
        ("Run window", "RUN_MAX_BARS", "Sessions the run-up is measured over."),
        ("Run, larger", "MIN_RUN_PCT_LARGE", "Minimum run-up for the larger tier, %."),
        ("Run, smaller", "MIN_RUN_PCT_SMALL", "Minimum run-up for the smaller tier, %."),
        ("Size proxy", "LARGE_TURNOVER", "Median daily traded value before the run that makes a stock 'larger'."),
        ("Up days", "MIN_UP_DAYS", "Consecutive up closes into the first red day."),
        ("Targets", "TARGET_FAST", "EMA the first tranche covers at; TARGET_SLOW the rest."),
        ("First tranche", "FIRST_TRANCHE_PCT", "Share of the position covered at the fast average, %."),
        ("Time stop", "TIME_STOP", "Sessions after which the rest is covered."),
        ("Risk per short", "RISK_PCT", "Percent of equity risked to the stop."),
        ("Position cap", "MAX_POSITION_PCT", "One short's notional, % of equity."),
        ("Borrow fee", "BORROW_PCT", "Percent a year of the short notional (base case)."),
        ("Cost per side", "COST_BPS", "Spread and slippage, basis points."),
    )


def main(argv: list[str] | None = None) -> dict | None:
    from ..paths import run_dir
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Parabolic short (Kullamägi)")
    ap.add_argument("--strategy", default="parabolic_short")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True)
    ap.add_argument("--borrow-pct", type=float, default=BORROW_PCT, help="borrow fee, %% a year")
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)
    cfg = MARKETS[a.market]

    prep = prepare(a.market)
    cands = candidates(prep, pd.Timestamp(a.start))
    tdf, eq, held, gross, costs, dropped = run(prep, a.start, a.borrow_pct, cands)
    bc = prep["bench"].reindex(eq.index).ffill()
    idx_exp = index_at_exposure(prep["bench"], gross)
    st, st_idx = _stats(eq), _stats(idx_exp)

    closed = tdf[tdf["exit_reason"] != "OPEN"] if len(tdf) else tdf
    by_tier = []
    if len(closed):
        for tier, g in closed.groupby("setup"):
            by_tier.append(f"{tier}: {len(g)} trades, win {(g['pnl'] > 0).mean() * 100:.0f}%, "
                           f"avg R {g['r_multiple'].mean():+.2f}, median R {g['r_multiple'].median():+.2f}")
        reasons = closed["exit_reason"].value_counts().to_dict()
    else:
        reasons = {}
    notes = [
        f"SHORT BOOK, borrow {a.borrow_pct:g}% a year. {len(prep['frames']):,} of {prep['n_universe']:,} "
        f"stocks ever signalled; {sum(len(v) for v in cands[0].values()):,} candidate signals on "
        f"{len(cands[0]):,} sessions. Dropped: {dropped}.",
        f"Average short exposure {gross.mean():.1f}% of equity (max {gross.max():.1f}%); "
        f"{(held > 0).mean() * 100:.0f}% of sessions hold any short.",
        f"Index at the same exposure: CAGR {st_idx['cagr']:+.2f}%, max DD {st_idx['max_dd']:.1f}% "
        f"(book: CAGR {st['cagr']:+.2f}%, max DD {st['max_dd']:.1f}%).",
        "By tier -- " + "; ".join(by_tier) if by_tier else "No closed trades.",
        f"Exit reasons: {reasons}.",
        "No interest is credited on short proceeds; locates are assumed available (see caveats).",
    ]
    perf = metrics.compute(equity=eq, positions_open=held, trades=tdf, max_open_positions=0,
                           costs_paid=costs, bench_close=bc, cash=None, notes=notes)
    perf.benchmark_name = f"{cfg.benchmark_symbol} ({cfg.benchmark_ticker})"

    name = f"{a.start}_borrow{a.borrow_pct:g}_risk{RISK_PCT:g}_{ParabolicShortStrategy.spec_id()}"
    out = run_dir(a.market, a.strategy, name)
    tdf.to_csv(out / "trades.csv", index=False)
    pd.DataFrame({"equity": eq, "positions_open": held, "gross_short_pct": gross,
                  "index_at_exposure": idx_exp * float(cfg.account_size),
                  "drawdown_pct": metrics.drawdown_series(eq) * 100}).to_csv(out / "equity.csv")

    long_dir = find_long_book(a.market, out)
    leq = (pd.read_csv(long_dir / "equity.csv", index_col=0, parse_dates=True)["equity"]
           if long_dir is not None else None)
    hv = hedge_view(eq, prep["bench"], leq)
    perf.notes.append(
        f"Hedge view (reported, not judged): in the index's {WORST_MONTHS} worst months the book averaged "
        f"{hv['worst_months_book_pct']:+.2f}% a month (index {hv['worst_months_index_pct']:+.2f}%); monthly "
        f"correlation with the index {hv['corr_index']:+.2f}"
        + (f", with {LONG_BOOK} ({long_dir.name}) {hv['corr_long_book']:+.2f}." if long_dir is not None
           else f"; no stored {LONG_BOOK} run with this stage tag."))
    pd.Series({**hv, "borrow_pct": a.borrow_pct, "index_exposure_cagr": st_idx["cagr"]}).to_csv(
        out / "hedge_view.csv")
    print()
    print(metrics.format_report(perf, cfg.currency_symbol, 0))
    try:
        from . import report as report_mod
        md = report_mod.write_report(
            out, f"{cfg.name} — Parabolic short, {a.start} onward, borrow {a.borrow_pct:g}%", perf, eq, held,
            tdf, cfg.currency_symbol, 0, bc,
            f"python3 -m swing_screener.backtesting.parabolic_short --market {a.market} --start {a.start} "
            f"--borrow-pct {a.borrow_pct:g}")
        print(f"Report -> {md}")
    except Exception as e:   # noqa: BLE001
        print(f"(markdown report not generated: {type(e).__name__}: {e})")
    if not a.no_ingest:
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return {"perf": perf, "run_dir": str(out), "trades": int(len(tdf))}


if __name__ == "__main__":
    main()
