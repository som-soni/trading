"""A de-SPAC's price history starts at its merger, not at the SPAC's listing.

Before a SPAC merges it is a shell holding cash in trust, and its shares sit at about $10 for months or
years with almost no movement. After the merger the same ticker carries the operating company, and the
stored history runs straight through: Virgin Galactic's starts in September 2017 with two years of the
SPAC flat at $10. Every rule that reads history then judges the company on the shell -- the Trend
Template's averages, a base's prior advance, the 52-week range, the young-listing allowance -- so SPCE's
textbook first base after its October 2019 listing was judged a stock in a falling trend with no advance.

`detect` finds the trust stretch from the prices alone: early in the history, at least
`TRUST_MIN_BARS` sessions trading between `TRUST_PRICE_LO` and `TRUST_PRICE_HI` dollars (the price paid
that day, not the split-adjusted close) on an ATR under `TRUST_ATR_PCT`% -- a trust share, not a stock
passing through $10. The company's history starts the session after the stretch's last such bar, which is
usually the merger's announcement, when the shares start trading on the deal. A stretch still running (a
SPAC that has not merged) is left alone.

`refresh` records each start in `spac_trust_history` and removes the trust bars from `prices` (backed up in
`prices_frozen_backup`, like frozen placeholder quotes), so every loader, indicator and strategy sees the
company's history only; `clip` keeps a later re-fetch from bringing them back (cache.save_cached). Markets
whose currency is not the dollar have no SPACs at $10 and are skipped.
"""

from __future__ import annotations

import argparse
import logging

import numpy as np
import pandas as pd

from . import db

logger = logging.getLogger(__name__)

TRUST_PRICE_LO = 9.0       # dollars: a SPAC's trust value is $10 a share, and it trades close to it
TRUST_PRICE_HI = 11.5
TRUST_ATR_PCT = 1.0        # 20-day ATR as % of the close: a trust share barely moves
TRUST_MIN_BARS = 60        # sessions of it, at least
TRUST_START_WITHIN = 150   # sessions from the history's start: a SPAC trades as one from its listing
TRUST_SCAN_BARS = 900      # how far into the history to look (the longest SPAC deadlines run about 3 years)
TRUST_DENSITY = 0.7        # share of the stretch's sessions that look like trust (rumours move a few)
TRUST_ENDED_BARS = 20      # sessions since the stretch ended: a SPAC still in trust is left alone

SCHEMA = """
CREATE TABLE IF NOT EXISTS spac_trust_history (
    market VARCHAR(16) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    history_start DATE NOT NULL,
    trust_from DATE,
    trust_bars INTEGER,
    detected_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (market, symbol)
);
"""

_starts: dict | None = None   # (market, symbol) -> history start, read once per process


def detect(daily: pd.DataFrame, factor: pd.Series | None = None) -> dict | None:
    """The trust stretch at the start of `daily` (lower-case OHLC columns), or None. `factor` turns a stored
    close into the price paid that day (backtesting.spec.split_factor_after); 1 when absent."""
    d = daily.iloc[:TRUST_SCAN_BARS + 20]
    if len(d) < TRUST_MIN_BARS + 20:
        return None
    c = d["close"].astype(float)
    tr = pd.concat([d["high"] - d["low"], (d["high"] - c.shift()).abs(), (d["low"] - c.shift()).abs()], axis=1).max(axis=1)
    atr_pct = tr.rolling(20).mean() / c * 100
    paid = c * (factor.reindex(d.index).fillna(1.0) if factor is not None else 1.0)
    trust = ((atr_pct < TRUST_ATR_PCT) & paid.between(TRUST_PRICE_LO, TRUST_PRICE_HI)).to_numpy()[:TRUST_SCAN_BARS]
    idx = np.flatnonzero(trust)
    if len(idx) < TRUST_MIN_BARS or idx[0] > TRUST_START_WITHIN:
        return None
    if len(idx) / (idx[-1] - idx[0] + 1) < TRUST_DENSITY:
        return None
    end = int(idx[-1]) + 1
    if len(daily) - end < TRUST_ENDED_BARS:
        return None
    return {"history_start": daily.index[end], "trust_from": d.index[int(idx[0])], "trust_bars": int(len(idx))}


def starts(market: str) -> dict:
    """symbol -> recorded history start, for `market`."""
    global _starts
    if _starts is None:
        with db.get_connection().cursor() as cur:
            cur.execute(SCHEMA)
            cur.execute("SELECT market, symbol, history_start FROM spac_trust_history")
            _starts = {(m, s): pd.Timestamp(d) for m, s, d in cur.fetchall()}
    return {s: d for (m, s), d in _starts.items() if m == market}


def clip(market: str, symbol: str, df: pd.DataFrame) -> pd.DataFrame:
    """`df` without the bars before `symbol`'s recorded history start (none recorded: unchanged)."""
    start = starts(market).get(symbol)
    return df if start is None or df is None or df.empty else df.loc[df.index >= start]


def refresh(market: str, apply: bool = True) -> dict:
    """Detect every symbol's trust stretch, record it, and (`apply`) remove the trust bars from `prices`."""
    from ..backtesting.spec import split_factor_after
    from ..config import MARKETS
    from . import cache, frozen
    global _starts
    if getattr(MARKETS[market], "currency_code", None) != "USD":
        return {"skipped": "no dollar SPACs in this market"}
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)
    syms = sorted(cache.cached_symbols(market))
    found = []
    for k in range(0, len(syms), 400):
        for sym, d in cache.load_many_cached(market, syms[k:k + 400]).items():
            head = d.iloc[:TRUST_SCAN_BARS + 20]
            f = split_factor_after(market, head.index, [sym])
            r = detect(d, f[sym] if sym in f.columns else None)
            if r:
                found.append((sym, r))
    db.execute_values(
        "INSERT INTO spac_trust_history (market, symbol, history_start, trust_from, trust_bars) VALUES %s "
        "ON CONFLICT (market, symbol) DO UPDATE SET history_start=EXCLUDED.history_start, "
        "trust_from=EXCLUDED.trust_from, trust_bars=EXCLUDED.trust_bars, detected_at=now()",
        [(market, s, r["history_start"].date(), r["trust_from"].date(), r["trust_bars"]) for s, r in found])
    _starts = None
    removed = touched = 0
    if apply:
        for sym, r in found:
            df = cache.load_cached(market, sym)
            if df is None:
                continue
            before = [t.date() for t in df.index[df.index < r["history_start"]]]
            if not before:
                continue
            removed += frozen.backup_and_delete(market, sym, before)
            cache.save_cached(market, sym, df.loc[df.index >= r["history_start"]])   # indicators from the merger on
            touched += 1
    return {"found": len(found), "symbols_trimmed": touched, "bars_removed": removed}


def main() -> None:
    from ..config import MARKETS
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=list(MARKETS))
    ap.add_argument("--detect-only", action="store_true", help="record the starts, remove nothing")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(refresh(a.market, apply=not a.detect_only))


if __name__ == "__main__":
    main()
