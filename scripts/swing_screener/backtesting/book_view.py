"""A book as its Portfolio tab reads it: what you own, valued at the latest stored closes.

The ledger (ledger.py) is the source of truth for what a book holds; the strategy's ranking is only the
source of recommendations, and nothing here reads it. Each position carries its shares, average cost,
the latest close, value, money invested and unrealised P&L; the book carries its cash, realised P&L,
costs paid, and two figures read from its value each session since the first ledger row (the same
`paper.equity_curve` the paper books use):

    return_pct      time-weighted: each session's change in value after the money you put in or took
                    out that session (CASH rows, and OPEN rows at that session's close), chained -- so a
                    deposit is not a gain and a withdrawal is not a loss
    drawdown_pct    that chained value against its own peak, now; max_drawdown_pct the worst since

Stored closes only (no broker quote), so a value is as of the latest stored session.
"""

from __future__ import annotations

import math

import pandas as pd

from . import ledger
from .ledger import EPS


def flows(trades: list[dict], closes: pd.DataFrame) -> pd.Series:
    """Money into (+) or out of (-) the book each session: CASH rows, and OPEN rows -- shares brought in
    from outside -- at that session's close. A BUY or SELL moves money inside the book, so it is no flow."""
    out = pd.Series(0.0, index=closes.index)
    for t in trades:
        on = closes.index[closes.index >= pd.Timestamp(t["trade_date"])]
        if not len(on):
            continue
        d = on[0]
        if t["side"] == "CASH":
            out[d] += float(t.get("amount") or 0)
        elif t["side"] == "OPEN":
            px = t.get("price")
            if px is None and t["symbol"] in closes.columns:
                px = closes[t["symbol"]].ffill().get(d)
            out[d] += float(t["shares"]) * float(px or 0)
    return out


def chained(equity: pd.Series, flow: pd.Series) -> pd.Series:
    """The book's value index, 1.0 at the start, with each session's flows taken out of its return."""
    if equity.empty:
        return equity
    idx = [1.0]
    for prev, now, f in zip(equity.iloc[:-1], equity.iloc[1:], flow.iloc[1:]):
        r = (now - f) / prev - 1 if prev > EPS else 0.0
        idx.append(idx[-1] * (1 + r))
    return pd.Series(idx, index=equity.index)


def valuation(book: str, market: str) -> dict:
    from . import paper
    rows = ledger.trades(book, market)
    h = ledger.holdings(rows)
    out = {"book": book, "market": market, "positions": [], "cash": h["cash"], "realised": h["realised"],
           "costs": h["costs"], "trades": len(rows), "as_of": None, "value": h["cash"], "invested": 0.0,
           "unrealised": 0.0, "contributed": 0.0, "return_pct": None, "drawdown_pct": None,
           "max_drawdown_pct": None, "first_trade": rows[0]["trade_date"] if rows else None}
    if not rows:
        return out
    sess = paper.sessions(market)
    idx = sess[sess >= pd.Timestamp(rows[0]["trade_date"])]
    syms = sorted({t["symbol"] for t in rows if t["symbol"]})
    got = {s: paper.bars(market, s) for s in syms}
    full = pd.DataFrame({s: d["close"] for s, d in got.items() if d is not None})
    # a book of cash alone still has a value each session (equity_curve reads an empty frame as no sessions)
    closes = (full.reindex(full.index.union(idx)).ffill().reindex(idx) if not full.empty
              else pd.DataFrame({"": 0.0}, index=idx))
    last_close = {s: (float(d["close"].dropna().iloc[-1]), d["close"].dropna().index[-1].date().isoformat())
                  for s, d in got.items() if d is not None and d["close"].notna().any()}

    value_held = invested = unreal = 0.0
    pos = []
    for s, n in h["positions"].items():
        px, on = last_close.get(s, (None, None))
        avg = h["avg_cost"].get(s)
        val = n * px if px is not None else None
        inv = n * avg if avg is not None else None
        pnl = val - inv if val is not None and inv is not None else None
        value_held += val or 0.0
        invested += inv or 0.0
        unreal += pnl or 0.0
        pos.append({"symbol": s, "shares": n, "avg_cost": avg, "since": h["since"].get(s), "close": px,
                    "close_date": on, "value": val, "invested": inv, "pnl": pnl,
                    "pnl_pct": (pnl / inv * 100) if pnl is not None and inv else None})
    total = h["cash"] + value_held
    for p in pos:
        p["weight_pct"] = (p["value"] / total * 100) if p["value"] is not None and total > EPS else None
    out.update(positions=pos, value=total, invested=invested, unrealised=unreal,
               unpriced=[p["symbol"] for p in pos if p["close"] is None])
    if len(idx):
        eq = paper.equity_curve(rows, closes)
        fl = flows(rows, closes)
        ix = chained(eq, fl)
        dd = ix / ix.cummax() - 1
        out.update(as_of=idx[-1].date().isoformat(), contributed=float(fl.sum()),
                   return_pct=round((float(ix.iloc[-1]) - 1) * 100, 2),
                   drawdown_pct=round(float(dd.iloc[-1]) * 100, 2),
                   max_drawdown_pct=round(float(dd.min()) * 100, 2) if not math.isnan(dd.min()) else None)
    return out
