"""The portfolio simulator's spec mode (research/minervini-backtest-spec.md), on hand-made bars.

    PYTHONPATH=. python3 -m tests.test_minervini_exits
"""

import dataclasses

import pandas as pd

from swing_screener.backtesting.portfolio_sim import ExitPolicy, Signal, simulate
from swing_screener.config import MARKETS

CFG = dataclasses.replace(MARKETS["india"], slippage_bps=0.0, commission_per_order=0.0, risk_pct=0.01,
                          max_position_pct=1.0, account_size=1_000_000)
POLICY = ExitPolicy(mode="minervini", use_target=False)


def _frame(bars: list[tuple], sma50: float = 50.0, vol50: float = 1000.0) -> pd.DataFrame:
    """bars: (open, high, low, close[, volume]) from 2024-01-01, business days."""
    idx = pd.bdate_range("2024-01-01", periods=len(bars))
    rows = [dict(open=b[0], high=b[1], low=b[2], close=b[3], volume=b[4] if len(b) > 4 else 500.0) for b in bars]
    df = pd.DataFrame(rows, index=idx)
    df["sma50"], df["vol_sma50"], df["sma200"] = sma50, vol50, 40.0
    return df


def _signal(df, setup="MV-01", stop=95.0, pivot=100.0, **meta) -> Signal:
    m = {"order": "open", "pivot": pivot, "tight_low": stop / 0.995, "max_fill": pivot * 1.05,
         "min_open": stop / 0.995, "max_risk_pct": 0.08, "base_id": "b1", **meta}
    return Signal(date=df.index[0], symbol="X", setup=setup, entry=pivot, stop=stop, target=pivot * 2,
                  decision="TRADE - HIGH CONFIDENCE", quality=1.0, meta=m)


def _run(df, sig):
    return simulate([sig], {"X": df}, CFG, df.index[0], exit_policy=POLICY).trades[0]


def test_open_entry_and_failed_breakout():
    # signal day, entry at next open 101, close below the pivot 2 days later -> sold at the following open
    df = _frame([(99, 101, 98, 100.5), (101, 102, 100, 101), (100, 101, 99, 99.5), (99, 99.5, 98, 99), (99, 100, 98, 99)])
    t = _run(df, _signal(df))
    assert t.entry_date == df.index[1] and t.entry_price == 101
    assert t.exit_reason == "FAILED_BREAKOUT" and t.exit_date == df.index[3] and t.exit_price == 99


def test_gap_above_buy_range_is_skipped():
    df = _frame([(99, 101, 98, 100.5), (106, 107, 105, 106), (106, 107, 105, 106)])
    res = simulate([_signal(df)], {"X": df}, CFG, df.index[0], exit_policy=POLICY)
    assert not res.trades and res.skipped.get("gapped above the buy range") == 1


def test_stop_gap_fills_at_open():
    df = _frame([(99, 101, 98, 100.5), (101, 103, 100.5, 102), (103, 104, 101, 103), (90, 91, 89, 90)])
    t = _run(df, _signal(df))
    assert t.exit_reason == "STOP" and t.exit_price == 90


def test_breakeven_then_partial_then_trend_break():
    # entry 100 (open), stop 95 -> R = 5; 2R = 110 raises the stop to breakeven; 3R = 115 sells a third
    df = _frame([
        (99, 100, 98, 99.5),
        (100, 101, 99.5, 100.6),       # entry at 100
        (101, 103, 100.7, 102.5), (103, 105, 102, 104.5), (105, 106, 104, 105.5), (106, 107, 105, 106.5),
        (107, 111, 106, 110.5),        # 2R touched: stop -> ~100
        (111, 116, 110, 115.5),        # 3R touched: a third sold at 115
        (115, 116, 113, 114),
        (113, 114, 40, 45, 5000),      # far below the stop -> stopped at the breakeven stop (the open is above it)
    ])
    sig = _signal(df, pivot=99.0, stop=95.0, max_fill=99 * 1.05)
    t = _run(df, sig)
    assert t.partial_shares == t.shares // 3, (t.partial_shares, t.shares)
    assert t.exit_reason == "BREAKEVEN_STOP", t.exit_reason
    expected = (t.partial_shares * 115 + (t.shares - t.partial_shares) * t.stop) / t.shares
    assert abs(t.exit_price - expected) < 1e-6 and t.r_multiple > 0


def test_trend_break_needs_volume():
    df = _frame([(99, 101, 98, 100.5), (101, 102, 100.5, 101.5)] + [(102, 103, 101.5, 102.5)] * 6
                + [(102, 102.5, 98.5, 49, 800), (49, 50, 48.5, 49, 1200), (48, 49, 47.5, 48)], sma50=50.0)
    # close 49 < SMA50 50 on light volume (800 < 1000): held; next day on heavy volume: sold at the next open 48
    sig = _signal(df, stop=40.0, max_risk_pct=1.0)
    t = _run(df, sig)
    assert t.exit_reason == "TREND_EXIT" and t.exit_price == 48, (t.exit_reason, t.exit_price)


def test_one_entry_per_base():
    df = _frame([(99, 101, 98, 100.5), (101, 102, 100, 101), (100, 101, 99, 99.5), (99, 99.5, 98, 99), (99, 100, 98, 99),
                 (99, 101, 98, 100.5), (101, 102, 100, 101), (101, 102, 100, 101)])
    s1, s2 = _signal(df), dataclasses.replace(_signal(df), date=df.index[5])
    res = simulate([s1, s2], {"X": df}, CFG, df.index[0], exit_policy=POLICY)
    assert len(res.trades) == 1 and res.skipped.get("base already entered") == 1


def test_pnl_reconciles_with_equity():
    # with slippage and charges on, the trades' P&L must add up to the change in equity (costs counted once)
    cfg = dataclasses.replace(CFG, slippage_bps=15.0)
    df = _frame([(99, 100, 98, 99.5), (100, 101, 99.5, 100.6), (101, 103, 100.7, 102.5), (103, 105, 102, 104.5),
                 (105, 106, 104, 105.5), (106, 107, 105, 106.5), (107, 111, 106, 110.5), (111, 116, 110, 115.5),
                 (115, 116, 113, 114), (113, 114, 40, 45, 5000), (45, 46, 44, 45)])
    res = simulate([_signal(df, pivot=99.0, stop=95.0, max_fill=99 * 1.05)], {"X": df}, cfg, df.index[0],
                   exit_policy=POLICY, cost_bps=12.0)
    t = res.trades[0]
    assert t.exit_reason != "OPEN"
    change = res.equity.iloc[-1] - cfg.account_size
    assert abs(t.pnl - change) < 1e-6, (t.pnl, change)


def test_legacy_bracket_pnl_reconciles_with_equity():
    # a plain buy-stop signal (no meta) under the bracket exit: one stop-out, one target, slippage on
    cfg = dataclasses.replace(CFG, slippage_bps=10.0, commission_per_order=5.0)
    df = _frame([(99, 100, 98, 99.5), (100, 101.5, 99.8, 101), (101, 102, 100, 101.5), (101, 112, 100.5, 111),
                 (111, 112, 110, 111)])
    sig = Signal(date=df.index[0], symbol="X", setup="A", entry=101.0, stop=97.0, target=110.0,
                 decision="TRADE - HIGH CONFIDENCE", quality=1.0)
    res = simulate([sig], {"X": df}, cfg, df.index[0], exit_policy=ExitPolicy())
    t = res.trades[0]
    assert t.exit_reason == "TARGET"
    change = res.equity.iloc[-1] - cfg.account_size
    assert abs(t.pnl - change) < 1e-6, (t.pnl, change)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
