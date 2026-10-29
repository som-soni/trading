"""The portfolio simulator's `minervini` exit mode, on hand-made bars.

V17 is minervini 1.7's exit ladder (the written spec's), set explicitly; GUIDE is ExitPolicy's defaults,
which since 1.8 are minervini_spec's constants (the SEPA Learn guide's management).

    PYTHONPATH=. python3 -m tests.test_minervini_exits
"""

import dataclasses

import pandas as pd

from swing_screener.backtesting.portfolio_sim import ExitPolicy, Signal, simulate
from swing_screener.config import MARKETS

CFG = dataclasses.replace(MARKETS["india"], slippage_bps=0.0, commission_per_order=0.0, risk_pct=0.01,
                          max_position_pct=1.0, account_size=1_000_000)
V17 = ExitPolicy(mode="minervini", use_target=False, fail_days=5, breakeven_r=2.5, partial_r=3.0,
                 strength_ext=0.0, climax_partial=False, trend_volume=True, time_stop_days=0)
GUIDE = ExitPolicy(mode="minervini", use_target=False)
POLICY = V17


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
    # the part sold is the policy's own fraction (STRENGTH_FRAC, 0.33 since 1.22), not an exact third
    assert t.partial_shares == int(t.shares * POLICY.partial_frac), (t.partial_shares, t.shares, POLICY.partial_frac)
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


def test_policy_defaults_are_the_strategy_constants():
    """minervini_spec documents the exits; ExitPolicy is what a --spec run actually gets. The defaults
    are read from the constants, so this guards against someone re-typing a literal."""
    from swing_screener.strategies import minervini_spec as ms
    p = ExitPolicy()
    assert p.breakeven_r == ms.BREAKEVEN_R and p.fail_days == ms.FAIL_DAYS
    assert p.time_stop_days == ms.TIME_STOP_DAYS and abs(p.strength_ext - ms.STRENGTH_EXT_PCT / 100) < 1e-12
    assert p.partial_frac == ms.STRENGTH_FRAC and p.climax_partial == bool(ms.CLIMAX_IS_PARTIAL)
    assert p.trend_volume == bool(ms.TREND_EXIT_NEEDS_VOLUME)
    assert p.fail_sma20_days == ms.FAIL_SMA20_DAYS


def _guide_run(df, sig):
    return simulate([sig], {"X": df}, CFG, df.index[0], exit_policy=GUIDE).trades[0]


def test_guide_no_failed_breakout_exit():
    # the 1.7 failed-breakout frame: a close below the pivot two days in is left to the stop
    df = _frame([(99, 101, 98, 100.5), (101, 102, 100, 101), (100, 101, 99, 99.5), (99, 99.5, 98, 99), (99, 100, 98, 99)])
    t = _guide_run(df, _signal(df))
    assert t.exit_reason == "OPEN", t.exit_reason


def test_guide_sells_a_third_into_strength():
    # entry 100 (open), stop 95, R = 5; SMA50 90, so a close >= 112.5 is 25% above it
    df = _frame([
        (99, 100, 98, 99.5),
        (100, 101, 99.5, 100.6),       # entry at 100
        (101, 106, 100.7, 105.5),
        (106, 111, 105, 110.5),        # 2R touched: stop -> ~100
        (111, 114, 110, 113.0),        # close 113 >= 112.5: a third queued
        (114, 115, 113, 114.5),        # ... sold at this open, 114
        (113, 114, 40, 45, 5000),      # far below the breakeven stop
    ], sma50=90.0)
    # since 1.23 the guide also banks a part at +2R (PARTIAL_R), which this frame touches at 110 before the
    # strength close; switch that off so the frame tests the strength sale alone
    policy = dataclasses.replace(GUIDE, partial_r=0.0)
    t = simulate([_signal(df, pivot=99.0, stop=95.0, max_fill=99 * 1.05)], {"X": df}, CFG, df.index[0],
                 exit_policy=policy).trades[0]
    assert t.partial_shares == int(t.shares * policy.partial_frac), (t.partial_shares, t.shares, policy.partial_frac)
    assert t.exit_reason == "BREAKEVEN_STOP", t.exit_reason
    expected = (t.partial_shares * 114 + (t.shares - t.partial_shares) * t.stop) / t.shares
    assert abs(t.exit_price - expected) < 1e-6, (t.exit_price, expected)


