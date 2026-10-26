"""The shared exit modes' opt-in trade management (ExitPolicy.be_r / time_stop_* / partial_at_target),
on hand-made bars.

    PYTHONPATH=. python3 -m tests.test_trade_management
"""

import dataclasses

import pandas as pd

from swing_screener.backtesting.portfolio_sim import ExitPolicy, Signal, simulate, weekly_line
from swing_screener.config import MARKETS
from swing_screener.core import indicators as ind

CFG = dataclasses.replace(MARKETS["india"], slippage_bps=0.0, commission_per_order=0.0, risk_pct=0.01,
                          max_position_pct=1.0, account_size=1_000_000)


def _frame(bars: list[tuple], atr: float = 2.0) -> pd.DataFrame:
    """bars: (open, high, low, close) from 2024-01-01, business days."""
    idx = pd.bdate_range("2024-01-01", periods=len(bars))
    df = pd.DataFrame([dict(open=b[0], high=b[1], low=b[2], close=b[3], volume=1000.0) for b in bars], index=idx)
    df["atr14"], df["sma50"] = atr, 50.0
    return df


def _signal(df, entry=100.0, stop=95.0, target=115.0, **meta) -> Signal:
    # a resting buy-stop at 100, placed on bar 0; R = 5, the target is +3R
    return Signal(date=df.index[0], symbol="X", setup="S", entry=entry, stop=stop, target=target,
                  decision="TRADE - HIGH CONFIDENCE", quality=1.0, meta=dict(meta))


def _run(df, sig, **policy):
    return simulate([sig], {"X": df}, CFG, df.index[0], exit_policy=ExitPolicy(**policy)).trades[0]


# entry on bar 1 at 100; +1R (105) touched on bar 3; then a slide through the initial stop
ROUND_TRIP = [(99, 99.5, 98, 99), (100, 101, 99.5, 100.5), (101, 103, 100, 102), (103, 106, 102, 104),
              (103, 104, 99, 100), (100, 100.5, 94, 94.5)]


def test_defaults_change_nothing():
    df = _frame(ROUND_TRIP)
    a, b = _run(df, _signal(df)), _run(df, _signal(df), be_r=0.0, time_stop_bars=0)
    assert not ExitPolicy().managed and ExitPolicy().label() == "bracket-withTarget"
    assert a.exit_reason == b.exit_reason == "STOP" and a.exit_price == b.exit_price == 95


def test_breakeven_after_1r():
    df = _frame(ROUND_TRIP)
    t = _run(df, _signal(df), be_r=1.0)
    assert t.exit_reason == "BREAKEVEN" and t.exit_date == df.index[4], (t.exit_reason, t.exit_date)
    assert t.exit_price == 100 and abs(t.r_multiple) < 1e-9


def test_breakeven_takes_effect_the_next_session():
    # +1R touched and the low under entry on the SAME bar: the stop is still the initial one that day
    df = _frame([(99, 99.5, 98, 99), (100, 101, 99.5, 100.5), (101, 106, 99, 100), (100, 100.5, 98, 99)])
    t = _run(df, _signal(df), be_r=1.0)
    assert t.exit_reason == "BREAKEVEN" and t.exit_date == df.index[3]


def test_time_stop_fixed_bars():
    df = _frame([(99, 99.5, 98, 99)] + [(100, 101, 99.5, 100.5)] * 8)
    t = _run(df, _signal(df), time_stop_bars=3)
    # entry session is bar 1; the 3rd session after it is bar 4, sold at its close
    assert t.exit_reason == "TIME" and t.exit_date == df.index[4] and t.exit_price == 100.5


def test_time_stop_multiple_of_the_setup():
    df = _frame([(99, 99.5, 98, 99)] * 4 + [(100, 101, 99.5, 100.5)] * 12)
    sig = Signal(date=df.index[3], symbol="X", setup="S", entry=100.0, stop=95.0, target=115.0,
                 decision="TRADE - HIGH CONFIDENCE", quality=1.0, meta={"setup_start": str(df.index[0].date())})
    res = simulate([sig], {"X": df}, CFG, df.index[0], exit_policy=ExitPolicy(time_stop_mult=2.0, time_stop_bars=99))
    t = res.trades[0]
    # setup from bar 0 to the entry at bar 4: 4 bars, x2 = 8 sessions -> bar 12
    assert t.entry_date == df.index[4] and t.exit_reason == "TIME" and t.exit_date == df.index[12], t.exit_date
    # no start on the signal: the fixed count
    t2 = _run(df, _signal(df), time_stop_mult=2.0, time_stop_bars=2)
    assert t2.exit_reason == "TIME" and t2.entry_date == df.index[4] and t2.exit_date == df.index[6]


