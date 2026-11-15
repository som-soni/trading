"""A short-side book simulator for per-stock setups -- the short counterpart of portfolio_sim's long book.

The per-symbol engine (`backtest.py`, `portfolio_sim.py`) is long-only in every layer: plan geometry, fills,
R, sizing. The two short books built so far (`stage4_shorts`, `parabolic_short`) each carry their own
simulator, wired to their own cover rules. This one is generic, so a new short setup is a signal function
plus documentation, not a third copy of the bookkeeping:

  signal   {date: [candidate, ...]}, each candidate a dict with `symbol`, `stop` (above the entry), and
           optionally `target` (below it), `setup`, `rank` (higher is taken first) and any extra fields,
           which are copied onto the trade row. The short is sold at the signal session's close.
  exits    each later session, in this order: the stop (the high reaches it: covered at the stop, or at the
           open if it gapped above); the target (the low reaches it: covered at the target, or the open if
           it gapped below); the time limit (covered at the close of session `rules.time_stop`).
  size     risk-based: shares = equity x risk_pct / (stop - entry), capped by one position's notional, by
           the gross short exposure of the whole book, and by the open risk of the whole book.
  costs    `cost_bps` a side; borrow (`borrow_pct` a year) and ordinary dividends paid while short
           (`dividend_pct` a year), charged nightly on the short's value; a special dividend or demerger
           on a stock held short is paid by the short on its ex-date (the stop moves down by it, as the
           price does). No interest is credited on short proceeds; locates are assumed available.

Every price it reads is the signal session's or later; signals must be causal (the caller's job). The
frames are `cache.load_many_cached` bars, which stop at a backtest stage's boundary (`marketdata/asof`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from ..config import MARKETS
from . import metrics


@dataclass
class ShortRules:
    risk_pct: float = 0.5            # of equity, between the entry and the stop
    max_position_pct: float = 20.0   # one short's notional, of equity
    max_open_risk_pct: float = 3.0   # all shorts' open risk together, of equity
    max_gross_pct: float = 100.0     # all shorts' notional together, of equity: no leverage
    max_positions: int = 10
    cost_bps: float = 10.0           # a side: spread and slippage
    borrow_pct: float = 1.0          # a year, of the short's value
    dividend_pct: float = 1.5        # a year, ordinary dividends a short pays
    time_stop: int = 10              # sessions after the entry; 0 = none
    min_size_frac: float = 0.25      # skip a short whose notional is under this x (equity x risk_pct)


def simulate(market: str, start: str, signals: dict, frames: dict, calendar: pd.DatetimeIndex,
             rules: ShortRules, credits=None):
    """(trades, equity, positions_open, gross short %, costs, skipped) for the short book."""
    cfg = MARKETS[market]
    side = rules.cost_bps / 10_000
    carry_day = (rules.borrow_pct + rules.dividend_pct) / 100 / 252
    cal = calendar[calendar >= pd.Timestamp(start)]
    cash = float(cfg.account_size)
    open_pos: dict = {}
    trades, eq_log, held_log, gross_log = [], [], [], []
    costs_total = 0.0
    skipped = {"already_short": 0, "slots_full": 0, "risk_budget": 0}
    last_close: dict = {}

    def cover(p, price):
        nonlocal cash, costs_total
        n = p["shares"]
        fee = n * price * side
        cash -= n * price + fee
        costs_total += fee
        p["fee"] += fee
        p["cover"] = price

    def close_trade(sym, p, d, reason):
        pnl = p["shares"] * (p["price"] - p["cover"]) - p["fee"] - p["carry"] - p["paid"]
        risk = p["shares"] * p["risk_ps"]
        trades.append({
            "symbol": sym, "direction": "short", "setup": p.get("setup", ""), "entry_date": p["date"],
            "entry_price": round(p["price"], 4), "initial_stop": round(p["stop0"], 4),
            "target": round(p["target"], 4) if p.get("target") else None,
            "exit_date": d, "exit_price": round(p["cover"], 4), "shares": round(p["shares"], 4),
            "exit_reason": reason, "pnl": round(pnl, 2), "notional": round(p["shares"] * p["price"], 2),
            "costs": round(p["fee"], 2), "carry": round(p["carry"], 2), "paid": round(p["paid"], 2),
            "holding_days": (d - p["date"]).days, "sessions": p["n"],
            "r_multiple": round(pnl / risk, 4) if risk > 0 else float("nan"),
            "mfe_r": round(p["mfe"] / p["risk_ps"], 3) if p["risk_ps"] > 0 else float("nan"),
            **p.get("extra", {}),
        })
        del open_pos[sym]

    credit_after = cal[0] - pd.Timedelta(days=1) if len(cal) else None
    for d in cal:
        # ---- a special dividend or demerger on a stock held short: the short pays it; its stop moves down
        if credits is not None:
            for s, c in credits.on(d, credit_after, open_pos).items():
                p = open_pos[s]
                cash -= c * p["shares"]
                p["paid"] += c * p["shares"]
                p["stop"] -= c
                if p.get("target"):
                    p["target"] -= c
                if s in last_close:
                    last_close[s] -= c
            credit_after = d
        # ---- exits on positions entered before today: stop, target, time
        closed_today = set()
        for s in list(open_pos):
            p = open_pos[s]
            f = frames[s]
            if d not in f.index:
                continue
            b = f.loc[d]
            p["n"] += 1
            hi, lo, cl, op = float(b["high"]), float(b["low"]), float(b["close"]), float(b["open"])
            if hi >= p["stop"]:
                cover(p, max(p["stop"], op))       # a squeeze through the stop fills at the open
                close_trade(s, p, d, "STOP")
                closed_today.add(s)
                continue
            p["mfe"] = max(p["mfe"], p["price"] - lo)
            if p.get("target") and lo <= p["target"]:
                cover(p, min(p["target"], op))     # a gap below the target fills at the open
                close_trade(s, p, d, "TARGET")
                closed_today.add(s)
            elif rules.time_stop and p["n"] >= rules.time_stop:
                cover(p, cl)
                close_trade(s, p, d, "TIME")
                closed_today.add(s)
        for s in open_pos:
            f = frames[s]
            if d in f.index:
                last_close[s] = float(f.at[d, "close"])
        # ---- entries at today's close, best-ranked first
        liab = sum(p["shares"] * last_close.get(s, p["price"]) for s, p in open_pos.items())
        equity = cash - liab
        for c in sorted(signals.get(d, []), key=lambda c: -float(c.get("rank", 0.0))):
            s = c["symbol"]
            if s in open_pos or s in closed_today:
                skipped["already_short"] += 1
                continue
            if len(open_pos) >= rules.max_positions:
                skipped["slots_full"] += 1
                continue
            o, stop = float(frames[s].at[d, "close"]), float(c["stop"])
            if not stop > o:
                continue
            open_risk = sum(p["shares"] * max(p["stop"] - last_close.get(x, p["price"]), 0) for x, p in open_pos.items())
            gross = sum(p["shares"] * last_close.get(x, p["price"]) for x, p in open_pos.items())
            budget = min(equity * rules.risk_pct / 100, equity * rules.max_open_risk_pct / 100 - open_risk)
            shares = min(budget / (stop - o), (equity * rules.max_gross_pct / 100 - gross) / o,
                         equity * rules.max_position_pct / 100 / o) if budget > 0 else 0.0
            shares = math.floor(shares)            # whole shares
            if shares <= 0 or shares * o < equity * rules.risk_pct / 100 * rules.min_size_frac:
                skipped["risk_budget"] += 1
                continue
            fee = shares * o * side
            cash += shares * o - fee
            costs_total += fee
            open_pos[s] = {"shares": shares, "price": o, "fee": fee, "date": d, "stop": stop, "stop0": stop,
                           "target": c.get("target"), "risk_ps": stop - o, "setup": c.get("setup", ""),
                           "n": 0, "carry": 0.0, "paid": 0.0, "mfe": 0.0, "cover": float("nan"),
                           "extra": {k: v for k, v in c.items() if k not in ("symbol", "stop", "target", "setup", "rank")}}
            last_close[s] = o
        # ---- the night's borrow and dividend carry
        for s, p in open_pos.items():
            ch = p["shares"] * last_close.get(s, p["price"]) * carry_day
            cash -= ch
            p["carry"] += ch
            costs_total += ch
        liab = sum(p["shares"] * last_close.get(s, p["price"]) for s, p in open_pos.items())
        val = cash - liab
        eq_log.append((d, val))
        held_log.append((d, len(open_pos)))
        gross_log.append((d, liab / val * 100 if val > 0 else float("nan")))
    if len(cal):
        for s in list(open_pos):   # valued at the last close, marked OPEN
            p = open_pos[s]
            cover(p, last_close.get(s, p["price"]))
            close_trade(s, p, cal[-1], "OPEN")
    eq = pd.Series(dict(eq_log)).sort_index()
    return (pd.DataFrame(trades), eq, pd.Series(dict(held_log)).sort_index(),
            pd.Series(dict(gross_log)).sort_index(), costs_total, skipped)


def index_at_exposure(bench: pd.Series, gross: pd.Series) -> pd.Series:
    """The index held LONG at the book's own capital use (each session's index return times the previous
    session's gross short %): what the same capital at work in the market made."""
    b = bench.reindex(gross.index).ffill()
    w = (gross.shift(1).fillna(0) / 100).clip(lower=0)
    return (1 + b.pct_change().fillna(0) * w).cumprod()


def stats(eq: pd.Series) -> dict:
    eq = eq.dropna()
    yrs = max((eq.index[-1] - eq.index[0]).days / 365.25, 1e-9)
    r = eq.pct_change().dropna()
    return {"cagr": ((eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1) * 100,
            "max_dd": float(metrics.drawdown_series(eq).min() * 100),
            "sharpe": float(r.mean() / r.std() * math.sqrt(252)) if r.std() > 0 else float("nan")}
