"""Sharpe is measured over the cash rate a book was credited (swing_screener/backtesting/metrics.py `rf`).

The case that prompted it: stage4_shorts India v1.5 (entries C+P, optimise) made two trades in nine years.
Its account sat in cash earning the cash rate, the equity drew a near-straight line, and the headline
Sharpe -- computed at 0% risk-free -- came out at 38.01. Over the cash rate that line earns about nothing
for its risk, and the Sharpe says so.

Synthetic series only, no database.

    PYTHONPATH=. .venv/bin/python -m tests.test_sharpe_risk_free
"""

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from swing_screener.backtesting import metrics

FAILS: list[str] = []
BACKTESTING = Path(__file__).resolve().parent.parent / "swing_screener" / "backtesting"


def check(what: str, ok: bool) -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}")
    if not ok:
        FAILS.append(what)


def _cash_book(days: int = 2268, rate: float = 0.07, seed: int = 0):
    """A book that is all cash: the equity compounds at an annual cash rate that drifts a little, with
    rounding-size noise -- the shape of a short book that hardly ever traded."""
    idx = pd.bdate_range("2013-01-01", periods=days)
    rng = np.random.default_rng(seed)
    annual = pd.Series(rate + 0.01 * np.sin(np.arange(days) / 300.0), index=idx)
    rf = annual / 252
    r = rf + rng.normal(0, 1e-6, days)
    eq = 1_000_000 * (1 + r).cumprod()
    return eq, rf


def main() -> int:
    eq, rf = _cash_book()
    trades = pd.DataFrame(columns=["r_multiple", "pnl", "notional", "exit_reason"])
    held = pd.Series(0, index=eq.index)

    zero = metrics.compute(eq, held, trades, 0)
    over = metrics.compute(eq, held, trades, 0, rf=rf)
    print(f"  cash-only book: Sharpe {zero.sharpe:.1f} at 0% risk-free, {over.sharpe:.2f} over the cash rate")
    check("at 0% risk-free a cash-only book scores an absurd Sharpe (the bug, reproduced)", zero.sharpe > 20)
    check("over the cash rate a cash-only book's Sharpe is near zero", abs(over.sharpe) < 1.0)
    check("the Performance says what Sharpe is over", over.risk_free == "cash rate" and zero.risk_free is None)
    check("volatility is of the raw returns, unchanged by rf", np.isclose(zero.ann_volatility_pct, over.ann_volatility_pct))

    # the benchmark is measured over the same rate, or the two Sharpes do not compare
    bench = pd.Series(100 * np.exp(np.cumsum(np.random.default_rng(1).normal(4e-4, 0.01, len(eq)))), index=eq.index)
    b0 = metrics.compute(eq, held, trades, 0, bench_close=bench)
    b1 = metrics.compute(eq, held, trades, 0, bench_close=bench, rf=rf)
    check("the benchmark Sharpe is over the cash rate too", b1.benchmark_sharpe < b0.benchmark_sharpe)

    # a real equity curve: rf lowers Sharpe by about rate / vol, not to zero
    r = pd.Series(np.random.default_rng(2).normal(0.12 / 252, 0.15 / np.sqrt(252), len(eq)), index=eq.index)
    s0, s1 = metrics.risk_stats(r)[1], metrics.risk_stats(r, rf)[1]
    check("on a risky book rf lowers Sharpe by about rate / vol", 0.25 < s0 - s1 < 0.65)

    # no rf -> unchanged from the 0% convention every other runner uses
    check("rf=None is the 0% convention", np.isclose(metrics.risk_stats(r)[1],
                                                     r.mean() / r.std() * np.sqrt(252)))

    # stage4_shorts credits interest on its collateral, so its headline must pass the rate
    src = (BACKTESTING / "stage4_shorts.py").read_text()
    call = re.search(r"perf = metrics\.compute\((.*?)\)\n", src, re.S)
    check("stage4_shorts passes its cash rate to metrics.compute", bool(call and "rf=" in call.group(1)))

    print("FAIL" if FAILS else "OK")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
