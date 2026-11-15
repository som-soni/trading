"""Classic trend following by channel breakouts -- the Turtle pair, traded as it was meant to be.

The claim under test (TODO, 2026-10-22/24): buy a close above the 20- or 55-day high, short a close
below the low, risk about 1% of the account with a 2 ATR stop, exit on the opposite 10- or 20-day
extreme; decades of positive expectancy on futures, a win rate near 45%, the money from a few big
trends, long flat spells. That is a hypothesis here, not a fact.

WHY NOT `donchian`. The `donchian` strategy runs the same channel idea long-only on single stocks,
and its own caveats say why that cannot test this claim: the Turtle edge was a DIVERSIFIED, LONG AND
SHORT book across asset classes, where a bond or a commodity trend pays while equities chop. This
runner trades that book: a small fixed universe of US-listed ETFs standing in for futures (equity
indices, Treasuries, metals, energy, agriculture, the dollar), both directions.

WHY ITS OWN RUNNER. The per-symbol engine (`backtest.py`, `portfolio_sim.py`) is long-only and ranks
a stock universe; `stage4_shorts` has a short-only simulator for stocks. A two-direction book on
thirteen fixed instruments needs a few dozen lines of simulation, so it is written here, and the
pieces of `stage4_shorts` that fit -- the month-end sleeve `blend`, the stats helper, finding the
stored long book of the same stage -- are imported from it rather than copied.

THE FUTURES SERIES ARE NOT USED. `index_series` holds GOLD_FUT, WTI, NATGAS and COPPER, but as
unadjusted front-month CLOSES: no high, low or open (so no ATR, no stop fill), and a roll gap every
month (WTI prints -37.63 in April 2020). A breakout system reads roll gaps as trends. India's
`derivatives_bhav` has NIFTY/BANKNIFTY futures, but no loader that builds a back-adjusted continuous
contract honouring the stage boundary, and two Indian index contracts in rupees are not a
diversified book beside a dollar one. See the caveats.

PRICES ARE NOT DIVIDEND-ADJUSTED. Stored ETF prices are split-adjusted only (SPY's price rose 3.25x
over 2013-2021, the stored S&P 500 total return 3.84x), so each instrument's distribution yield is
credited to a long and charged to a short, from ASSETS.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import MARKETS
from ..core import indicators as ind
from ..marketdata import cache, index_data
from ..strategies.base import PortfolioStrategy
from . import metrics
from .stage4_shorts import _stats, blend

logger = logging.getLogger("backtest")

#: The one market this runner backtests (the Strategy page offers only its commands): the ETF book is US-listed.
MARKET = "us"

#: (symbol, asset class, distribution yield % a year, 2013-2021 approximately). The yield is credited
#: to a long and charged to a short, because stored prices are not dividend-adjusted. Commodity and
#: currency ETFs pay (almost) nothing; their roll cost is already inside their price.
ASSETS = (
    ("SPY", "equity", 1.9), ("QQQ", "equity", 0.8), ("EFA", "equity", 2.8), ("EEM", "equity", 2.2),
    ("TLT", "bonds", 2.5), ("IEF", "bonds", 1.8),
    ("GLD", "metals", 0.0), ("SLV", "metals", 0.0),
    ("USO", "energy", 0.0), ("UNG", "energy", 0.0), ("DBC", "commodities", 0.3), ("DBA", "commodities", 0.0),
    ("UUP", "currency", 0.0),
)

# ---- the two systems: (entry channel, exit channel), in sessions. A close beyond the prior N
# sessions' extreme enters at the next open; a close beyond the prior M sessions' opposite extreme exits.
S1_ENTRY = 20
S1_EXIT = 10
S2_ENTRY = 55
S2_EXIT = 20
ATR_BARS = 20                 # the Turtles' N: a 20-session average true range
STOP_ATR = 2.0                # initial stop, in N, from the fill; it never moves (the channel exit trails)

# ---- size
RISK_PCT = 1.0                # of equity, from the fill to the 2N stop, per trade
MAX_OPEN_RISK_PCT = 10.0      # initial risk of all open positions together, % of current equity
MAX_POSITION_PCT = 50.0       # one position's notional, % of equity: a bond ETF's N is ~0.5% of price,
                              # so 1% risk would otherwise buy twice the account in IEF
MAX_GROSS_PCT = 200.0         # long plus short notional AT ENTRY: Reg T margin, not futures leverage
MIN_FILL_UNIT = 0.25          # a fill scaled below this fraction of a unit is skipped

# ---- the faithful Turtle mode (`--unit turtle`): the original unit, pyramiding and unit limits
TURTLE_UNIT_PCT = 1.0         # a unit is this % of equity per N (so the 2 N stop risks twice it)
TURTLE_PYRAMID_UNITS = 4      # units per instrument, the first included
PYRAMID_STEP_N = 0.5          # add a unit at each half N past the last fill (on a close, filled next open)
UNIT_LIMIT_GROUP = 6          # units in one asset class ("closely correlated")
UNIT_LIMIT_DIRECTION = 12     # units long, and units short

# ---- time-series momentum (`--system tsmom`), Moskowitz, Ooi and Pedersen (2012)
TSMOM_LOOKBACK = 252          # sessions of trailing return: the 12-month signal
TSMOM_VOL_PCT = 40.0          # each instrument's annualised volatility target, before dividing by their count
TSMOM_VOL_COM = 60            # centre of mass, in sessions, of the ex-ante volatility estimate

# ---- costs, explicit; COST_LEVELS scales the trading, borrow and margin costs (not the yields)
COST_BPS = 5.0                # per side: spread and slippage on a liquid ETF
BORROW_PCT = 1.0              # a year, of short notional: general collateral for these ETFs runs under it
MARGIN_RATE_PCT = 2.0         # a year, on cash borrowed when long notional exceeds the cash
COST_LEVELS = (0.5, 1.0, 2.0)

# ---- the judgement: benchmark, the long book it is blended with, the sleeve weights tried
BENCH_EQUITY_PCT = 60         # a 60/40 of the stored total-return series, rebalanced at month-ends
LONG_BOOK = "momentum_baseline"
SLEEVE_WEIGHTS = (0, 20, 30, 50)
# ---- robustness, computed inside every single-system run (written before the v1.1 runs, 2026-11-14)
ORDER_SEEDS = 10              # random first-come entry orders: the band a first-come rule would draw from
ROBUST_GROSS = (150.0, 250.0)  # the gross cap's neighbours
ROBUST_PYRAMID = 3            # the pyramid's neighbour, when pyramiding
ROBUST_NO_SHORT = ("USO", "UNG")  # energy-ETF shorts earn contango roll decay a real borrow fee gives back

# ---- the pass criteria (caveats); every run prints them evaluated
PASS_SHARPE = 0.3             # breakout: standalone Sharpe at least this
PASS_CORR_SPY = 0.3           # monthly correlation to SPY at most this
SLEEVE_PCT = 20               # breakout: the sleeve weight criterion (c) reads, beside LONG_BOOK
ROBUST_P10_SHARPE = 0.25      # the order band's 10th-percentile Sharpe at least this ...
ROBUST_MEDIAN_SHARPE = 0.3    # ... and its median at least this
ROBUST_NEIGHBOUR_SHARPE = 0.25  # each neighbour (gross, pyramid) keeps at least this Sharpe and a positive CAGR
BEST_YEAR_MAX_SHARE_PCT = 100  # the best calendar year earns less than this % of the whole gain
TSMOM_PASS_SHARPE = 0.5       # TSMOM: standalone Sharpe at least this
TSMOM_SLEEVE_PCT = 30         # TSMOM: the sleeve beside the 60/40 and beside the 200-day-filtered index
TSMOM_SLEEVE_SHARPE_GAIN = 0.05  # the 60/40 with the sleeve beats the 60/40's Sharpe by at least this
TSMOM_NEIGHBOUR_SHARPE = 0.4  # TSMOM neighbours (gross cap, no energy shorts) keep at least this Sharpe
INDEX_SMA = 200               # the filtered-index benchmark: S&P 500 TR while SPY closed above this average
TOP_SHARE_PCT = 10            # "the money comes from a few big trends": gross-profit share of the best this %
MIN_HISTORY = 300             # bars an ETF needs before the window opens


def system_params(system: str) -> tuple[int, int]:
    return {"1": (S1_ENTRY, S1_EXIT), "2": (S2_ENTRY, S2_EXIT)}[system]


def load(market: str = MARKET) -> dict:
    """{symbol: frame with OHLC, ATR, the four channels and the TSMOM inputs}, read through the bounded
    loaders."""
    if market != MARKET:
        raise SystemExit(f"{market}: the cross-asset ETF universe is US-listed; no {market} universe is defined")
    out = {}
    for sym, _cls, _y in ASSETS:
        d = cache.load_cached(market, sym)
        if d is None or len(d) < MIN_HISTORY:
            logger.warning("%s: not enough stored history, left out", sym)
            continue
        d = d[["open", "high", "low", "close"]].astype(float)
        f = d.copy()
        f["atr"] = ind.atr(d, ATR_BARS)
        for n in sorted({S1_ENTRY, S1_EXIT, S2_ENTRY, S2_EXIT}):
            f[f"hi{n}"] = d["high"].shift(1).rolling(n).max()   # the PRIOR n sessions, not today
            f[f"lo{n}"] = d["low"].shift(1).rolling(n).min()
        r = d["close"].pct_change()
        f["ret12"] = d["close"] / d["close"].shift(TSMOM_LOOKBACK) - 1
        # ex-ante volatility as Moskowitz, Ooi and Pedersen estimate it: exponentially weighted squared
        # daily returns, centre of mass TSMOM_VOL_COM sessions, annualised
        f["vol"] = np.sqrt((r ** 2).ewm(com=TSMOM_VOL_COM, min_periods=TSMOM_VOL_COM).mean() * 261)
        out[sym] = f
    return out


def _allocate(cands: list, gross_room: float, risk_room: float, unit_room: dict, seed: int | None) -> tuple:
    """Shares to fill for each of a session's candidate entries and adds, within the rooms left.

    `seed=None` is the rule (v1.1): ORDER-FREE. Every candidate is scaled by the same factor -- the
    tightest of the gross room and the risk room against the session's total demand -- after each is
    first held to its unit-limit buckets (each bucket shared pro rata among the candidates in it). No
    candidate is preferred, so the result cannot depend on the order the instruments are listed in. A
    candidate scaled below MIN_FILL_UNIT of a unit is skipped; the room it leaves is not handed on.

    A `seed` fills them one at a time in a random order instead -- the v1.0 mechanics with the list
    order shuffled. It is not a rule; it measures how much a first-come rule would move the result
    (the order band in every report).
    """
    fills, skipped = {}, 0
    if not cands:
        return fills, skipped
    if seed is None:
        scale = {}
        for c in cands:
            sc = 1.0
            for b in c["buckets"]:
                demand = sum(x["units"] for x in cands if b in x["buckets"])
                sc = min(sc, max(unit_room.get(b, math.inf), 0) / demand if demand > 0 else 1.0)
            scale[id(c)] = sc
        notional = sum(scale[id(c)] * c["shares"] * c["price"] for c in cands)
        risk = sum(scale[id(c)] * c["shares"] * c["risk_ps"] for c in cands)
        g = min(1.0, gross_room / notional if notional > 0 else 1.0, risk_room / risk if risk > 0 else 1.0)
        for c in cands:
            sh = c["shares"] * scale[id(c)] * max(g, 0.0)
            if sh * c["risk_ps"] < MIN_FILL_UNIT * c["unit_risk"]:
                skipped += 1
                continue
            fills[c["key"]] = sh
        return fills, skipped
    rooms = dict(unit_room)
    for c in np.random.default_rng(seed).permutation(len(cands)):
        c = cands[c]
        f = min(1.0, gross_room / (c["shares"] * c["price"]), risk_room / (c["shares"] * c["risk_ps"]),
                *[max(rooms.get(b, math.inf), 0) / c["units"] for b in c["buckets"]])
        sh = c["shares"] * max(f, 0.0)
        if sh * c["risk_ps"] < MIN_FILL_UNIT * c["unit_risk"]:
            skipped += 1
            continue
        fills[c["key"]] = sh
        gross_room -= sh * c["price"]
        risk_room -= sh * c["risk_ps"]
        for b in c["buckets"]:
            rooms[b] = rooms.get(b, math.inf) - c["units"] * sh / c["shares"]
    return fills, skipped


def run(frames: dict, start: str, system: str, cost_level: float = 1.0, account: float = 50_000.0,
        unit: str = "risk", pyramid: int = 1, gross_cap: float = MAX_GROSS_PCT, no_short: tuple = (),
        seed: int | None = None):
    """Simulate one breakout system. Returns (trades, equity, positions open, gross %, costs paid, skipped).

    `unit` "risk" sizes a unit to risk RISK_PCT of equity to the STOP_ATR N stop (the TODO's rule);
    "turtle" sizes it at TURTLE_UNIT_PCT of equity per N (the original rule) and applies the Turtles'
    unit limits. `pyramid` > 1 adds a unit at each PYRAMID_STEP_N N past the last fill, up to that many,
    with the stop for all units raised to STOP_ATR N from the latest fill."""
    n_in, n_out = system_params(system)
    yld = {s: y / 100 / 252 for s, _c, y in ASSETS}
    cls = {s: c for s, c, _y in ASSETS}
    side = COST_BPS * cost_level / 10_000
    borrow_day = BORROW_PCT * cost_level / 100 / 252
    margin_day = MARGIN_RATE_PCT * cost_level / 100 / 252
    cal = sorted(set().union(*[f.index[f.index >= pd.Timestamp(start)] for f in frames.values()]))
    cash = float(account)
    pos: dict = {}            # symbol -> position
    pending_in: dict = {}     # symbol -> (direction +1 / -1, N at the signal), from yesterday's close
    pending_add: dict = {}    # symbol -> N at the signal
    pending_out: set = set()
    last: dict = {}
    trades, eq_log, held_log, gross_log = [], [], [], []
    costs = 0.0
    skipped = {"too_small": 0}

    def value(sym, p):
        return p["dir"] * p["shares"] * last.get(sym, p["price"])

    def unit_shares(equity, n):
        if unit == "turtle":
            return equity * TURTLE_UNIT_PCT / 100 / n
        return equity * RISK_PCT / 100 / (STOP_ATR * n)

    def close_out(sym, d, price, reason):
        nonlocal cash, costs
        p = pos.pop(sym)
        fee = p["shares"] * price * side
        cash += p["dir"] * p["shares"] * price - fee
        costs += fee
        pnl = p["dir"] * (p["shares"] * price - p["cost"]) - fee - p["fee"] + p["carry"]
        trades.append({
            "symbol": sym, "asset_class": cls[sym], "system": f"S{system}",
            "direction": "long" if p["dir"] > 0 else "short", "setup": f"S{system}",
            "entry_date": p["date"], "entry_price": round(p["price"], 4), "initial_stop": round(p["stop0"], 4),
            "exit_date": d, "exit_price": round(price, 4), "shares": round(p["shares"], 4),
            "units": round(p["units"], 3), "adds": p["adds"] - 1,
            "exit_reason": reason, "pnl": round(pnl, 2), "notional": round(p["cost"], 2),
            "costs": round(fee + p["fee"], 2), "carry": round(p["carry"], 2),
            "holding_days": (d - p["date"]).days, "sessions": p["n"],
            "r_multiple": round(pnl / p["risk"], 4) if p["risk"] > 0 else float("nan"),
            "mfe_r": round(p["mfe"] / p["risk_ps"], 3) if p["risk_ps"] > 0 else float("nan"),
        })

    for d in cal:
        equity = cash + sum(value(s, p) for s, p in pos.items())
        # ---- at the open: exits first (a reversal frees its slot), then entries and adds, all at once
        for s in list(pending_out):
            f = frames[s]
            if s in pos and d in f.index:
                close_out(s, d, float(f.at[d, "open"]), "CHANNEL")
        pending_out = set()
        cands = []
        for s, (direction, n) in pending_in.items():
            if s in pos or d not in frames[s].index:
                continue
            o = float(frames[s].at[d, "open"])
            u = unit_shares(equity, n)
            sh = min(u, equity * MAX_POSITION_PCT / 100 / o)
            cands.append({"key": s, "kind": "new", "dir": direction, "n": n, "price": o, "shares": sh,
                          "units": sh / u, "risk_ps": STOP_ATR * n, "unit_risk": u * STOP_ATR * n,
                          "buckets": (cls[s], direction) if unit == "turtle" else ()})
        for s, n in pending_add.items():
            if s not in pos or d not in frames[s].index:
                continue
            p, o = pos[s], float(frames[s].at[d, "open"])
            u = unit_shares(equity, n)
            sh = min(u, max(equity * MAX_POSITION_PCT / 100 - p["shares"] * o, 0) / o)
            if sh <= 0:
                continue
            cands.append({"key": s, "kind": "add", "dir": p["dir"], "n": n, "price": o, "shares": sh,
                          "units": sh / u, "risk_ps": STOP_ATR * p["n0"], "unit_risk": u * STOP_ATR * p["n0"],
                          "buckets": (cls[s], p["dir"]) if unit == "turtle" else ()})
        pending_in, pending_add = {}, {}
        if cands:
            gross_room = equity * gross_cap / 100 - sum(abs(value(x, p)) for x, p in pos.items())
            # INITIAL risk, the Turtles' unit count: the stop is fixed, so risk to it measured at the last
            # close grows as a winner runs and would block new trends for being right about old ones.
            # The Turtles capped units, not risk, so the faithful mode has unit limits instead.
            risk_room = (math.inf if unit == "turtle"
                         else equity * MAX_OPEN_RISK_PCT / 100 - sum(p["risk"] for p in pos.values()))
            unit_room = {}
            if unit == "turtle":
                for c in set(cls.values()):
                    unit_room[c] = UNIT_LIMIT_GROUP - sum(p["units"] for x, p in pos.items() if cls[x] == c)
                for dd in (1, -1):
                    unit_room[dd] = UNIT_LIMIT_DIRECTION - sum(p["units"] for p in pos.values() if p["dir"] == dd)
            fills, k = _allocate(cands, gross_room, risk_room, unit_room, seed)
            skipped["too_small"] += k
            for c in cands:
                sh = fills.get(c["key"])
                if not sh:
                    continue
                s, o, direction = c["key"], c["price"], c["dir"]
                fee = sh * o * side
                cash -= direction * sh * o + fee
                costs += fee
                if c["kind"] == "new":
                    stop = o - direction * STOP_ATR * c["n"]
                    pos[s] = {"dir": direction, "shares": sh, "price": o, "cost": sh * o, "fee": fee, "date": d,
                              "stop": stop, "stop0": stop, "risk_ps": STOP_ATR * c["n"], "n0": c["n"],
                              "risk": sh * STOP_ATR * c["n"], "units": c["units"] * sh / c["shares"],
                              "adds": 1, "last_fill": o, "fill_date": d, "n": 0, "carry": 0.0, "mfe": 0.0}
                else:
                    p = pos[s]
                    p["shares"] += sh
                    p["cost"] += sh * o
                    p["fee"] += fee
                    p["risk"] += sh * c["risk_ps"]
                    p["units"] += c["units"] * sh / c["shares"]
                    p["adds"] += 1
                    p["last_fill"], p["fill_date"] = o, d
                    p["stop"] = o - direction * STOP_ATR * p["n0"]   # every unit's stop, raised to the latest
        # ---- intraday: the stop. A gap through it fills at the open.
        for s in list(pos):
            f, p = frames[s], pos[s]
            if d not in f.index:
                continue
            p["n"] += 1
            o, hi, lo = float(f.at[d, "open"]), float(f.at[d, "high"]), float(f.at[d, "low"])
            hit = lo <= p["stop"] if p["dir"] > 0 else hi >= p["stop"]
            if hit:
                gapped = o <= p["stop"] if p["dir"] > 0 else o >= p["stop"]
                close_out(s, d, o if (gapped and p["fill_date"] != d) else p["stop"], "STOP")
                continue
            p["mfe"] = max(p["mfe"], (hi - p["price"]) if p["dir"] > 0 else (p["price"] - lo))
        # ---- at the close: carry, then tomorrow's exits, adds and entries
        for s, f in frames.items():
            if d in f.index:
                last[s] = float(f.at[d, "close"])
        for s, p in pos.items():
            notional = p["shares"] * last[s]
            c = notional * yld[s] if p["dir"] > 0 else -notional * (yld[s] + borrow_day)
            cash += c
            p["carry"] += c
            if p["dir"] < 0:
                costs += notional * borrow_day   # the yield a short pays is carry, not a cost
        long_notional = sum(p["shares"] * last[s] for s, p in pos.items() if p["dir"] > 0)
        short_proceeds = sum(p["shares"] * last[s] for s, p in pos.items() if p["dir"] < 0)
        # cash below zero, not counting short proceeds (held as collateral, earning nothing), is a loan
        loan = max(-(cash - short_proceeds), 0.0) if long_notional > 0 else 0.0
        if loan:
            cash -= loan * margin_day
            costs += loan * margin_day
        for s, f in frames.items():
            if d not in f.index:
                continue
            r = f.loc[d]
            cl = float(r["close"])
            if s in pos:
                p = pos[s]
                if (p["dir"] > 0 and cl < r[f"lo{n_out}"]) or (p["dir"] < 0 and cl > r[f"hi{n_out}"]):
                    pending_out.add(s)
                else:
                    if (p["adds"] < pyramid and r["atr"] > 0
                            and p["dir"] * (cl - p["last_fill"]) >= PYRAMID_STEP_N * p["n0"]):
                        pending_add[s] = float(r["atr"])
                    continue
            if not (r["atr"] > 0):
                continue
            if cl > r[f"hi{n_in}"]:
                pending_in[s] = (1, float(r["atr"]))
            elif cl < r[f"lo{n_in}"] and s not in no_short:
                pending_in[s] = (-1, float(r["atr"]))
        # a reversal: the exit and the opposite entry both go at tomorrow's open, so the entry must not be
        # blocked by the position it replaces -- entries are allocated after `pending_out` is closed
        val = cash + sum(value(s, p) for s, p in pos.items())
        eq_log.append((d, val))
        held_log.append((d, len(pos)))
        gross_log.append((d, sum(abs(value(s, p)) for s, p in pos.items()) / val * 100 if val > 0 else np.nan))
    for s in list(pos):
        close_out(s, cal[-1], last[s], "OPEN")
    return (pd.DataFrame(trades), pd.Series(dict(eq_log)).sort_index(),
            pd.Series(dict(held_log)).sort_index(), pd.Series(dict(gross_log)).sort_index(), costs, skipped)


def run_tsmom(frames: dict, start: str, cost_level: float = 1.0, account: float = 50_000.0,
              gross_cap: float = MAX_GROSS_PCT, no_short: tuple = (), rf: pd.Series | None = None):
    """Time-series momentum as Moskowitz, Ooi and Pedersen (2012) state it, on the same ETFs.

    At each month's first open, from the prior close: each instrument is held long if its trailing
    TSMOM_LOOKBACK-session return (with its distribution yield) beat T-bills over the same span, short
    if not, at a weight of TSMOM_VOL_PCT / its ex-ante volatility / the number of instruments -- each
    contributes the same risk. Each weight is held to MAX_POSITION_PCT and the book to `gross_cap`
    (scaled down together). A "trade" is one run of one direction in one instrument, resized monthly;
    its r_multiple is P&L over its largest notional, a return, not an R."""
    yld = {s: y / 100 for s, _c, y in ASSETS}
    cls = {s: c for s, c, _y in ASSETS}
    side = COST_BPS * cost_level / 10_000
    borrow_day = BORROW_PCT * cost_level / 100 / 252
    margin_day = MARGIN_RATE_PCT * cost_level / 100 / 252
    cal = sorted(set().union(*[f.index[f.index >= pd.Timestamp(start)] for f in frames.values()]))
    rf12 = (rf.rolling(TSMOM_LOOKBACK, min_periods=20).mean() if rf is not None else None)
    cash = float(account)
    sh: dict = {s: 0.0 for s in frames}       # signed shares
    ep: dict = {}                             # symbol -> the open episode
    last: dict = {}
    trades, eq_log, held_log, gross_log = [], [], [], []
    costs = 0.0
    prev = None

    def trade(s, d, delta, price):
        nonlocal cash, costs
        fee = abs(delta) * price * side
        cash -= delta * price + fee
        costs += fee
        sh[s] += delta
        e = ep[s]
        e["flow"] -= delta * price
        e["fee"] += fee
        e["peak"] = max(e["peak"], abs(sh[s]) * price)

    def end_episode(s, d, price, reason):
        e = ep[s]
        if sh[s]:
            trade(s, d, -sh[s], price)
        pnl = e["flow"] - e["fee"] + e["carry"]
        trades.append({
            "symbol": s, "asset_class": cls[s], "system": "TSMOM", "setup": "TSMOM",
            "direction": "long" if e["dir"] > 0 else "short", "entry_date": e["date"],
            "entry_price": round(e["price"], 4), "exit_date": d, "exit_price": round(price, 4),
            "exit_reason": reason, "pnl": round(pnl, 2), "notional": round(e["peak"], 2),
            "costs": round(e["fee"], 2), "carry": round(e["carry"], 2), "holding_days": (d - e["date"]).days,
            "rebalances": e["n"], "r_multiple": round(pnl / e["peak"], 4) if e["peak"] > 0 else float("nan"),
        })
        del ep[s]

    for d in cal:
        if prev is not None and d.month != prev.month:
            equity = cash + sum(sh[s] * last.get(s, 0.0) for s in frames)
            rf_span = float(rf12.asof(prev)) if rf12 is not None and len(rf12) else 0.0
            w = {}
            for s, f in frames.items():
                if prev not in f.index or d not in f.index:
                    continue
                r = f.loc[prev]
                if not (r["vol"] > 0) or pd.isna(r["ret12"]):
                    continue
                excess = r["ret12"] + yld[s] - (rf_span if rf_span == rf_span else 0.0)
                w[s] = (1 if excess > 0 else -1) * (TSMOM_VOL_PCT / 100 / r["vol"])
            n_live = len(w)
            for s in w:
                w[s] = w[s] / n_live
                w[s] = max(min(w[s], MAX_POSITION_PCT / 100), -MAX_POSITION_PCT / 100)
                if w[s] < 0 and s in no_short:
                    w[s] = 0.0
            g = sum(abs(v) for v in w.values())
            if g > gross_cap / 100:
                w = {s: v * gross_cap / 100 / g for s, v in w.items()}
            for s, f in frames.items():
                if d not in f.index:
                    continue
                o = float(f.at[d, "open"])
                tgt = w.get(s, 0.0) * equity / o
                cur_dir = int(np.sign(sh[s]))
                if s in ep and np.sign(tgt) != cur_dir:
                    end_episode(s, d, o, "FLIP" if tgt else "FLAT")
                if tgt and s not in ep:
                    ep[s] = {"dir": int(np.sign(tgt)), "date": d, "price": o, "flow": 0.0, "fee": 0.0,
                             "carry": 0.0, "peak": 0.0, "n": 0}
                if s in ep:
                    ep[s]["n"] += 1
                    trade(s, d, tgt - sh[s], o)
        for s, f in frames.items():
            if d in f.index:
                last[s] = float(f.at[d, "close"])
        for s in ep:
            notional = abs(sh[s]) * last[s]
            c = notional * yld[s] / 252 if sh[s] > 0 else -notional * (yld[s] / 252 + borrow_day)
            cash += c
            ep[s]["carry"] += c
            if sh[s] < 0:
                costs += notional * borrow_day
        long_notional = sum(sh[s] * last[s] for s in ep if sh[s] > 0)
        short_proceeds = sum(-sh[s] * last[s] for s in ep if sh[s] < 0)
        loan = max(-(cash - short_proceeds), 0.0) if long_notional > 0 else 0.0
        if loan:
            cash -= loan * margin_day
            costs += loan * margin_day
        val = cash + sum(sh[s] * last.get(s, 0.0) for s in frames)
        eq_log.append((d, val))
        held_log.append((d, len(ep)))
        gross_log.append((d, sum(abs(sh[s]) * last.get(s, 0.0) for s in frames) / val * 100 if val > 0 else np.nan))
        prev = d
    for s in list(ep):
        end_episode(s, cal[-1], last[s], "OPEN")
    return (pd.DataFrame(trades), pd.Series(dict(eq_log)).sort_index(),
            pd.Series(dict(held_log)).sort_index(), pd.Series(dict(gross_log)).sort_index(), costs, {})


# ------------------------------------------------------------------ the measurements the claim is judged on

def trade_profile(t: pd.DataFrame) -> dict:
    """Win rate, average win and loss in R, the top-decile share of gross profit, long vs short P&L."""
    closed = t[t["exit_reason"] != "OPEN"] if len(t) else t
    if not len(closed):
        return {}
    wins, losses = closed[closed["pnl"] > 0], closed[closed["pnl"] <= 0]
    k = max(1, int(math.ceil(len(t) * TOP_SHARE_PCT / 100)))
    total = float(t["pnl"].sum())
    gross_profit = float(t.loc[t["pnl"] > 0, "pnl"].sum())
    top = float(t["pnl"].nlargest(k).sum())
    return {
        "trades": int(len(t)), "win_rate_pct": round(len(wins) / len(closed) * 100, 1),
        "avg_win_r": round(float(wins["r_multiple"].mean()), 2) if len(wins) else float("nan"),
        "avg_loss_r": round(float(losses["r_multiple"].mean()), 2) if len(losses) else float("nan"),
        "avg_r": round(float(closed["r_multiple"].mean()), 3),
        # of GROSS profit (winning trades only): a share of net P&L passes 100% whenever losers eat most of it
        "top_share_pct": round(top / gross_profit * 100, 1) if gross_profit > 0 else float("nan"),
        "top_pnl": round(top, 0), "gross_profit": round(gross_profit, 0), "total_pnl": round(total, 0),
        "long_pnl": round(float(t.loc[t["direction"] == "long", "pnl"].sum()), 0),
        "short_pnl": round(float(t.loc[t["direction"] == "short", "pnl"].sum()), 0),
    }


def sixty_forty() -> pd.Series:
    """The benchmark: 60% S&P 500 / 40% 7-10y Treasuries, both total return, month-end rebalanced."""
    eq = index_data.load("us", "SP500_TR")
    bd = index_data.load("us", "BONDS")
    idx = eq.index.intersection(bd.index)
    return blend(eq.reindex(idx), bd.reindex(idx), 100 - BENCH_EQUITY_PCT)


def monthly_corr(a: pd.Series, b: pd.Series) -> float:
    ra = a.resample("ME").last().pct_change()
    rb = b.resample("ME").last().pct_change()
    j = pd.concat([ra, rb], axis=1).dropna()
    return float(j.iloc[:, 0].corr(j.iloc[:, 1])) if len(j) > 6 else float("nan")


def sleeve_table(long_eq: pd.Series, trend_eq: pd.Series) -> tuple[pd.DataFrame, str]:
    """The long book with the trend book as a sleeve at each weight, beside the same weight in cash --
    the control: a book that is often small dilutes a drawdown by being there, hedge or not."""
    flat = pd.Series(1.0, index=trend_eq.index)
    rows = []
    for w in SLEEVE_WEIGHTS:
        for kind in (("trend",) if w == 0 else ("trend", "cash")):
            e = blend(long_eq, trend_eq if kind == "trend" else flat, w)
            st = _stats(e)
            rows.append({"sleeve_pct": w, "sleeve": "none" if w == 0 else kind,
                         "cagr_pct": round(st["cagr"], 2), "max_dd_pct": round(st["max_dd"], 2),
                         "vol_pct": round(st["vol"], 2), "sharpe": round(st["sharpe"], 3)})
    t = pd.DataFrame(rows)
    md = ["| Sleeve | CAGR | Max DD | Vol | Sharpe |", "|---|---|---|---|---|"]
    md += [f"| {r['sleeve_pct']}% {r['sleeve']} | {r['cagr_pct']:+.2f}% | {r['max_dd_pct']:.1f}% | "
           f"{r['vol_pct']:.1f}% | {r['sharpe']:.2f} |" for r in rows]
    return t, "\n".join(md)


def long_book_dir(out_dir: Path) -> Path | None:
    """The newest stored LONG_BOOK run with this run's start and stage tag and no overrides, or None.

    Named here rather than taken from `stage4_shorts.find_long_book`, which reads that module's per-market
    `LONG_BOOKS`: criterion (c) names momentum_baseline, and when the shared default moved to
    quality_momentum (stage4_shorts 1.5) v1.0's criterion moved with it under the old label."""
    tag = out_dir.name[out_dir.name.find("_stage-"):] if "_stage-" in out_dir.name else ""
    start = out_dir.name.split("_", 1)[0]
    root = out_dir.parent.parent / LONG_BOOK
    if not tag or not root.exists():
        return None

    def clean(q: Path) -> bool:
        f = q / "overrides.json"
        if not f.exists():
            return "regime-" not in q.name
        try:
            return not json.loads(f.read_text()).get("overrides")
        except Exception:   # noqa: BLE001
            return False
    runs = [q for q in root.iterdir() if q.name.endswith(tag) and q.name.startswith(start + "_")
            and (q / "equity.csv").exists() and clean(q)]
    return max(runs, key=lambda q: (q / "equity.csv").stat().st_mtime) if runs else None


def index_filter(idx: pd.DatetimeIndex) -> pd.Series:
    """The S&P 500 total return held while SPY's prior close was above its INDEX_SMA-day average, T-bills
    otherwise -- the plain index trend filter a trend book has to beat."""
    tr = index_data.load(MARKET, "SP500_TR")
    spy = cache.load_cached(MARKET, "SPY")["close"].astype(float)
    on = (spy > spy.rolling(INDEX_SMA).mean()).shift(1).reindex(tr.index).ffill().fillna(False).astype(bool)
    rf, _ = index_data.cash_rate_series(MARKET, tr.index)
    r = tr.pct_change().where(on, rf / 252).fillna(0.0)
    return (1 + r).cumprod().reindex(idx).ffill()


def best_year_share(eq: pd.Series) -> float:
    """The best calendar year's gain as % of the whole gain (inf when there is no gain)."""
    ye = eq.resample("YE").last()
    gains = ye.diff()
    gains.iloc[0] = ye.iloc[0] - eq.iloc[0]
    total = float(eq.iloc[-1] - eq.iloc[0])
    return float(gains.max() / total * 100) if total > 0 else math.inf


def sleeve_check(base: pd.Series, book: pd.Series, w: float) -> dict:
    """The base book with `w`% in `book` and in cash, month-end rebalanced, beside the base alone."""
    alone, with_book = _stats(base.dropna()), _stats(blend(base, book, w))
    with_cash = _stats(blend(base, pd.Series(1.0, index=book.index), w))
    return {"alone": alone, "book": with_book, "cash": with_cash}


def criteria(system: str, st: dict, st2: dict, corr_spy: float, sleeve: dict | None, robust: dict,
             pyramid: int) -> list[tuple[str, bool | None, str]]:
    """The pre-registered pass criterion (caveats), evaluated: [(test, passed, the figures)]. None = not
    measurable in this run (e.g. no stored long book)."""
    out = []
    if system == "tsmom":
        out.append(("(a) Sharpe >= TSMOM_PASS_SHARPE, CAGR > 0 at x1 and x2 costs",
                    st["sharpe"] >= TSMOM_PASS_SHARPE and st["cagr"] > 0 and st2["cagr"] > 0,
                    f"Sharpe {st['sharpe']:.2f}, CAGR {st['cagr']:+.2f}% / {st2['cagr']:+.2f}% at x2"))
    else:
        out.append(("(a) CAGR > 0 and Sharpe >= PASS_SHARPE", st["cagr"] > 0 and st["sharpe"] >= PASS_SHARPE,
                    f"CAGR {st['cagr']:+.2f}%, Sharpe {st['sharpe']:.2f}"))
    out.append(("(b) monthly correlation to SPY <= PASS_CORR_SPY", corr_spy <= PASS_CORR_SPY, f"{corr_spy:+.2f}"))
    if system == "tsmom":
        for key, label, gain in (("6040", "the 60/40", TSMOM_SLEEVE_SHARPE_GAIN), ("filter", "the 200-day index", 0.0)):
            sc = (sleeve or {}).get(key)
            if sc is None:
                out.append((f"({'c' if key == '6040' else 'd'}) {TSMOM_SLEEVE_PCT}% sleeve beside {label}", None, "no series"))
                continue
            ok = sc["book"]["sharpe"] >= sc["alone"]["sharpe"] + gain and sc["book"]["max_dd"] >= sc["alone"]["max_dd"]
            out.append((f"({'c' if key == '6040' else 'd'}) {TSMOM_SLEEVE_PCT}% sleeve beside {label}: Sharpe >= alone"
                        + (f" + {gain:g}" if gain else "") + ", drawdown no deeper", ok,
                        f"Sharpe {sc['book']['sharpe']:.3f} vs {sc['alone']['sharpe']:.3f}; DD {sc['book']['max_dd']:.1f}% "
                        f"vs {sc['alone']['max_dd']:.1f}%"))
    else:
        sc = (sleeve or {}).get("long")
        if sc is None:
            out.append((f"(c) {SLEEVE_PCT}% sleeve beside {LONG_BOOK}", None, "no stored long-book run"))
        else:
            ok = sc["book"]["sharpe"] >= sc["alone"]["sharpe"] and sc["book"]["max_dd"] >= sc["cash"]["max_dd"]
            out.append((f"(c) {SLEEVE_PCT}% sleeve beside {LONG_BOOK}: Sharpe >= book alone, DD no deeper than "
                        f"{SLEEVE_PCT}% cash", ok,
                        f"Sharpe {sc['book']['sharpe']:.3f} vs {sc['alone']['sharpe']:.3f}; DD {sc['book']['max_dd']:.1f}% "
                        f"vs cash {sc['cash']['max_dd']:.1f}%"))
        out.append(("(d) CAGR > 0 at x2 costs", st2["cagr"] > 0, f"{st2['cagr']:+.2f}%"))
    nb_sharpe = TSMOM_NEIGHBOUR_SHARPE if system == "tsmom" else ROBUST_NEIGHBOUR_SHARPE
    if "order" in robust:
        sh = np.array([r["sharpe"] for r in robust["order"]])
        out.append(("R1 order band: p10 Sharpe >= ROBUST_P10_SHARPE, median >= ROBUST_MEDIAN_SHARPE",
                    float(np.percentile(sh, 10)) >= ROBUST_P10_SHARPE and float(np.median(sh)) >= ROBUST_MEDIAN_SHARPE,
                    f"p10 {np.percentile(sh, 10):.2f}, median {np.median(sh):.2f}"))
    elif system == "tsmom":
        out.append(("R1 order band", True, "order-free by construction: one target weight per instrument"))
    for k, r in robust.get("neighbours", {}).items():
        if k.startswith("pyramid") and pyramid <= 1:
            continue
        out.append((f"R2 neighbour {k}: Sharpe >= {nb_sharpe:g}, CAGR > 0", r["sharpe"] >= nb_sharpe and r["cagr"] > 0,
                    f"CAGR {r['cagr']:+.2f}%, Sharpe {r['sharpe']:.2f}"))
    if "no_energy_shorts" in robust:
        r = robust["no_energy_shorts"]
        need = TSMOM_NEIGHBOUR_SHARPE if system == "tsmom" else None
        ok = r["cagr"] > 0 and (need is None or r["sharpe"] >= need)
        out.append(("R3 without USO/UNG shorts: CAGR > 0" + (f", Sharpe >= {need:g}" if need else ""), ok,
                    f"CAGR {r['cagr']:+.2f}%, Sharpe {r['sharpe']:.2f}"))
    bys = robust.get("best_year_share")
    if bys is not None:
        out.append(("R4 best year < BEST_YEAR_MAX_SHARE_PCT% of the gain", bys < BEST_YEAR_MAX_SHARE_PCT,
                    "no gain" if bys == math.inf else f"{bys:.0f}%"))
    return out


# ------------------------------------------------------------------ documentation

DOC = {
    "key": "turtle_trend",
    "name": "Cross-asset trend following (Turtle breakouts)",
    "description": (
        "Long a close above the prior {S1_ENTRY}-session high (System 1) or {S2_ENTRY}-session high "
        "(System 2), short a close below the low, across {n_assets} ETFs standing in for futures -- "
        "equity indices, Treasuries, metals, energy, agriculture, the dollar. {RISK_PCT}% of equity "
        "risked to a {STOP_ATR} N stop; out on the opposite {S1_EXIT}- or {S2_EXIT}-session extreme. Two "
        "measured alternatives: the original Turtle unit with pyramiding, and monthly time-series momentum."
    ),
    "status": (
        "RETIRED 2026-11-15 -- ALL THREE v1.1 TESTS FAIL their criteria written beforehand (owner's decision). "
        "Optimise stage (2013-2021, in-sample, US): System 2 +2.73% a year, Sharpe 0.24; faithful Turtle unit "
        "+2.05%, Sharpe 0.21; TSMOM +3.26%, Sharpe 0.35, against the 60/40's +10.8%, Sharpe 1.16. Kept as a "
        "measured negative result; not run live, no verify run spent. "
        "v1.1 FAILS IN THE OPTIMISE STAGE (2013-2021, US; runs 2128-2130, 2026-11-15); no verify run exists "
        "and none should be. RETIREMENT RECOMMENDED as a standalone strategy: the faithful mode and TSMOM both "
        "fail their criteria written beforehand (the rule set in the caveats); the owner retired it on 2026-11-15. "
        "v1.1 fixed the three bugs of the 2026-11-14 review: order-free, pro-rata fills when the gross cap "
        "binds; criterion (c) names its long book (momentum_baseline); the runner is US only. "
        "SYSTEM 2 BASELINE (risk unit): +2.73% a year, -33.8% drawdown, Sharpe 0.24, 427 trades, 32% won; fails "
        "(a) Sharpe >= {PASS_SHARPE}, the order band (p10 0.15, median 0.24), gross {ROBUST_GROSS}% at the low "
        "end (Sharpe 0.11) and the best year (116% of the gain); passes correlation to SPY (-0.01), the "
        "{SLEEVE_PCT}% sleeve (Sharpe 0.331 vs 0.313) and x2 costs (+0.16%). "
        "FAITHFUL TURTLE UNIT ({TURTLE_UNIT_PCT}% per N, pyramid to {TURTLE_PYRAMID_UNITS}): +2.05%, -53.6%, "
        "Sharpe 0.21; fails (a), the order band (p10 0.09, median 0.14), both gross neighbours, no USO/UNG "
        "shorts (-4.01%: the energy shorts carry it) and the best year (233%); only pyramiding to "
        "{ROBUST_PYRAMID} reaches Sharpe 0.31. "
        "TSMOM: +3.26%, -24.4%, Sharpe 0.35 (+1.70% at x2 costs); fails (a) Sharpe >= {TSMOM_PASS_SHARPE}, "
        "the {TSMOM_SLEEVE_PCT}% sleeve beside the 60/40 (Sharpe 1.142 vs 1.159) and beside the "
        "{INDEX_SMA}-day index (0.943 vs 0.962) although each sleeve cut drawdown (-10.7% vs -19.0%), both "
        "gross neighbours and no USO/UNG shorts (Sharpe 0.26); passes correlation (-0.01) and the best year "
        "(59%). Benchmark: the 60/40, +10.8%, -19%, Sharpe 1.16. "
        "v1.0 (optimise): System 2 +1.4%, Sharpe 0.17 -- one draw from the order band v1.1 removed."
    ),
    "thesis": (
        "Prices trend across asset classes more often than chance: a market that has broken out keeps "
        "going for months often enough that a few large winners pay for many small stopped-out losses "
        "(time-series momentum: Moskowitz, Ooi and Pedersen 2012, on 58 futures and forwards; Hurst, "
        "Ooi and Pedersen's century of trend following). The edge lives in the DIVERSIFIED, LONG AND "
        "SHORT book -- a bond, gold or dollar trend pays while equities chop or fall -- which is why it "
        "is tested here across asset classes and both directions, not on stocks (see donchian). The same "
        "paper's own form -- a monthly 12-month signal with every instrument sized to equal volatility -- "
        "is run beside the breakouts as `--system tsmom`, because it is the form the evidence is for."
    ),
    "how_it_works": (
        "The idea. Follow every big move in any of a dozen markets, in either direction, with a stop "
        "small enough that most losers cost about 1% of the account, and let the winners run until the "
        "trend reverses. Expect to lose on more than half the trades.",
        "The universe. {n_assets} US-listed ETFs: SPY, QQQ, EFA, EEM (equities), TLT, IEF (Treasuries), "
        "GLD, SLV (metals), USO, UNG (energy), DBC, DBA (broad commodities, agriculture), UUP (the "
        "dollar). Daily bars, stored, split-adjusted.",
        "Step 1 -- the breakout. After each close: a close above the highest high of the prior N "
        "sessions is a long signal, a close below the lowest low a short signal. System 1: N = "
        "{S1_ENTRY}. System 2: N = {S2_ENTRY}.",
        "Step 2 -- the trade, at the next open, sized so the {STOP_ATR} N stop from the fill risks "
        "{RISK_PCT}% of equity (N = the {ATR_BARS}-session average true range), within the caps on "
        "open risk, one position's size and gross exposure. When a session's entries together need more "
        "room than is left, every one is scaled by the same factor: no instrument goes first.",
        "The faithful Turtle mode (`--unit turtle`). A unit is {TURTLE_UNIT_PCT}% of equity per N, so its "
        "{STOP_ATR} N stop risks twice that. A close {PYRAMID_STEP_N} N past the last fill adds a unit at "
        "the next open, up to {TURTLE_PYRAMID_UNITS}, and moves every unit's stop to {STOP_ATR} N from the "
        "newest fill. At most {UNIT_LIMIT_GROUP} units in one asset class and {UNIT_LIMIT_DIRECTION} long "
        "or short.",
        "Time-series momentum (`--system tsmom`). At each month's first open, from the prior close: long "
        "each ETF whose {TSMOM_LOOKBACK}-session return (with its yield) beat T-bills, short the rest, each "
        "at {TSMOM_VOL_PCT}% / its ex-ante volatility / the number of ETFs, so each carries the same risk; "
        "held to the position and gross caps.",
        "Step 3 -- the exit: the stop, intraday; or a close beyond the opposite extreme of the prior "
        "M sessions (System 1: M = {S1_EXIT}, System 2: M = {S2_EXIT}), at the next open. A reversal "
        "exits and enters the other way on the same open.",
        "Judged three ways. Standalone against a {BENCH_EQUITY_PCT}/40 stock/bond blend; by the shape "
        "of its trades (win rate, average win and loss in R, the share of profit from the top "
        "{TOP_SHARE_PCT}% of trades, long against short); and as a sleeve beside the momentum_baseline "
        "run of the same stage, against the same weight held in cash. TSMOM is also judged as a sleeve "
        "beside the 60/40 and beside the S&P 500 held only above its {INDEX_SMA}-day average. Every run "
        "prints the pass criterion evaluated, and the robustness checks it reads.",
        "Running it. `python -m jobs enqueue backtest --market us --strategies turtle_trend --stage "
        "optimise --bt '--system 2'`; `--system` is 1, 2, both (50/50, rebalanced monthly) or tsmom; "
        "`--unit turtle` is the faithful mode (`--pyramid` sets its units), `--max-gross` the gross cap "
        "and `--no-short USO,UNG` drops shorts of the named ETFs.",
    ),
    "entry_rules": (
        "Breakout. Today's close above the highest high of the prior N sessions (long) or below the "
        "lowest low (short); today's bar is not in the channel. N = {S1_ENTRY} for System 1, "
        "{S2_ENTRY} for System 2.\n\n**Claim (TODO):** the same, on a close. Differs from the original "
        "Turtle rules: those entered intraday on the touch, added units every half N up to four, and "
        "skipped a System 1 breakout after a winning one -- none of that is here.",
        "Fill. At the next session's open. One position per instrument per system.",
        "Several fills in one session (v1.1). The session's new entries and adds are filled together: each "
        "is first held to its unit-limit buckets (shared pro rata), then all are scaled by one factor -- the "
        "tighter of the gross room and the open-risk room against their total demand. A fill scaled below "
        "{MIN_FILL_UNIT} of a unit is skipped. v1.0 filled them in the order the ETFs were listed (SPY "
        "first, UUP last), which no rule asked for and which moved CAGR by about four points.",
        "Size. Units = {RISK_PCT}% of equity / ({STOP_ATR} × N at the signal). Cut so that the initial "
        "risk of all open positions stays within {MAX_OPEN_RISK_PCT}% of equity, one position's notional within "
        "{MAX_POSITION_PCT}% and long plus short notional within {MAX_GROSS_PCT}% at entry (winners may drift "
        "above it, as Reg T maintenance margin allows). Fractional shares.\n\n"
        "**Claim:** risk about 1% with a 2 ATR stop -- the same. The position and gross caps are "
        "added: an ETF account cannot take a futures account's leverage, so a Treasury position is "
        "often capped below its 1%-risk size.",
        "Faithful unit and pyramiding (`--unit turtle`). Unit = {TURTLE_UNIT_PCT}% of equity / N at the "
        "signal. A close at least {PYRAMID_STEP_N} N (N at the first entry) past the last fill adds a unit "
        "at the next open, up to {TURTLE_PYRAMID_UNITS} units, the instrument's notional still within "
        "{MAX_POSITION_PCT}%. Unit limits replace the open-risk cap: {UNIT_LIMIT_GROUP} units per asset "
        "class, {UNIT_LIMIT_DIRECTION} per direction.\n\n**Turtle rules (Faith 2003):** the same, with "
        "adds intraday at the half-N price and a loosely-correlated limit of 10, not modelled.",
        "TSMOM (`--system tsmom`). Monthly, at the first open of the month from the prior close: direction "
        "= sign of the {TSMOM_LOOKBACK}-session price return plus the ETF's yield minus the T-bill return "
        "over the span; weight = {TSMOM_VOL_PCT}% / ex-ante volatility (exponentially weighted, centre of "
        "mass {TSMOM_VOL_COM} sessions) / the number of ETFs with a signal, each held to "
        "{MAX_POSITION_PCT}%, the book scaled to the gross cap. Rebalanced to the targets every month.\n\n"
        "**Moskowitz, Ooi and Pedersen (2012):** the same, on 58 futures and forwards.",
        "Costs (base case). {COST_BPS} bps a side; shorts pay a borrow fee of {BORROW_PCT}% a year and "
        "the ETF's distribution yield; longs are credited the yield (stored prices exclude it); cash "
        "borrowed when longs exceed it costs {MARGIN_RATE_PCT}% a year. Every run also reports "
        "{COST_LEVELS} times the trading, borrow and margin costs.",
    ),
    "exit_rules": (
        "Each session the stop is checked first, then the channel exit at the close.",
        "Stop. {STOP_ATR} N from the fill, fixed (with pyramiding: moved to {STOP_ATR} N from each new "
        "unit's fill, for every unit). The day's low (long) or high (short) through it exits at the stop, "
        "or at the open when the open is already past it.",
        "Channel exit. A close below the lowest low of the prior M sessions (long) or above the highest "
        "high (short) exits at the next open. M = {S1_EXIT} for System 1, {S2_EXIT} for System 2.\n\n"
        "**Claim:** exit on the opposite 10- or 20-day extreme -- the same, on a close.",
        "TSMOM has no stop: a position is resized every month and closed when its signal flips (FLIP) or "
        "its target is zero (FLAT).",
        "A position open when the backtest ends is closed at its last close and marked OPEN.",
    ),
    "caveats": (
        "**ETFs are not futures.** The claim is about futures; these are their nearest stored stand-ins. "
        "Equity and bond ETFs track their index closely. Commodity ETFs do not: USO, UNG, DBC and DBA "
        "hold rolling futures, and in contango each roll sells cheap and buys dear -- UNG lost most of "
        "its value to roll decay over 2013-2021 while gas prices ended near where they started. That "
        "decay is REAL COST to a long and is inside the price series; a short appears to earn it, which "
        "a real short of UNG partly gives back in a borrow fee that ran far above {BORROW_PCT}% at times. "
        "Read short P&L on USO and UNG with that in mind. An ETF account also has no futures leverage "
        "and no interest on idle collateral: no interest is credited here (T-bills averaged under 1% in "
        "2013-2021, so this costs the book well under a point a year in this window, and much more after).",
        "**Thirteen instruments, not fifty.** The published evidence is on 50-60 futures markets with "
        "low correlation; four of these thirteen are equity indices that move together, two are "
        "Treasuries, and the commodity ETFs overlap. Fewer independent bets means fewer of the big "
        "trends that pay for the losses. The futures series in `index_series` (GOLD_FUT, WTI, NATGAS, "
        "COPPER) are unadjusted front-month closes without highs or lows, with roll gaps a breakout "
        "reads as trends (WTI -37.63 in April 2020), so they are not used; India's NIFTY futures have "
        "no boundary-honouring continuous-contract loader.",
        "**Simplified Turtle rules.** No pyramiding (the originals added up to four units), no System 1 "
        "skip-after-a-winner filter, no correlated-group unit limits, close signals rather than intraday "
        "touches, and no drawdown rule (the Turtles cut their notional account 20% for each 10% drawdown). "
        "The claim as written in the TODO is what is tested; `--unit turtle` restores the unit, pyramiding, "
        "raised stops and the group and direction limits, not the filter or the drawdown rule.",
        "**Dividend yields are flat assumptions** per ETF (ASSETS), because stored prices exclude "
        "distributions; the benchmark uses the stored total-return series.",
        "**PASS CRITERION, written before the first run (2026-10-25).** Judged on the optimise stage, "
        "base cost level, per system (1, 2, both). A system passes to verify only if ALL hold: "
        "(a) standalone CAGR above zero and Sharpe at least 0.3; (b) correlation of monthly returns to "
        "SPY at most 0.3; (c) the 20% trend sleeve beside momentum_baseline has a Sharpe at least the "
        "long book's alone AND a maximum drawdown no deeper than the 20% cash sleeve; (d) CAGR still "
        "above zero at the x2 cost level. The claim's shape (win rate near 45%, most profit from the "
        "top {TOP_SHARE_PCT}% of trades) is reported, not a criterion. If more than one system passes, "
        "only the one with the higher 20% sleeve Sharpe goes to verify, once.",
        "**v1.1 CRITERION, written before the v1.1 runs (2026-11-14), for every breakout run including "
        "the faithful mode.** (a)-(d) above, with (c) read against {LONG_BOOK} -- named in this module, "
        "so a change to another strategy's default long book cannot move it -- PLUS every robustness "
        "check: R1 the {ORDER_SEEDS}-order band's 10th-percentile Sharpe at least {ROBUST_P10_SHARPE} and "
        "its median at least {ROBUST_MEDIAN_SHARPE}; R2 the gross cap at {ROBUST_GROSS}% (and, pyramiding, "
        "{ROBUST_PYRAMID} units) each keeping Sharpe at least {ROBUST_NEIGHBOUR_SHARPE} and CAGR above zero; "
        "R3 CAGR above zero without USO and UNG shorts (their gain is roll decay a real borrow fee gives "
        "back); R4 the best calendar year under {BEST_YEAR_MAX_SHARE_PCT}% of the whole gain.",
        "**TSMOM CRITERION, written before its first run (2026-11-14).** A rough in-sample pre-test made "
        "about 7% at Sharpe 0.56, so the bar is set against the two books such a result has to improve: "
        "(a) Sharpe at least {TSMOM_PASS_SHARPE} and CAGR above zero at x1 and x2 costs; (b) monthly "
        "correlation to SPY at most {PASS_CORR_SPY}; (c) the 60/40 with a {TSMOM_SLEEVE_PCT}% TSMOM "
        "sleeve has a Sharpe at least {TSMOM_SLEEVE_SHARPE_GAIN} above the 60/40's alone and a drawdown "
        "no deeper; (d) the S&P 500 held above its {INDEX_SMA}-day average with a {TSMOM_SLEEVE_PCT}% "
        "sleeve has a Sharpe no lower and a drawdown no deeper than that filter alone; R2 the gross cap at "
        "{ROBUST_GROSS}% and R3 the book without USO and UNG shorts each keep Sharpe at least "
        "{TSMOM_NEIGHBOUR_SHARPE} and CAGR above zero; R4 as above. Standalone it need not beat the "
        "60/40's return -- a diversifier is judged by what it adds -- but it must add to both books.",
        "**Retirement rule (2026-11-14).** If the faithful mode and TSMOM both fail their criteria on the "
        "optimise stage, turtle_trend is recommended for retirement as a standalone strategy; its runs stay "
        "as the record.",
    ),
}


class TurtleTrendStrategy(PortfolioStrategy):
    """The Turtle channel-breakout pair on a cross-asset ETF book, long and short."""

    key = DOC["key"]
    doc = DOC
    family = "turtle_trend"
    version = "1.1"
    changelog = (("1.1", "2026-11-14",
                  "The 2026-11-14 review's bugs. B3: a session's entries, when the gross cap binds, are filled "
                  "together and scaled pro rata instead of in ETF-list order (which moved CAGR 0.3-4.3% on order "
                  "alone); every run reports the band of ten random first-come orders. B2: criterion (c) reads "
                  "momentum_baseline, named here (stage4_shorts' shared default had moved it to quality_momentum "
                  "unseen). B1: MARKET = 'us'. Added, as modes judged by criteria written before their runs: "
                  "--unit turtle (1% per N, pyramiding to 4, raised stops, unit limits) and --system tsmom "
                  "(Moskowitz-Ooi-Pedersen time-series momentum); --max-gross and --no-short for the "
                  "robustness checks, which every run computes and prints with the criterion evaluated."),
                 ("1.0", "2026-10-25",
                  "First version: the TODO's Turtle rules (20/10 and 55/20 channel breakouts, 2N stop, 1% "
                  "risk) on 13 US-listed cross-asset ETFs, long and short, with explicit trading, borrow, "
                  "margin and yield costs at three levels, a 60/40 benchmark, and a month-end sleeve "
                  "blend against momentum_baseline in every run."),)
    name = DOC["name"]
    description = DOC["description"]
    retired = "2026-11-15"
    status = DOC["status"]
    thesis = DOC["thesis"]
    how_it_works = tuple(DOC["how_it_works"])
    caveats = tuple(DOC["caveats"])
    entry_rules = tuple(DOC["entry_rules"])
    exit_rules = tuple(DOC["exit_rules"])

    behaviour = "trend_momentum"
    selection = "time_series"
    style = "trend"
    horizon = "swing"
    runner = "turtle_trend"

    n_assets = len(ASSETS)

    param_docs = (
        ("System 1 channels", "S1_ENTRY", "Entry channel in sessions; exits on S1_EXIT."),
        ("System 2 channels", "S2_ENTRY", "Entry channel in sessions; exits on S2_EXIT."),
        ("N", "ATR_BARS", "Sessions in the average true range that sizes and stops a trade."),
        ("Stop", "STOP_ATR", "Initial stop distance, in N."),
        ("Risk per trade", "RISK_PCT", "Percent of equity from the fill to the stop."),
        ("Total open risk", "MAX_OPEN_RISK_PCT", "Initial risk of all open positions together, % of equity."),
        ("One position", "MAX_POSITION_PCT", "Largest notional of one position, % of equity."),
        ("Gross exposure", "MAX_GROSS_PCT", "Long plus short notional, % of equity."),
        ("Cost per side", "COST_BPS", "Basis points of notional per fill."),
        ("Borrow fee", "BORROW_PCT", "Percent a year of short notional."),
        ("Margin rate", "MARGIN_RATE_PCT", "Percent a year on cash borrowed for longs."),
        ("Smallest fill", "MIN_FILL_UNIT", "A scaled fill below this fraction of a unit is skipped."),
        ("Turtle unit", "TURTLE_UNIT_PCT", "--unit turtle: percent of equity per N in one unit."),
        ("Turtle pyramid", "TURTLE_PYRAMID_UNITS", "--unit turtle: units per instrument, added every PYRAMID_STEP_N N."),
        ("Unit limits", "UNIT_LIMIT_GROUP", "--unit turtle: units per asset class; UNIT_LIMIT_DIRECTION per direction."),
        ("TSMOM lookback", "TSMOM_LOOKBACK", "--system tsmom: sessions of trailing return in the signal."),
        ("TSMOM volatility", "TSMOM_VOL_PCT", "--system tsmom: each ETF's volatility target, before dividing by their count."),
        ("Order band", "ORDER_SEEDS", "Random first-come entry orders each run reports beside the order-free rule."),
    )


def _show(label: str) -> str:
    """A criterion's label with its constants' live values in place of their names."""
    return re.sub(r"\b([A-Z][A-Z0-9_]{3,})\b", lambda m: f"{globals()[m.group(1)]:g}"
                  if isinstance(globals().get(m.group(1)), (int, float)) else m.group(1), label)


def main(argv: list[str] | None = None) -> dict | None:
    from ..paths import run_dir
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Turtle trend following on a cross-asset ETF book")
    ap.add_argument("--strategy", default="turtle_trend")
    ap.add_argument("--market", default=MARKET, choices=[MARKET])
    ap.add_argument("--start", required=True)
    ap.add_argument("--system", default="2", choices=["1", "2", "both", "tsmom"])
    ap.add_argument("--unit", default="risk", choices=["risk", "turtle"],
                    help="risk: RISK_PCT to the 2N stop (the TODO's rule); turtle: TURTLE_UNIT_PCT per N")
    ap.add_argument("--pyramid", type=int, default=None,
                    help="units per instrument, the first included (default 1, or TURTLE_PYRAMID_UNITS with --unit turtle)")
    ap.add_argument("--max-gross", type=float, default=MAX_GROSS_PCT, help="gross notional cap, % of equity")
    ap.add_argument("--no-short", default="", help="comma-separated symbols never shorted, e.g. USO,UNG")
    ap.add_argument("--no-robustness", action="store_true", help="skip the in-run robustness checks")
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)
    cfg = MARKETS[a.market]
    frames = load(a.market)
    pyramid = a.pyramid if a.pyramid is not None else (TURTLE_PYRAMID_UNITS if a.unit == "turtle" else 1)
    no_short = tuple(x.strip().upper() for x in a.no_short.split(",") if x.strip())
    acct = float(cfg.account_size)
    rf = None
    if a.system == "tsmom":
        rf = index_data.cash_rate_series(MARKET, pd.DatetimeIndex(sorted(set().union(
            *[f.index for f in frames.values()]))))[0]

    def sim(level=1.0, gross=a.max_gross, ns=no_short, pyr=pyramid, seed=None, system=a.system):
        if system == "tsmom":
            return run_tsmom(frames, a.start, level, acct, gross, ns, rf)
        if system != "both":
            return run(frames, a.start, system, level, acct, a.unit, pyr, gross, ns, seed)
        # two sub-accounts, half each, put back to 50/50 at every month-end
        (t1, e1, h1, g1, c1, k1), (t2, e2, h2, g2, c2, k2) = (sim(level, gross, ns, pyr, seed, "1"),
                                                              sim(level, gross, ns, pyr, seed, "2"))
        eq = blend(e1, e2, 50) * acct
        t = pd.concat([t1, t2], ignore_index=True)
        if len(t):   # an empty concat has no columns (a short window, or every symbol under MIN_HISTORY)
            t[["pnl", "costs", "carry", "shares", "notional"]] *= 0.5   # each system ran on half the account
        return (t, eq, (h1 + h2).reindex(eq.index), ((g1 + g2) / 2).reindex(eq.index), (c1 + c2) / 2,
                {k: k1.get(k, 0) + k2.get(k, 0) for k in k1})

    runs = {lvl: sim(lvl) for lvl in COST_LEVELS}
    tdf, eq, held, gross, costs, skipped = runs[1.0]

    # ---- robustness, in this run (single system or TSMOM; "both" is a blend of two runs that each have it)
    robust: dict = {}
    rob_md = []
    if not a.no_robustness and a.system != "both":
        neighbours = {f"gross {g:g}%": sim(gross=g)[1] for g in ROBUST_GROSS}
        if pyramid > 1 and a.system != "tsmom":
            neighbours[f"pyramid {ROBUST_PYRAMID}"] = sim(pyr=ROBUST_PYRAMID)[1]
        robust["neighbours"] = {k: _stats(e) for k, e in neighbours.items()}
        robust["no_energy_shorts"] = _stats(sim(ns=tuple(sorted(set(no_short) | set(ROBUST_NO_SHORT))))[1])
        if a.system != "tsmom":
            robust["order"] = [_stats(sim(seed=k)[1]) for k in range(1, ORDER_SEEDS + 1)]
        rob_md = ["| Check | CAGR | Max DD | Sharpe |", "|---|---|---|---|"]
        if "order" in robust:
            for q in (10, 50, 90):
                rob_md.append(f"| Order band p{q} ({ORDER_SEEDS} random first-come orders) | "
                              f"{np.percentile([r['cagr'] for r in robust['order']], q):+.2f}% | "
                              f"{np.percentile([r['max_dd'] for r in robust['order']], 100 - q):.1f}% | "
                              f"{np.percentile([r['sharpe'] for r in robust['order']], q):.2f} |")
        for k, r in [*robust["neighbours"].items(), ("without USO/UNG shorts", robust["no_energy_shorts"])]:
            rob_md.append(f"| {k} | {r['cagr']:+.2f}% | {r['max_dd']:.1f}% | {r['sharpe']:.2f} |")
    robust["best_year_share"] = best_year_share(eq)

    bench = sixty_forty().reindex(eq.index).ffill()
    filt = index_filter(eq.index)
    spy = cache.load_cached(a.market, "SPY")["close"].astype(float).reindex(eq.index).ffill()
    prof = trade_profile(tdf)
    sens, sens_md = [], ["| Cost level | CAGR | Max DD | Sharpe | Avg R |", "|---|---|---|---|---|"]
    for lvl, (t, e, *_r) in runs.items():
        st_l, pr = _stats(e), trade_profile(t)
        sens.append({"level": lvl, "cagr_pct": round(st_l["cagr"], 2), "max_dd_pct": round(st_l["max_dd"], 2),
                     "sharpe": round(st_l["sharpe"], 3), "avg_r": pr.get("avg_r")})
        sens_md.append(f"| ×{lvl:g} | {st_l['cagr']:+.2f}% | {st_l['max_dd']:.1f}% | {st_l['sharpe']:.2f} | "
                       f"{pr.get('avg_r', float('nan')):+.3f} |")

    by_class = (tdf.groupby(["asset_class", "direction"])["pnl"].sum().unstack(fill_value=0).round(0)
                if len(tdf) else pd.DataFrame())
    cls_md = ["| Asset class | Long P&L | Short P&L |", "|---|---|---|"]
    for c, r in by_class.iterrows():
        cls_md.append(f"| {c} | {r.get('long', 0):,.0f} | {r.get('short', 0):,.0f} |")
    by_year = (eq.resample("YE").last().pct_change() * 100).round(1)
    by_year.iloc[0] = round((eq.resample("YE").last().iloc[0] / eq.iloc[0] - 1) * 100, 1)
    st, st2 = _stats(eq), _stats(runs[max(COST_LEVELS)][1])
    bst, fst = _stats(bench), _stats(filt.dropna())
    corr_spy = monthly_corr(eq, spy)
    corr_bench = monthly_corr(eq, bench)
    profile = {**prof, "cagr_pct": round(st["cagr"], 2), "max_dd_pct": round(st["max_dd"], 2),
               "sharpe": round(st["sharpe"], 3), "corr_spy_monthly": round(corr_spy, 3),
               "corr_6040_monthly": round(corr_bench, 3), "bench_cagr_pct": round(bst["cagr"], 2),
               "bench_max_dd_pct": round(bst["max_dd"], 2), "bench_sharpe": round(bst["sharpe"], 3),
               "filter200_cagr_pct": round(fst["cagr"], 2), "filter200_max_dd_pct": round(fst["max_dd"], 2),
               "filter200_sharpe": round(fst["sharpe"], 3), "best_year_share_pct": round(robust["best_year_share"], 1)}
    mode = ("TSMOM, monthly, volatility-scaled" if a.system == "tsmom"
            else f"system {a.system}, {a.unit} unit" + (f", pyramid to {pyramid}" if pyramid > 1 else ""))
    notes = [
        f"CROSS-ASSET TREND BOOK, {mode}: {len(frames)} ETFs, long and short, gross cap {a.max_gross:g}% at entry"
        + (f", never short {', '.join(no_short)}" if no_short else "") + ". "
        f"Benchmark: {BENCH_EQUITY_PCT}/40 S&P 500 / 7-10y Treasuries, total return, month-end rebalanced "
        f"(CAGR {bst['cagr']:+.2f}%, max DD {bst['max_dd']:.1f}%, Sharpe {bst['sharpe']:.2f}). S&P 500 TR above its "
        f"{INDEX_SMA}-day, else T-bills: CAGR {fst['cagr']:+.2f}%, max DD {fst['max_dd']:.1f}%, Sharpe {fst['sharpe']:.2f}.",
        f"Trades: {prof.get('trades', 0)}, win rate {prof.get('win_rate_pct')}%, average win "
        f"{prof.get('avg_win_r')}{'' if a.system == 'tsmom' else 'R'}, average loss {prof.get('avg_loss_r')}"
        f"{' (TSMOM: P&L over peak notional, not R)' if a.system == 'tsmom' else 'R'}; top {TOP_SHARE_PCT}% of trades "
        f"made {prof.get('top_share_pct')}% of the gross profit. Long P&L {prof.get('long_pnl', 0):,.0f}, "
        f"short P&L {prof.get('short_pnl', 0):,.0f}.",
        f"Correlation of monthly returns: {corr_spy:+.2f} to SPY, {corr_bench:+.2f} to the 60/40.",
        f"Average gross exposure {gross.mean():.0f}% of equity (max {gross.max():.0f}%); "
        f"{(held > 0).mean() * 100:.0f}% of sessions hold a position. Skipped fills: {skipped}.",
        "Cost sensitivity -- " + "; ".join(f"x{s_['level']:g}: CAGR {s_['cagr_pct']:+.2f}%, DD "
                                          f"{s_['max_dd_pct']:.1f}%" for s_ in sens),
        "By year: " + ", ".join(f"{y.year} {v:+.1f}%" for y, v in by_year.items()),
        "Stored ETF prices exclude distributions: yields are credited to longs and charged to shorts as "
        "flat per-ETF rates. Commodity ETFs' roll decay is inside their prices. No interest on idle cash.",
    ]
    perf = metrics.compute(equity=eq, positions_open=held, trades=tdf, max_open_positions=0,
                           costs_paid=costs, bench_close=bench, cash=None, notes=notes)
    perf.benchmark_name = f"{BENCH_EQUITY_PCT}/40 S&P 500 TR / Treasuries 7-10y TR"

    tag = ("tsmom" if a.system == "tsmom" else f"system{a.system}" + (
        f"_turtle-p{pyramid}" if a.unit == "turtle" else (f"_p{pyramid}" if pyramid > 1 else f"_risk{RISK_PCT:g}")))
    tag += (f"_gross{a.max_gross:g}" if a.max_gross != MAX_GROSS_PCT else "")
    tag += (f"_noshort-{'-'.join(no_short)}" if no_short else "")
    out = run_dir(a.market, a.strategy, f"{a.start}_{tag}_{TurtleTrendStrategy.spec_id()}")
    tdf.to_csv(out / "trades.csv", index=False)
    pd.DataFrame({"equity": eq, "positions_open": held, "gross_pct": gross,
                  "drawdown_pct": metrics.drawdown_series(eq) * 100}).to_csv(out / "equity.csv")
    pd.DataFrame(sens).to_csv(out / "cost_sensitivity.csv", index=False)
    extra = [("Cost sensitivity", "\n".join(sens_md)), ("P&L by asset class", "\n".join(cls_md))]
    if rob_md:
        extra.append(("Robustness (written before the run)", "\n".join(rob_md)))

    sleeve: dict = {}
    ld = long_book_dir(out)
    if ld is not None:
        leq = pd.read_csv(ld / "equity.csv", index_col=0, parse_dates=True)["equity"]
        profile["corr_long_book_monthly"] = round(monthly_corr(eq, leq), 3)
        profile["long_book"] = ld.name
        idx = leq.index.intersection(eq.index)
        sleeve["long"] = sleeve_check(leq.reindex(idx), eq.reindex(idx), SLEEVE_PCT)
        tables = []
        for lvl in (1.0, max(COST_LEVELS)):
            t, md = sleeve_table(leq, runs[lvl][1])
            t.insert(0, "cost_level", lvl)
            tables.append(t)
            extra.append((f"As a sleeve beside {LONG_BOOK} (cost x{lvl:g})",
                          f"Long book: `{ld.name}`. Monthly rebalance to the split. Correlation of monthly "
                          f"returns to it: {profile['corr_long_book_monthly']:+.2f}.\n\n{md}"))
        pd.concat(tables).to_csv(out / "sleeve_blend.csv", index=False)
    else:
        perf.notes.append(f"Sleeve test skipped: no stored {LONG_BOOK} run with this run's start and stage tag.")
    sleeve["6040"] = sleeve_check(bench, eq, TSMOM_SLEEVE_PCT)
    sleeve["filter"] = sleeve_check(filt.dropna(), eq, TSMOM_SLEEVE_PCT)

    crit = criteria(a.system, st, st2, corr_spy, sleeve, robust, pyramid)
    verdict = ("PASSES" if all(c[1] for c in crit) else
               "FAILS" if any(c[1] is False for c in crit) else "INCOMPLETE")
    crit_md = ["| Test | Result | Figures |", "|---|---|---|"]
    crit_md += [f"| {_show(lab)} | {'pass' if ok else 'n/a' if ok is None else '**fail**'} | {fig} |"
                for lab, ok, fig in crit]
    extra.insert(0, (f"Pass criterion (pre-registered): {verdict}", "\n".join(crit_md)))
    perf.notes.insert(0, f"PASS CRITERION: {verdict} -- " + "; ".join(
        f"{lab.split(' ')[0]} {'ok' if ok else 'n/a' if ok is None else 'FAIL'}" for lab, ok, _f in crit))
    pd.DataFrame([{"test": _show(lab), "passed": ok, "figures": fig} for lab, ok, fig in crit]).to_csv(
        out / "criteria.csv", index=False)
    profile["verdict"] = verdict
    pd.Series(profile).to_csv(out / "profile.csv", header=["value"])
    print()
    print(metrics.format_report(perf, cfg.currency_symbol, 0))
    for title, body in extra:
        print("\n" + title + "\n" + body)
    try:
        from . import report as report_mod
        md = report_mod.write_report(
            out, f"{cfg.name} — cross-asset trend, {mode}, {a.start} onward", perf, eq, held,
            tdf, cfg.currency_symbol, 0, bench,
            f"python3 -m swing_screener.backtesting.turtle_trend --start {a.start} --system {a.system} "
            f"--unit {a.unit} --pyramid {pyramid} --max-gross {a.max_gross:g}"
            + (f" --no-short {','.join(no_short)}" if no_short else ""), extra_sections=extra)
        print(f"Report -> {md}")
    except Exception as e:   # noqa: BLE001
        print(f"(markdown report not generated: {type(e).__name__}: {e})")
    if not a.no_ingest:
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return {"perf": perf, "run_dir": str(out), "trades": int(len(tdf))}


if __name__ == "__main__":
    main()
