"""`--exit-mode revert` and the next-session buy limit in the portfolio simulator, on synthetic bars.

The stock_reversion strategy's exit: from the fill session on, the first close above the short average
sells at that close (MEAN_REVERTED); with the RSI switch, the first close with RSI(2) above the level
does instead; the close of session `rv_max_bars` after the fill session sells the rest (TIME). A stop of
0 is no stop; a real one wins over the close. The limit order fills at the open when the stock opens
under it, at the limit when the session trades down to it, and is dropped otherwise.

Synthetic bars, no database and no cached prices.

    PYTHONPATH=. .venv/bin/python -m tests.test_revert_exit
"""

import dataclasses
import sys

import pandas as pd

from swing_screener.backtesting.portfolio_sim import ExitPolicy, Signal, simulate
from swing_screener.config import MARKETS
from swing_screener.core import indicators as ind
from swing_screener.strategies import stock_reversion as sr

CFG = dataclasses.replace(MARKETS["us"], slippage_bps=0.0, commission_per_order=0.0, risk_pct=0.01,
                          max_position_pct=1.0, account_size=1_000_000)
WARMUP = 10
FAILS: list[str] = []


def check(what: str, ok: bool, detail="") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def _frame(after: list[tuple]) -> pd.DataFrame:
    """WARMUP flat bars at 100, the signal bar (a dip to 95), then `after`: (open, high, low, close)."""
    bars = [(100, 101, 99, 100)] * WARMUP + [(97, 97.5, 94.5, 95)] + list(after)
    idx = pd.bdate_range("2024-01-01", periods=len(bars))
    df = pd.DataFrame([dict(open=b[0], high=b[1], low=b[2], close=b[3], volume=1e6) for b in bars], index=idx)
    df["atr14"] = 2.0
    return df


POLICY = ExitPolicy(mode="revert", use_target=False, rv_sma=5, rv_rsi_exit=0.0, rv_max_bars=5)


def _run(df, policy=POLICY, stop=0.0, meta=None):
    sig = Signal(date=df.index[WARMUP], symbol="X", setup="S1", entry=95.0, stop=stop, target=190.0,
                 decision="TRADE - HIGH CONFIDENCE", quality=90.0, meta=meta or {"order": "open"})
    return simulate([sig], {"X": df}, CFG, df.index[0], equal_alloc_pct=0.10, exit_policy=policy)


def _one(res):
    assert len(res.trades) == 1, (res.trades, res.skipped)
    return res.trades[0]


def main() -> int:
    print("revert exit")
    # the fill session closes 96, under its 5-day average (100,100,100,95,96 -> 98.2): held. The next
    # closes 99, above 100,100,95,96,99 -> 98: sold at that close
    df = _frame([(95.5, 96.5, 95, 96), (96, 99.5, 96, 99)])
    t = _one(_run(df))
    check("first close above the 5-day average sells at that close",
          t.exit_reason == "MEAN_REVERTED" and t.exit_date == df.index[-1] and abs(t.exit_price - 99) < 1e-9,
          f"{t.exit_reason} {t.exit_date} {t.exit_price}")
    check("bought at the next session's open",
          abs(t.entry_price - 95.5) < 1e-9 and t.entry_date == df.index[WARMUP + 1], f"{t.entry_date} {t.entry_price}")
    check("equal weight: one tenth of equity", abs(t.shares * t.entry_price - 100_000) < t.entry_price,
          t.shares * t.entry_price)

    # the fill session's own close counts: 101 is above 100,100,100,95,101 -> 99.2
    df = _frame([(95.5, 101.5, 95, 101), (101, 102, 100, 101)])
    t = _one(_run(df))
    check("the fill session's close above the average sells that session",
          t.exit_reason == "MEAN_REVERTED" and t.exit_date == df.index[WARMUP + 1], f"{t.exit_reason} {t.exit_date}")

    # never bounces: sold at the close of the 5th session after the fill session
    df = _frame([(95, 95.5, 93, 93)] + [(93 - i, 93.5 - i, 91 - i, 92 - i) for i in range(6)])
    t = _one(_run(df))
    check("time stop at the close of session 5 after the fill",
          t.exit_reason == "TIME" and t.exit_date == df.index[WARMUP + 1 + 5], f"{t.exit_reason} {t.exit_date}")

    # no stop: a crash is held (a stop of 0 never triggers)
    df = _frame([(95, 95.5, 93, 93), (60, 61, 50, 55), (55, 56, 54, 55.5)])
    t = _one(_run(df))
    check("a stop of 0 never sells", t.exit_reason == "OPEN", t.exit_reason)

    # a catastrophe stop at 89: a gap through it sells at the open, before a close above the line
    df = _frame([(95, 95.5, 93, 93), (85, 120, 84, 119)])
    t = _one(_run(df, stop=89.0))
    check("a real stop gapped through sells at the open, before the close",
          t.exit_reason == "STOP" and abs(t.exit_price - 85) < 1e-9, f"{t.exit_reason} {t.exit_price}")

    # the RSI switch: the first close with RSI(2) above 70 sells; the average is then not used
    df = _frame([(95.5, 96.5, 95, 96), (96, 99.5, 96, 99), (99, 101, 98.5, 100.5), (100.5, 102, 100, 101.5)])
    t = _one(_run(df, policy=dataclasses.replace(POLICY, rv_rsi_exit=70.0)))
    r = ind.rsi(df["close"], 2)
    first = next(d for d in df.index[WARMUP + 1:] if r[d] > 70)
    check("RSI exit: sells on the first close with RSI(2) above 70",
          t.exit_reason == "MEAN_REVERTED" and t.exit_date == first, f"{t.exit_reason} {t.exit_date} vs {first}")

    print("buy limit")
    meta = {"order": "limit", "limit": 93.0}
    df = _frame([(95, 96, 92.5, 94), (94, 99.5, 94, 99)])
    t = _one(_run(df, meta=meta))
    check("fills at the limit when the session trades down to it", abs(t.entry_price - 93) < 1e-9, t.entry_price)
    df = _frame([(92, 96, 91.5, 94), (94, 99.5, 94, 99)])
    t = _one(_run(df, meta=meta))
    check("fills at the open when it opens under the limit", abs(t.entry_price - 92) < 1e-9, t.entry_price)
    df = _frame([(95, 96, 93.5, 94), (93, 93, 90, 91)])
    check("is dropped when the next session never reaches it (no later fill)", not _run(df, meta=meta).trades)

    print("the strategy's constants reach the policy")
    old = sr.EXIT_ON_RSI, sr.MAX_HOLD_BARS
    try:
        sr.EXIT_ON_RSI, sr.MAX_HOLD_BARS = 1, 7
        p = ExitPolicy(mode="revert")
        check("EXIT_ON_RSI / MAX_HOLD_BARS patched after import (--const) are read",
              p.rv_rsi_exit == sr.EXIT_RSI and p.rv_max_bars == 7, f"{p.rv_rsi_exit} {p.rv_max_bars}")
    finally:
        sr.EXIT_ON_RSI, sr.MAX_HOLD_BARS = old
    lbl = ExitPolicy(mode="revert", use_target=False).label()
    check("default policy: the 5-day average, no RSI exit, 5 sessions", lbl == "revert-sma5-max5-noTarget", lbl)

    print(f"\n{'OK — the revert exit and the buy limit behave as documented.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
