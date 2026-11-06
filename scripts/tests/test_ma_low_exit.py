"""`--exit-mode ma_low` in the portfolio simulator, on synthetic bars.

A close below `ma_col` is not an exit; the next session trading under that candle's low is, as a sell-stop
at that low (at the open on a gap below it). A close back above the line cancels it, the stop still wins,
and a dip before the buy never arms it.

    PYTHONPATH=. python3 -m tests.test_ma_low_exit
"""

import dataclasses
import sys

import pandas as pd

from swing_screener.backtesting.portfolio_sim import ExitPolicy, Signal, simulate
from swing_screener.config import MARKETS

CFG = dataclasses.replace(MARKETS["india"], slippage_bps=0.0, commission_per_order=0.0, risk_pct=0.01,
                          max_position_pct=1.0, account_size=1_000_000)
LINE = 100.0   # the `ma_col` line, flat, so a close's side of it is obvious
WARMUP = 5


def _frame(after: list[tuple], before: list[tuple] | None = None) -> pd.DataFrame:
    """WARMUP bars, the signal bar (high 101: the buy-stop sits at 101.5), then `after`:
    (open, high, low, close). `before` replaces the warmup's last bars."""
    warm = [(102, 103, 101, 102)] * WARMUP
    if before:
        warm = warm[:WARMUP - len(before)] + list(before)
    bars = warm + [(100.5, 101, 99, 100.8)] + list(after)
    idx = pd.bdate_range("2024-01-01", periods=len(bars))
    df = pd.DataFrame([dict(open=b[0], high=b[1], low=b[2], close=b[3], volume=1000.0) for b in bars], index=idx)
    df["atr14"] = 2.0
    df["line"] = LINE
    return df


def _run(df):
    sig = Signal(date=df.index[WARMUP], symbol="X", setup="S1", entry=101.5, stop=90.0, target=200.0,
                 decision="TRADE - HIGH CONFIDENCE", quality=2.0, meta={"expiry_bdays": 3})
    res = simulate([sig], {"X": df}, CFG, df.index[0],
                   exit_policy=ExitPolicy(mode="ma_low", use_target=False, ma_col="line"))
    assert len(res.trades) == 1, res.skipped
    return res.trades[0]


FILL = (101, 104, 100.5, 103)   # the fill session: the buy-stop at 101.5 triggers, closes above the line


def check() -> list[str]:
    bad = []

    # a close below the line alone does not sell; the next session under its low (98) sells at 98
    df = _frame([FILL, (101, 101.5, 98.5, 99), (99, 99.5, 97, 97.5)])
    t = _run(df)
    if t.exit_reason != "TREND_EXIT" or t.exit_date != df.index[-1] or abs(t.exit_price - 98.5) > 1e-9:
        bad.append(f"break of the close-below candle's low: {t.exit_reason} on {t.exit_date} @ {t.exit_price}, "
                   f"expected TREND_EXIT on the last bar @ 98.5")

    # a gap under that low fills at the open
    df = _frame([FILL, (101, 101.5, 98.5, 99), (97, 97.5, 96, 97)])
    t = _run(df)
    if t.exit_reason != "TREND_EXIT" or abs(t.exit_price - 97) > 1e-9:
        bad.append(f"gap under the low: {t.exit_reason} @ {t.exit_price}, expected TREND_EXIT @ 97 (the open)")

    # the next session holds the low and closes back above: cancelled; a later break of the OLD low does not sell
    df = _frame([FILL, (101, 101.5, 98.5, 99), (99, 101.5, 98.7, 101), (101, 101.2, 98, 100.5),
                 (100.5, 103, 100, 102)])
    t = _run(df)
    if t.exit_reason != "OPEN":
        bad.append(f"a close back above cancels: got {t.exit_reason} on {t.exit_date}, expected still open")

    # two closes below in a row: the second candle's low arms (98.7), and the third session breaks it
    df = _frame([FILL, (101, 101.5, 98.5, 99), (99, 99.5, 98.7, 99.2), (99, 99.3, 98.6, 99)])
    t = _run(df)
    if t.exit_reason != "TREND_EXIT" or t.exit_date != df.index[-1] or abs(t.exit_price - 98.7) > 1e-9:
        bad.append(f"re-armed at the latest close-below candle: {t.exit_reason} on {t.exit_date} @ {t.exit_price}, "
                   f"expected TREND_EXIT on the last bar @ 98.7")

    # the stop wins a tie with the low break
    df = _frame([FILL, (101, 101.5, 98.5, 99), (95, 95, 85, 86)])
    t = _run(df)
    if t.exit_reason != "STOP" or abs(t.exit_price - 90) > 1e-9:
        bad.append(f"stop vs low break: {t.exit_reason} @ {t.exit_price}, expected STOP @ 90")

    # the fill session itself closing below the line arms the exit for the next session
    df = _frame([(101, 102, 99.6, 99.8), (99.8, 100, 99, 99.5)])
    t = _run(df)
    if t.exit_reason != "TREND_EXIT" or abs(t.exit_price - 99.6) > 1e-9:
        bad.append(f"fill session below the line: {t.exit_reason} @ {t.exit_price}, expected TREND_EXIT @ 99.6")

    # a close below the line BEFORE the buy (the dip) never arms it: the signal bar closes 100.8, the bar
    # before it closed 99 with low 98; the fill session trades down to 98.2 and must not sell
    df = _frame([(101, 104, 98.2, 103), (103, 105, 102, 104)], before=[(100, 100.5, 98, 99)])
    t = _run(df)
    if t.exit_reason != "OPEN":
        bad.append(f"a pre-entry dip armed the exit: {t.exit_reason} on {t.exit_date}")
    return bad


if __name__ == "__main__":
    probs = check()
    for p in probs:
        print("FAIL:", p)
    print("ok" if not probs else f"{len(probs)} problem(s)")
    sys.exit(1 if probs else 0)