def test_guide_time_stop_when_1r_never_reached():
    # entry 100, R = 5: the high stays under 105 for 15 sessions -> sold at the next open
    from swing_screener.strategies import minervini_spec as ms
    n = ms.TIME_STOP_DAYS
    df = _frame([(99, 100, 98, 99.5), (100, 101, 99.5, 100.6)] + [(100, 103, 99, 101)] * (n + 2))
    t = _guide_run(df, _signal(df, pivot=99.0, stop=95.0, max_fill=99 * 1.05))
    assert t.exit_reason == "TIME_STOP" and t.exit_date == df.index[n + 2], (t.exit_reason, t.exit_date)


def test_guide_light_volume_buy_stop_fill_is_sold():
    # a buy-stop through the pivot that fills on a close with volume 500 < 1.4 x 1000 -> out at the next open
    df = _frame([(98, 99, 97, 98.5), (99, 101, 98.5, 100.5, 500), (100, 101, 99, 100.2), (100, 101, 99, 100)])
    sig = Signal(date=df.index[0], symbol="X", setup="MV-02", entry=100.1, stop=95.0, target=200.0,
                 decision="TRADE ON TRIGGER", quality=1.0,
                 meta={"order": "stop", "pivot": 100.0, "tight_low": 95.0 / 0.995, "max_fill": 105.0,
                       "max_risk_pct": 0.10, "base_id": "b1", "cancel_close_below": 95.0 / 0.995,
                       "confirm_close_above": 100.0, "min_breakout_vol": 1.4})
    t = _guide_run(df, sig)
    assert t.entry_date == df.index[1] and t.entry_price == 100.5, (t.entry_date, t.entry_price)
    assert t.exit_reason == "LIGHT_VOLUME_BREAKOUT" and t.exit_date == df.index[2] and t.exit_price == 100


def test_guide_trend_exit_needs_no_volume():
    df = _frame([(99, 101, 98, 100.5), (101, 102, 100.5, 101.5)] + [(102, 103, 101.5, 102.5)] * 6
                + [(102, 102.5, 98.5, 49, 800), (49, 50, 48.5, 49, 1200), (48, 49, 47.5, 48)], sma50=50.0)
    # close 49 < SMA50 50 on light volume: sold at the next open, 49 (1.7 waited for volume)
    t = _guide_run(df, _signal(df, stop=40.0, max_risk_pct=1.0))
    assert t.exit_reason == "TREND_EXIT" and t.exit_date == df.index[9], (t.exit_reason, t.exit_date)


def test_guide_breakout_that_closes_below_its_20_day_is_sold():
    # EX-02b: entry 101 at the open; two days later the close 99.5 is under the 20-day (100) -> out next open
    df = _frame([(99, 101, 98, 100.5), (101, 102, 100, 101), (101, 101.5, 100.5, 101), (100.5, 101, 99, 99.5),
                 (99.4, 100, 98, 99)], sma50=90.0)
    df["sma20"] = 100.0
    t = simulate([_signal(df)], {"X": df}, CFG, df.index[0],
                 exit_policy=dataclasses.replace(GUIDE, fail_sma20_days=10)).trades[0]
    assert t.exit_reason == "FAILED_SMA20" and t.exit_date == df.index[4] and t.exit_price == 99.4, \
        (t.exit_reason, t.exit_date, t.exit_price)


def test_guide_20_day_rule_ends_after_its_window():
    # the same close under the 20-day, but only after the window's sessions: left to the other rules
    n = 10
    df = _frame([(99, 101, 98, 100.5), (101, 102, 100, 101)] + [(101, 103, 100.5, 102)] * n
                + [(101, 101.5, 99, 99.5), (99.5, 100, 99, 99.6)], sma50=90.0)
    df["sma20"] = 100.0
    t = simulate([_signal(df)], {"X": df}, CFG, df.index[0],
                 exit_policy=dataclasses.replace(GUIDE, time_stop_days=0, fail_sma20_days=n)).trades[0]
    assert t.exit_reason == "OPEN", t.exit_reason


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
