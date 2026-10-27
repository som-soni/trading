"""Gather what the framework's checks read for one stock — stored data only, never a download.

  company     the Fundamentals page's build (fundamentals/company.py): statements, ratios, growth, peers,
              shareholding, estimates and the strategy views (Minervini SEPA's F2 / F8 feed check G5)
  metrics     the shared quarterly metrics (fundamentals/growth.py) — EPS / sales growth, ROE, turnarounds
  snap        the stock's row of the day's snapshot (screens/snapshot.py): trend, RS, peer group, risk
  frame       that row as a one-row DataFrame, for the built-in screens' conditions
  quality     the Quality page's score, tests and live valuation (fundamentals/quality.py assess)
  estimates   analysts' consensus and surprise history (marketdata/estimates.py summary)
"""

from __future__ import annotations

import datetime as dt

from fundamentals import company, growth
from fundamentals import quality as qual
from swing_screener.marketdata import db, financials


def _clean(v):
    return None if isinstance(v, float) and v != v else v


def _quality(market: str, symbol: str, srow: dict) -> dict | None:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT to_regclass('quality_scores') IS NOT NULL")
        if not cur.fetchone()[0]:
            return None
        cur.execute("SELECT quality_score, tests, metrics FROM quality_scores WHERE market=%s AND symbol=%s", (market, symbol))
        r = cur.fetchone()
    if not r or not r[2]:
        return None
    score, tests, m = r
    price = {k: srow.get(k) for k in ("close", "sma200", "high_252", "rsi14")} if srow.get("close") else None
    return {"score": score, "tests": tests, "metrics": m, "assess": qual.assess(m, price)}


def _metrics(market: str, symbol: str) -> dict:
    scored = company._scores(market, [symbol]).get(symbol)
    if scored:
        return scored[0]
    return growth.metrics(financials.load(market, [symbol]).get(symbol, []), financials.load_meta(market).get(symbol) or {})


def gather(market: str, symbol: str, snap=None) -> dict:
    """Everything evaluate() reads. `snap`: the day's snapshot DataFrame (the server passes its cached one)."""
    if snap is None:
        from swing_screener.screens import snapshot
        try:
            snap = snapshot.load(market)
        except Exception:  # noqa: BLE001 — no snapshot yet: the trend and risk checks read n/a
            snap = None
    frame, srow = None, {}
    if snap is not None and len(snap) and symbol in set(snap["symbol"]):
        frame = snap[snap["symbol"] == symbol].reset_index(drop=True)
        srow = {k: _clean(v) for k, v in frame.iloc[0].to_dict().items()}
    co = company.build(market, symbol, snap)
    views = {v["key"]: v.get("result") for v in co.get("views") or []}
    asof = snap.attrs.get("date") if snap is not None else None
    return {
        "market": market, "symbol": symbol, "name": co.get("name"), "bank": co.get("layout") == "bank",
        "asof": str(asof) if asof else dt.date.today().isoformat(),
        "company": co, "metrics": _metrics(market, symbol), "snap": srow, "frame": frame,
        "quality": _quality(market, symbol, srow), "estimates": co.get("estimates"), "views": views,
    }
