"""The swing-trading backtest options: the fixed-percentage trail, equal allocation, and the trend-alignment
rule's point-in-time property.

    PYTHONPATH=. python3 -m tests.test_swing_options
"""

import dataclasses

import numpy as np
import pandas as pd

from swing_screener.backtesting.portfolio_sim import ExitPolicy, Signal, simulate
from swing_screener.config import MARKETS
from swing_screener.screens import criteria as crit

CFG = dataclasses.replace(MARKETS["india"], slippage_bps=0.0, commission_per_order=0.0, risk_pct=0.01,
                          max_position_pct=0.25, account_size=1_000_000)


def _frame(bars):
    idx = pd.bdate_range("2024-01-01", periods=len(bars))
    df = pd.DataFrame([dict(open=o, high=h, low=l, close=c, volume=1000.0) for o, h, l, c in bars], index=idx)
    df["sma50"] = df["vol_sma50"] = df["sma200"] = np.nan
    return df


def _signal(df, entry=100.0, stop=90.0):
    return Signal(date=df.index[0], symbol="X", setup="S1", entry=entry, stop=stop, target=1e9,
                  decision="TRADE - HIGH CONFIDENCE", quality=1.0)


def test_trail_pct_follows_the_highest_high():
    # buy-stop at 100 fills on day 1; the high reaches 120 on day 3, so a 4% trail sits at 115.2 from day 4;
    # day 5 trades down to 114 -> sold at 115.2
    df = _frame([(98, 99, 97, 98), (99, 101, 99, 100.5), (101, 110, 100, 109), (109, 120, 108, 118),
                 (118, 119, 116, 117), (117, 117.5, 114, 115), (115, 116, 113, 114)])
    pol = ExitPolicy(mode="trail_pct", use_target=False, trail_pct=0.04)
    t = simulate([_signal(df)], {"X": df}, CFG, df.index[0], exit_policy=pol).trades[0]
    assert t.exit_reason == "STOP" and abs(t.exit_price - 120 * 0.96) < 1e-9, (t.exit_reason, t.exit_price)
    assert t.exit_date == df.index[5], t.exit_date


def test_trail_pct_never_lowers_the_initial_stop():
    # price never rises: the trail (4% under a 101 high = 96.96) is above the 90 stop, so it takes over;
    # a deep fall sells at the trail, not at 90
    df = _frame([(98, 99, 97, 98), (99, 101, 99, 100), (100, 100.5, 97, 98), (95, 96, 94, 95)])
    pol = ExitPolicy(mode="trail_pct", use_target=False, trail_pct=0.04)
    t = simulate([_signal(df)], {"X": df}, CFG, df.index[0], exit_policy=pol).trades[0]
    assert t.exit_reason == "STOP" and t.exit_price <= 101 * 0.96 + 1e-9 and t.exit_price > 90


def test_equal_allocation_ignores_the_stop_distance():
    df = _frame([(98, 99, 97, 98), (99, 101, 99, 100), (100, 101, 99, 100)])
    pol = ExitPolicy(mode="bracket", use_target=False)
    eq = simulate([_signal(df, stop=99.0)], {"X": df}, CFG, df.index[0], exit_policy=pol, equal_alloc_pct=0.20).trades[0]
    assert eq.shares == int(1_000_000 * 0.20 // 100), eq.shares          # 2,000 shares: 20% of equity at 100
    rb = simulate([_signal(df, stop=99.0)], {"X": df}, CFG, df.index[0], exit_policy=pol).trades[0]
    assert rb.shares == int(1_000_000 * 0.25 // 100), rb.shares          # risk-based: 1% / ₹1 stop, capped at 25%


def test_trend_alignment_is_point_in_time():
    rng = np.random.default_rng(3)
    idx = pd.bdate_range("2018-01-01", periods=1500)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0004, 0.015, len(idx)))), index=idx)
    full = crit.trend_alignment(close)
    for d in idx[400::23]:
        cut = crit.trend_alignment(close.loc[:d]).iloc[-1]
        assert (cut == full.loc[d]).all(), (d, cut.to_dict(), full.loc[d].to_dict())


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
