"""Completing sessions from an exchange's end-of-day file (marketdata/eod_files.py, cache.append_bars).

    PYTHONPATH=. python3 -m tests.test_eod_files
"""

import datetime as dt

import numpy as np
import pandas as pd

from swing_screener.marketdata import cache, db, derivatives, eod_files

SYM = "__EODTEST__.NS"


def test_nse_file_is_read_as_equity_bars():
    d = dt.date(2026, 10, 23)
    raw = pd.DataFrame({
        "TradDt": [d.isoformat()] * 5, "TckrSymb": ["AAA", "AAA", "BBB", "GSEC1", "CCC"],
        "SctySrs": ["BE", "EQ", "SM", "GS", "EQ"],
        "OpnPric": [10, 11, 20, 100, None], "HghPric": [12, 12, 21, 101, 5], "LwPric": [9, 10, 19, 99, 4],
        "ClsPric": [11, 11.5, 20.5, 100, 4.5], "TtlTradgVol": [5, 6, 7, 8, 9]})
    real = derivatives._download
    derivatives._download = lambda url: raw.copy()
    try:
        bars = eod_files.nse_cm_day(d, ".NS")
    finally:
        derivatives._download = real
    assert sorted(bars.index) == ["AAA.NS", "BBB.NS"], bars.index       # GS is a bond; CCC has no open
    assert bars.loc["AAA.NS", "close"] == 11.5                          # EQ wins over BE for the same stock
    assert bars.loc["BBB.NS", "volume"] == 7


def test_append_bars_keeps_stored_bars_and_computes_indicators():
    days = pd.bdate_range("2025-01-01", periods=260)
    px = pd.Series(np.linspace(100, 160, len(days)), index=days)
    hist = pd.DataFrame({"open": px, "high": px * 1.01, "low": px * 0.99, "close": px, "volume": 1000.0})
    hist.index.name = "Date"
    try:
        cache.save_cached("india", SYM, hist.iloc[:-1])
        last_stored = hist.index[-2]
        new_day = hist.index[-1]
        add = pd.DataFrame({"open": [1.0, 161.0], "high": [1.0, 163.0], "low": [1.0, 159.0], "close": [1.0, 162.0],
                            "volume": [1.0, 2000.0]}, index=pd.DatetimeIndex([last_stored, new_day], name="Date"))
        n = cache.append_bars("india", {SYM: add})
        assert n == 1, n                                                # the stored day is not written again
        got = cache.load_cached_with_indicators("india", SYM, new_day, 3)
        assert got.loc[last_stored, "close"] == px.iloc[-2]             # the provider's bar is untouched
        assert got.loc[new_day, "close"] == 162.0 and got.loc[new_day, "volume"] == 2000
        want50 = pd.concat([px.iloc[:-1], pd.Series([162.0], index=[new_day])]).rolling(50).mean().iloc[-1]
        assert abs(got.loc[new_day, "sma50"] - want50) < 1e-6, (got.loc[new_day, "sma50"], want50)
    finally:
        with db.get_connection().cursor() as cur:
            cur.execute("DELETE FROM prices WHERE market='india' AND symbol=%s", (SYM,))


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
