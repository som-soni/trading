"""A refresh's window never leaves a scale break behind (marketdata/splits.py, marketdata/cache.py).

TRENT.NS: a 1:2 bonus on 2026-06-04 that Yahoo adjusts only back to 1 January, so its history shows a
-33% gap on 2026-01-01. `correct` rescaled the bars before it and recorded a `rescale_before`; then the
daily refresh re-wrote its ~450-session window from the source, putting 2025-01-08 .. 2025-12-31 back on
the old scale -- a +46% break on 2025-01-08 and the gap back on 2026-01-01. The fix re-applies a recorded
correction on every write (`cache.save_cached` -> `apply_recorded`), and only to the bars still on the old
scale: from the gap back to the window's break, never the already-corrected bars before it.

The same window put a new split's break ~450 sessions back: CONCORDBIO.NS's 1:1 bonus (2026-11-04) left the
stored bars before 2025-01-10 at twice the source's re-adjusted scale. So a refresh whose fetched bars
disagree in scale with the stored ones on their latest common sessions re-fetches the full history.

Synthetic bars, plus a scratch symbol in `price_corrections` / `prices` (deleted afterwards).

    PYTHONPATH=. .venv/bin/python -m tests.test_unadjusted_splits
"""

import sys

import numpy as np
import pandas as pd

from swing_screener.marketdata import cache, db
from swing_screener.marketdata.cache import source_rescaled
from swing_screener.marketdata.splits import _rescale, apply_recorded, offscale_before

FAILS: list[str] = []
RATIO = 2 / 3                    # a 1:2 bonus: new / old price
SYM = "__SPLITTEST__.NS"
SYM2, SYM3 = "__SPLITTEST2__.NS", "__SPLITTEST3__.NS"


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def _frame(close: np.ndarray, idx) -> pd.DataFrame:
    return pd.DataFrame({"open": close, "high": close * 1.01, "low": close * 0.99, "close": close,
                         "volume": np.full(len(close), 1000.0)}, index=idx)


def _scenario(idx):
    """(adjusted truth, the source as served, the stored bars after a window re-write), gap at idx[200]."""
    rng = np.random.default_rng(7)
    truth = 3000 * np.exp(np.cumsum(rng.normal(0, 0.01, len(idx))))
    gap = 200
    source = truth.copy()
    source[:gap] = truth[:gap] / RATIO                 # the source leaves the bars before 1 January unadjusted
    window = 120                                        # the refresh re-writes from here on
    stored = truth.copy()
    stored[window:] = source[window:]
    stored = _frame(stored, idx)
    # the window's first bar opens like any day, not like a split session: 4% off the ratio (MBRX 2025-01-22)
    stored.iloc[window, stored.columns.get_loc("open")] = stored["close"].iloc[window - 1] / RATIO * 0.96
    return _frame(truth, idx), _frame(source, idx), stored, idx[gap], idx[window]


def synthetic() -> None:
    print("the old-scale bars run from the gap back to the window's break, and only those are rescaled")
    idx = pd.bdate_range("2025-01-01", periods=300)
    truth, source, stored, gap, window = _scenario(idx)

    m = offscale_before(source, gap, RATIO)
    check("as served: every bar before the gap is off-scale", m.sum() == idx.get_loc(gap), str(m.sum()))
    check("as served: rescaling restores the adjusted series",
          np.allclose(_rescale(source, m, RATIO)["close"], truth["close"]))

    m = offscale_before(stored, gap, RATIO)
    flagged = idx[m]
    check("after a window re-write: only the window's bars before the gap are flagged",
          len(flagged) and flagged[0] == window and flagged[-1] == idx[idx.get_loc(gap) - 1],
          f"{flagged[0].date() if len(flagged) else None} .. {flagged[-1].date() if len(flagged) else None}")
    fixed = _rescale(stored, m, RATIO)
    check("after a window re-write: rescaling restores the adjusted series (no double scaling)",
          np.allclose(fixed["close"], truth["close"]),
          f"max error {np.abs(fixed['close'] / truth['close'] - 1).max():.3f}")
    check("re-applying to the corrected series flags nothing", not offscale_before(fixed, gap, RATIO).any())
    check("a date outside the history flags nothing", not offscale_before(stored, "2020-01-01", RATIO).any())
    check("a window that starts after the gap (a tail) flags nothing",
          not offscale_before(stored.loc[gap:].iloc[1:], gap, RATIO).any())