def test_partial_at_target_then_trail():
    # target 115 hit on bar 3: half sold there; the rest trails 3 x ATR(2) = 6 under the highest close
    df = _frame([(99, 99.5, 98, 99), (100, 101, 99.5, 100.5), (101, 108, 100, 107),
                 (110, 116, 109, 115), (115, 121, 114, 120), (119, 119.5, 113, 113.5)])
    t = _run(df, _signal(df), partial_at_target=0.5)
    assert t.partial_shares == t.shares // 2
    # trail after bar 4: 120 - 6 = 114; bar 5's low 113 touches it
    assert t.exit_reason == "TRAIL_STOP" and t.exit_date == df.index[5], (t.exit_reason, t.exit_date)
    rest = t.shares - t.partial_shares
    assert abs(t.exit_price - (t.partial_shares * 115 + rest * 114) / t.shares) < 1e-6


def test_stop_wins_the_tie_with_the_target():
    df = _frame([(99, 99.5, 98, 99), (100, 101, 99.5, 100.5), (100, 116, 94, 110)])
    t = _run(df, _signal(df), partial_at_target=0.5, be_r=1.0)
    assert t.exit_reason == "STOP" and t.partial_shares == 0


def _weekly(closes: list[float]) -> pd.DataFrame:
    """One bar per close from Monday 2024-01-01, business days; high 1 above the close, low 1 below."""
    return _frame([(c, c + 1, c - 1, c) for c in closes])


# week 1 at 100 (signal Mon, filled Tue); week 2 at 110; week 3 dips to 90 Mon-Thu but closes the
# week at 120; week 4 holds 118 Mon-Thu and closes the week at 100, under the 2-week line of 110
WEEKS = [100] * 5 + [110] * 5 + [90] * 4 + [120] + [118] * 4 + [100] + [100] * 3


def test_weekly_line_is_read_on_a_weeks_last_session():
    df = _weekly(WEEKS)
    line = weekly_line(df, 2)
    fridays = [i for i, d in enumerate(df.index) if d.weekday() == 4]
    assert line.notna().sum() == len(fridays) - 1          # week 1 has no 2-week average yet
    assert line.iloc[9] == 105 and line.iloc[14] == 115 and line.iloc[19] == 110
    assert line.iloc[-1] != line.iloc[-1]                  # the final bar is a Wednesday: its week is not over
    holiday = df.drop(df.index[14])                         # week 3's Friday is a holiday: Thursday ends it
    assert weekly_line(holiday, 2).loc[df.index[13]] == 100  # (110 + 90) / 2


def test_weekly_ma_sells_only_on_a_week_closing_below_the_line():
    df = _weekly(WEEKS)
    for policy in ({}, {"be_r": 50.0}):                     # the plain and the managed exit path
        t = _run(df, _signal(df, stop=50.0, target=1000.0), mode="weekly_ma", ma_weeks=2, use_target=False, **policy)
        assert t.entry_date == df.index[1] and t.exit_reason == "TREND_EXIT", (policy, t.exit_reason)
        assert t.exit_date == df.index[19] and t.exit_price == 100, (policy, t.exit_date, t.exit_price)


def test_supertrend_sells_at_the_close_that_turns_it_down():
    # Supertrend(3, 1): a steady climb, then one bar closing far below the rising lower band
    bars = [(100 + i, 101 + i, 99 + i, 100.5 + i) for i in range(12)] + [(111, 111.5, 100, 101), (101, 102, 100, 101.5)]
    df = _frame(bars)
    st = ind.supertrend(df, 3, 1.0)
    turn = int((st["dir"] == -1).to_numpy().argmax())
    assert turn == 12 and (st["dir"].iloc[3:12] == 1).all(), st
    for policy in ({}, {"be_r": 50.0}):                     # the plain and the managed exit path
        t = _run(df, _signal(df, entry=101.0, stop=50.0, target=1000.0), mode="supertrend", st_period=3,
                 st_mult=1.0, use_target=False, **policy)
        assert t.exit_reason == "TREND_EXIT" and t.exit_date == df.index[12] and t.exit_price == 101, (policy, t)
    assert ExitPolicy(mode="supertrend", use_target=False, st_period=10, st_mult=3).label() == "supertrend-10x3-noTarget"


def test_label():
    assert ExitPolicy(be_r=1.0, time_stop_mult=2.0).label() == "bracket-withTarget-be1R-time2x"
    assert ExitPolicy(time_stop_bars=40, partial_at_target=0.5).label() == "bracket-withTarget-time40-partial0.5atT"
    assert ExitPolicy(mode="weekly_ma", use_target=False).label() == "weekly_ma-30w-noTarget"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
