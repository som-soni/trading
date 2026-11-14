"""sector_rotation's point-in-time liquidity floor (1.3).

A fund below the floor at a rebalance date is not ranked, however strong its return; it ranks once
its traded value AS OF that date clears the floor; an index is exempt; a session with no stored row
counts as nothing traded. Synthetic prices, no database.

    PYTHONPATH=. .venv/bin/python -m tests.test_sector_rotation_liquidity
"""
from __future__ import annotations

import sys

import pandas as pd

from swing_screener.backtesting import sector_rotation as sr
from swing_screener.config import MARKETS

FAILS: list[str] = []


def check(name: str, ok: bool) -> None:
    print(("  ok    " if ok else "  FAIL  ") + name)
    if not ok:
        FAILS.append(name)


MARKET = next(iter(MARKETS))
N = sr.MIN_BARS + 120
IDX = pd.bdate_range("2015-01-01", periods=N)
BASE = pd.Series(range(N), index=IDX, dtype=float)
FLOOR = float(MARKETS[MARKET].account_size) / 1 / sr.MAX_POSITION_DAYS     # top_n = 1 below


def _bars(close: pd.Series, traded: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"close": close, "volume": traded / close})


def _run(bars: dict, **kw):
    """sr.run over synthetic series: `bars` maps ticker -> a frame of close and volume."""
    px = pd.DataFrame({t: b["close"] for t, b in bars.items()}).sort_index().ffill()
    orig_load, orig_cache = sr.load_sectors, sr.cache.load_cached
    sr.load_sectors = lambda market, only=None: (px, {c: c for c in px.columns})
    sr.cache.load_cached = lambda market, tkr: bars.get(tkr)
    try:
        return sr.run(MARKET, str(IDX[sr.MIN_BARS].date()), top_n=1, lookback_days=20, cost_bps=0.0, **kw)
    finally:
        sr.load_sectors, sr.cache.load_cached = orig_load, orig_cache


def thin_fund_not_ranked() -> None:
    # THIN has by far the best return but trades a tenth of the floor until `cut`, then 10x it.
    cut = IDX[sr.MIN_BARS + 60]
    thin_tv = pd.Series(FLOOR * 0.1, index=IDX)
    thin_tv.loc[cut:] = FLOOR * 10
    bars = {"THIN": _bars(100 + BASE * 2.0, thin_tv),
            "^IDX": _bars(100 + BASE * 0.5, pd.Series(0.0, index=IDX)),        # an index: no volume, exempt
            "LIQ": _bars(100 + BASE * 0.2, pd.Series(FLOOR * 10, index=IDX))}
    tdf, _eq, _held, _costs, _labels, rankable = _run(bars)
    before = tdf[tdf["entry_date"] < cut]
    check("a fund below the floor at a month-end is not ranked, whatever its return",
          len(before) and "THIN" not in set(before["symbol"]))
    check("an index with no traded value is exempt from the floor (it is the best of the rest)",
          "^IDX" in set(before["symbol"]))
    # the floor reads a median over LIQ_WINDOW sessions up to the date, so THIN ranks only once more than
    # half of the window lies after the cut -- point in time, never earlier
    first_ok = IDX[IDX.get_loc(cut) + sr.LIQ_WINDOW // 2]
    thin = tdf[tdf["symbol"] == "THIN"]
    check("it ranks once its traded value up to the date clears the floor",
          len(thin) and thin["entry_date"].min() >= first_ok)
    check("the rankable count excludes it before, includes it after",
          rankable[min(rankable)] == 2 and rankable[max(rankable)] == 3)


def missing_rows_count_as_nothing_traded() -> None:
    # GAPPY trades well above the floor on the days it has a row, but has a row on only one session in three
    keep = IDX[::3]
    gappy = _bars(100 + BASE * 2.0, pd.Series(FLOOR * 3, index=IDX)).loc[keep]
    bars = {"GAPPY": gappy, "LIQ": _bars(100 + BASE * 0.2, pd.Series(FLOOR * 10, index=IDX))}
    px = pd.DataFrame({t: b["close"] for t, b in bars.items()}).sort_index()
    orig = sr.cache.load_cached
    sr.cache.load_cached = lambda market, tkr: bars.get(tkr)
    try:
        tv = sr.traded_value(MARKET, px)
    finally:
        sr.cache.load_cached = orig
    check("a session with no stored row counts as zero traded value",
          tv["GAPPY"].loc[IDX[1]] == 0.0 and tv["GAPPY"].loc[IDX[0]] > 0)
    check("its median over the window is then zero, below the floor",
          tv["GAPPY"].rolling(sr.LIQ_WINDOW).median().dropna().max() == 0.0)


def main() -> None:
    print("sector_rotation liquidity floor")
    thin_fund_not_ranked()
    missing_rows_count_as_nothing_traded()
    if FAILS:
        print(f"FAIL -- {len(FAILS)} check(s)")
        sys.exit(1)
    print("all passed")


if __name__ == "__main__":
    main()