def stored_round_trip() -> None:
    print("a recorded correction is re-applied on every write (cache.save_cached)")
    ref = cache.load_cached("india", "RELIANCE.NS")
    idx = ref.index[-300:]                              # real NSE sessions, so no bar is dropped as stray
    truth, source, stored, gap, window = _scenario(idx)
    try:
        db.execute_values("INSERT INTO price_corrections (market, symbol, date, kind, ratio, reason) VALUES %s",
                          [("india", SYM, gap.date(), "rescale_before", RATIO, "test")])
        check("apply_recorded corrects a window re-write",
              np.allclose(apply_recorded("india", SYM, stored)["close"], truth["close"]))
        cache.save_cached("india", SYM, source)         # a full re-fetch, gap and all
        cache.save_cached("india", SYM, stored.loc[window:])   # then a refresh re-writing its window
        got = cache.load_cached("india", SYM)
        check("the stored series matches the adjusted one after both writes",
              got is not None and len(got) == len(truth) and np.allclose(got["close"], truth["close"]),
              "" if got is None else f"max error {np.abs(got['close'].to_numpy() / truth['close'].to_numpy() - 1).max():.3f}")
        r = np.log(got["close"] / got["close"].shift()).abs().max() if got is not None else None
        check("no one-day move larger than the synthetic noise", r is not None and r < 0.1, str(r))
    finally:
        with db.get_connection().cursor() as cur:
            cur.execute("DELETE FROM price_corrections WHERE market='india' AND symbol=%s", (SYM,))
            cur.execute("DELETE FROM prices WHERE market='india' AND symbol=%s", (SYM,))


def two_records() -> None:
    print("two recorded errors in one series are both fixed, the older first (SILVERTUC.NS)")
    idx = pd.bdate_range("2022-01-03", periods=500)
    rng = np.random.default_rng(11)
    truth = _frame(500 * np.exp(np.cumsum(rng.normal(0, 0.01, len(idx)))), idx)
    year, gap = (100, 200), 400                         # a year served at a tenth; a 1:10 split left out
    src = truth.copy()
    m = np.zeros(len(idx), bool); m[year[0]:year[1]] = True
    src = _rescale(src, m, 0.1)
    src = _rescale(src, np.arange(len(idx)) < gap, 10.0)
    want = truth                                        # the adjusted series: post-split scale throughout
    try:
        db.execute_values("INSERT INTO price_corrections (market, symbol, date, kind, ratio, reason) VALUES %s",
                          [("india", SYM, idx[year[1]].date(), "rescale_before", 10.0, "test"),
                           ("india", SYM, idx[gap].date(), "rescale_before", 0.1, "test")])
        got = apply_recorded("india", SYM, src)
        check("both errors fixed: the series is continuous and on the post-split scale",
              np.allclose(got["close"], want["close"]),
              f"max error {np.abs(got['close'] / want['close'] - 1).max():.3f}")
        check("re-applying changes nothing", np.allclose(apply_recorded("india", SYM, got)["close"], got["close"]))
    finally:
        with db.get_connection().cursor() as cur:
            cur.execute("DELETE FROM price_corrections WHERE market='india' AND symbol=%s", (SYM,))


