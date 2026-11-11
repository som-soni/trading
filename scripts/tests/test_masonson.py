"""Masonson's two strategies: the synthetic 3x fund, the timing book, and the sector-rotation switches.

No database: every check runs on small hand-made series, so it says what the code does, not what the
market did.

    PYTHONPATH=. python3 -m tests.test_masonson
"""

import sys

import pandas as pd

from swing_screener.backtesting import masonson_tqqq as mt
from swing_screener.backtesting import sector_rotation as sr
from swing_screener.marketdata import asof

FAILS: list[str] = []


def check(name: str, ok: bool) -> None:
    print(("  ok    " if ok else "  FAIL  ") + name)
    if not ok:
        FAILS.append(name)


def synthetic_formula() -> None:
    idx = pd.bdate_range("2020-01-01", periods=4)
    bars = pd.DataFrame({"open": [100, 101, 99, 100], "close": [100, 102, 99, 99]}, index=idx, dtype=float)
    rate = pd.Series(0.05, index=idx)
    syn = mt.synthetic(bars, leverage=3, expense=0.0095, rate=rate)
    fee = (0.0095 + 2 * 0.05) / 252
    want = 100 * (1 + 3 * 0.02 - fee)
    check("synthetic close = 3x the index's return less expense and 2x the bill rate, /252",
          abs(syn["close"].iloc[1] - want) < 1e-9)
    check("synthetic open applies 3x the overnight gap to the previous close",
          abs(syn["open"].iloc[2] - syn["close"].iloc[1] * (1 + 3 * (99 / 102 - 1))) < 1e-9)


def next_open_fills() -> None:
    idx = pd.bdate_range("2020-01-01", periods=5)
    inst = pd.DataFrame({"open": [10, 11, 12, 13, 14], "close": [10.5, 11.5, 12.5, 13.5, 14.5]}, index=idx)
    want = pd.Series([True, False, False, False, False], index=idx)
    reason = pd.Series(["", "", "BELOW_EMA20", "", ""], index=idx)
    tdf, eq, held, _cash, _costs = mt.simulate(inst, want, reason, str(idx[0].date()), 0.0, 1000.0,
                                               pd.Series(0.0, index=idx))
    t = tdf.iloc[0]
    check("a signal on the close buys at the NEXT open", t["entry_date"] == idx[1] and t["entry_price"] == 11)
    check("an exit on the close sells at the next open", t["exit_date"] == idx[3] and t["exit_price"] == 13)
    check("equity marks the holding at the close", abs(eq.loc[idx[2]] - 1000 / 11 * 12.5) < 1e-9)


def context_end_never_extends_a_stage() -> None:
    with asof.boundary("2021-12-31", "stage-optimise-to-2021-12-31"):
        with mt._context_boundary("2030-01-01"):
            check("a context --end past the stage's end keeps the stage's end",
                  asof.end() == pd.Timestamp("2021-12-31"))
        with mt._context_boundary("2012-12-31"):
            check("an earlier context --end stops reads there and tags the run",
                  asof.end() == pd.Timestamp("2012-12-31") and asof.label() == "stage-optimise-to-2012-12-31")
    with asof.boundary(None, "stage-full"):
        with mt._context_boundary("2012-12-31"):
            check("a full-stage context run is labelled full", asof.label() == "stage-full-to-2012-12-31")


def _sectors(px: pd.DataFrame, **kw):
    orig_load, orig_cache = sr.load_sectors, sr.cache.load_cached
    sr.load_sectors = lambda market, only=None: (px, {c: c for c in px.columns})
    sr.cache.load_cached = lambda market, tkr: None
    try:
        return sr.run("us", str(px.index[sr.MIN_BARS].date()), top_n=1, lookback_days=5, rebalance="W-FRI",
                      cost_bps=0.0, **kw)
    finally:
        sr.load_sectors, sr.cache.load_cached = orig_load, orig_cache


def rank_buffer_and_ema_exit() -> None:
    n = sr.MIN_BARS + 40
    idx = pd.bdate_range("2015-01-01", periods=n)
    base = pd.Series(range(n), index=idx, dtype=float)
    # A leads, then B overtakes it narrowly for the last 20 sessions while A keeps rising: with a top 1 and no
    # buffer the book switches to B; with hold_rank 2 it keeps A (still ranked second)
    a = 100 + base * 0.5
    b = 100 + base * 0.5
    b.iloc[-20:] = b.iloc[-20:] + pd.Series(range(1, 21), index=idx[-20:], dtype=float)
    c = 100 + base * 0.1
    px = pd.DataFrame({"A": a + 0.001 * base, "B": b, "C": c})
    plain = _sectors(px)[0]
    held_last = plain.sort_values("entry_date").iloc[-1]["symbol"]
    check("without a buffer the top 1 rotates to the new leader", held_last == "B")
    buf = _sectors(px, hold_rank=2)[0]
    check("with hold_rank 2 the holding stays while it ranks second", set(buf["symbol"]) == {"A"})
    # EMA exit: A collapses mid-week -> sold at that close, before the Friday ranking
    px2 = px.copy()
    crash = idx[-8]
    px2.loc[crash:, "A"] = px2.loc[crash:, "A"] * 0.5
    px2.loc[crash:, "B"] = 100 + base.loc[crash:] * 0.1   # B never leads, so A is the holding until it breaks
    ex = _sectors(px2, ema_exit=20)[0]
    sold = ex[ex["exit_reason"] == "EXIT_RULE"]
    check("a close below the EMA sells between rankings", len(sold) == 1 and sold.iloc[0]["exit_date"] == crash)


def main() -> None:
    print("Masonson strategies")
    synthetic_formula()
    next_open_fills()
    context_end_never_extends_a_stage()
    rank_buffer_and_ema_exit()
    if FAILS:
        print(f"FAIL -- {len(FAILS)} check(s)")
        sys.exit(1)
    print("OK -- the synthetic fund, the fills and the sector switches behave as documented.")


if __name__ == "__main__":
    main()
