"""The kullamagi strategy's order and management in the portfolio simulator, on synthetic bars.

A close order (meta["order"] == "close") buys at its own signal session's close; `--exit-mode kullamagi`
then sells a part after PARTIAL_AFTER_BARS sessions in profit with the stop moved to the entry, and the
rest on a close below the TRAIL_SMA-day average, at the stop, or after MAX_HOLD_BARS sessions.

    PYTHONPATH=. python3 -m tests.test_kullamagi_exits
"""

import dataclasses
import sys

import pandas as pd

from swing_screener.backtesting.portfolio_sim import ExitPolicy, Signal, simulate
from swing_screener.config import MARKETS

CFG = dataclasses.replace(MARKETS["india"], slippage_bps=0.0, commission_per_order=0.0, risk_pct=0.01,
                          max_position_pct=1.0, account_size=1_000_000)
WARMUP = 12   # flat bars at 100 before the signal, so the 10-day average is 100 at the entry


def _frame(after: list[tuple]) -> pd.DataFrame:
    """WARMUP flat bars, the signal bar (close 100, low 97), then `after`: (open, high, low, close)."""
    bars = [(100, 100.5, 99.5, 100)] * WARMUP + [(99, 100.5, 97, 100)] + list(after)
    idx = pd.bdate_range("2024-01-01", periods=len(bars))
    df = pd.DataFrame([dict(open=b[0], high=b[1], low=b[2], close=b[3], volume=1000.0) for b in bars], index=idx)
    df["atr14"] = 2.0
    return df


def _run(df, **policy):
    sig = Signal(date=df.index[WARMUP], symbol="X", setup="S1", entry=100.0, stop=97.0, target=130.0,
                 decision="TRADE - HIGH CONFIDENCE", quality=2.0, meta={"order": "close"})
    res = simulate([sig], {"X": df}, CFG, df.index[0],
                   exit_policy=ExitPolicy(mode="kullamagi", use_target=False, **policy))
    assert len(res.trades) == 1, res.skipped
    return res.trades[0]


def check() -> list[str]:
    bad = []
    pol = dict(km_partial_bars=3, km_partial_divisor=3, km_trail_sma=10, km_max_bars=120)

    # bought at the signal close; a third sold at session 3's close; the rest stopped at the entry
    df = _frame([(100, 104, 99, 103), (103, 106, 102, 105), (105, 109, 104, 108), (108, 111, 107, 110),
                 (109, 109, 99.5, 101)])
    t = _run(df, **pol)
    if t.entry_date != df.index[WARMUP] or abs(t.entry_price - 100) > 1e-9:
        bad.append(f"close order: entry {t.entry_date.date()} @ {t.entry_price}, expected the signal bar @ 100")
    if t.partial_shares != t.shares // 3:
        bad.append(f"partial: {t.partial_shares} of {t.shares} sold, expected a third")
    if t.exit_reason != "BREAKEVEN" or t.exit_date != df.index[-1]:
        bad.append(f"after the partial the stop is the entry: got {t.exit_reason} on {t.exit_date}")
    want = (108 * t.partial_shares + 100 * (t.shares - t.partial_shares)) / t.shares
    if abs(t.exit_price - want) > 1e-6:
        bad.append(f"blended exit {t.exit_price:.4f}, expected {want:.4f}")

    # session 3 closes under the entry: no partial; a close under the 10-day sells everything
    df = _frame([(100, 101, 98, 100.5), (100.5, 101, 98, 100.2), (100, 100.5, 98, 99.5), (99.5, 100, 98, 98.5)])
    t = _run(df, **pol)
    if t.partial_shares or t.exit_reason != "TREND_EXIT" or t.exit_date != df.index[WARMUP + 3]:
        bad.append(f"no-partial case: partial {t.partial_shares}, {t.exit_reason} on {t.exit_date}")

    # a gap through the initial stop fills at the open
    df = _frame([(95, 96, 94, 95)])
    t = _run(df, **pol)
    if t.exit_reason != "STOP" or abs(t.exit_price - 95) > 1e-9:
        bad.append(f"gap-through: {t.exit_reason} @ {t.exit_price}, expected STOP @ 95")

    # the time limit sells what is left at the close of session km_max_bars
    df = _frame([(100 + i, 102 + i, 99.5 + i, 101 + i) for i in range(8)])
    t = _run(df, **{**pol, "km_max_bars": 5})
    if t.exit_reason != "TIME" or t.exit_date != df.index[WARMUP + 5]:
        bad.append(f"time limit: {t.exit_reason} on {t.exit_date}, expected TIME on session 5")
    return bad


if __name__ == "__main__":
    probs = check()
    print("\n".join(probs) or "OK — close orders and the kullamagi exit behave as documented")
    sys.exit(1 if probs else 0)