def carried_factor() -> None:
    print("the traded-price factor follows a recorded correction where Yahoo misstates or lacks the split")
    from swing_screener.backtesting.spec import split_factor_after
    acts = [("india", SYM, "2026-03-06", "split", 2.0, "yahoo"),        # SILVERTUC.NS: Yahoo records 2 ...
            ("india", SYM, "2026-03-06", "bonus", 2.0, "nse"),          # ... NSE a 1:1 bonus
            ("india", SYM, "2026-03-06", "face_split", 5.0, "nse"),     # ... and Rs 10 -> Rs 2: 10 in all
            ("india", SYM2, "2026-02-27", "face_split", 10.0, "nse"),   # an ETF's unit split: no Yahoo row
            ("india", SYM3, "2026-06-04", "split", 1.5, "yahoo")]       # Yahoo right (TRENT.NS): unchanged
    idx = pd.DatetimeIndex(["2025-06-02", "2026-02-02", "2026-03-02", "2026-07-01"])
    try:
        db.execute_values("INSERT INTO corporate_actions (market, symbol, ex_date, kind, value, source) VALUES %s", acts)
        db.execute_values("INSERT INTO price_corrections (market, symbol, date, kind, ratio, reason) VALUES %s",
                          [("india", SYM, "2026-01-01", "rescale_before", 0.1, "test"),
                           ("india", SYM, "2024-01-01", "rescale_before", 10.0, "test: not a split"),
                           ("india", SYM2, "2026-02-27", "rescale_before", 0.1, "test"),
                           ("india", SYM3, "2026-01-01", "rescale_before", 0.666667, "test")])
        k = split_factor_after("india", idx, [SYM, SYM2, SYM3])
        check("NSE's bonus x face-value split, not Yahoo's row, before the ex-date",
              k[SYM].tolist() == [10.0, 10.0, 10.0, 1.0], str(k[SYM].tolist()))
        check("an ETF's unit split with no Yahoo row", k[SYM2].tolist() == [10.0, 10.0, 1.0, 1.0], str(k[SYM2].tolist()))
        check("Yahoo's exact factor kept where it agrees", k[SYM3].tolist() == [1.5, 1.5, 1.5, 1.0], str(k[SYM3].tolist()))
    finally:
        with db.get_connection().cursor() as cur:
            for sym in (SYM, SYM2, SYM3):
                cur.execute("DELETE FROM corporate_actions WHERE market='india' AND symbol=%s", (sym,))
                cur.execute("DELETE FROM price_corrections WHERE market='india' AND symbol=%s", (sym,))


def rescale_check() -> None:
    print("a fetched window on a new scale is told from one on the stored scale")
    idx = pd.bdate_range("2025-01-01", periods=300)
    stored = _scenario(idx)[0]
    window = stored.iloc[-100:].copy()
    check("same scale: merged", not source_rescaled(stored, window))
    adj = window.copy()
    adj[["open", "high", "low", "close"]] *= 0.5        # the source re-adjusted for a 1:1 bonus
    check("re-adjusted by the source: re-fetched in full", source_rescaled(stored, adj))
    old = window.copy()
    old.iloc[:40, old.columns.get_loc("close")] /= RATIO   # a recorded correction far back in the window
    check("an old stretch the stored bars correct: merged", not source_rescaled(stored, old))
    one = window.copy()
    one.iloc[-3, one.columns.get_loc("close")] *= 10    # one stray bar among the latest sessions
    check("one stray bar among the latest: merged", not source_rescaled(stored, one))
    check("no common sessions: merged", not source_rescaled(stored.iloc[:100], window))


class _Source:
    """A source that re-adjusted its whole history by 1/2 after the stored bars were fetched."""

    def __init__(self, full: pd.DataFrame):
        self.full, self.calls = full, []

    def get_many_daily_bars(self, symbols, lookback_days, **kw):
        self.calls.append(kw.get("period"))
        return {s: self.full if kw.get("period") == "max" else self.full.iloc[-150:] for s in symbols}


def refresh_round_trip() -> None:
    print("a refresh after a split re-fetches the full history (cache.get_many_bars)")
    idx = cache.load_cached("india", "RELIANCE.NS").index[-300:]
    truth = _scenario(idx)[0]
    old_scale = _rescale(truth, np.ones(len(truth), bool), 2.0)  # stored before a 1:1 bonus
    src = _Source(truth)
    try:
        cache.save_cached("india", SYM, old_scale.iloc[:-1])
        got, failed = cache.get_many_bars(src, "india", [SYM], lookback_days=100, force=True)
        stored = cache.load_cached("india", SYM)
        check("the full history was asked for", "max" in src.calls, str(src.calls))
        check("the stored series is on the source's new scale throughout, with no break",
              stored is not None and len(stored) == len(truth) and np.allclose(stored["close"], truth["close"]),
              "" if stored is None else f"{len(stored)} bars")
    finally:
        with db.get_connection().cursor() as cur:
            cur.execute("DELETE FROM prices WHERE market='india' AND symbol=%s", (SYM,))
            cur.execute("DELETE FROM backfill_progress WHERE market='india' AND symbol=%s", (SYM,))


def main() -> int:
    synthetic()
    stored_round_trip()
    two_records()
    carried_factor()
    rescale_check()
    refresh_round_trip()
    print(f"\n{'OK — no refresh window leaves a scale break behind.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
