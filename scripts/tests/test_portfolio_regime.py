"""The portfolio runners' market-regime switch (backtesting/regime.py).

What can go wrong is WHEN it reads: a switch that sees a later close sits out a crash it could not
have known about. So the checks are point-in-time first, arithmetic second.

    PYTHONPATH=. .venv/bin/python -m tests.test_portfolio_regime
"""

import sys

import numpy as np
import pandas as pd

from swing_screener.backtesting import regime as rg


def _frames(n=400, k=10):
    idx = pd.bdate_range("2015-01-01", periods=n)
    px = pd.DataFrame({f"S{i}": np.linspace(100, 200, n) for i in range(k)}, index=idx)
    return idx, px


def main() -> int:
    fails = []
    idx, px = _frames()
    sma = px.rolling(200, min_periods=200).mean()
    dv = pd.DataFrame(1e9, index=idx, columns=px.columns)

    # index_sma: a crash at the end must not switch off any earlier day
    bench = pd.Series(np.linspace(100, 200, len(idx)), index=idx)
    crashed = bench.copy()
    crashed.iloc[-20:] = 50.0
    a = rg.regime_on("index_sma", idx, bench_px=bench, px=px, sma200=sma, dv=dv, liq_floor=None)
    b = rg.regime_on("index_sma", idx, bench_px=crashed, px=px, sma200=sma, dv=dv, liq_floor=None)
    if not (a.iloc[:-20] == b.iloc[:-20]).all():
        fails.append("index_sma: a later crash changed an earlier day's regime (look-ahead)")
    if b.iloc[-20:].any():
        fails.append("index_sma: closes far below the 200-day still read as on")
    if not a.iloc[:199].all():
        fails.append("index_sma: days with no 200-day average yet must count as on")

    # breadth: 3 of 10 names below their 200-day -> 70% (on); 7 of 10 -> 30% (off at a 40% floor)
    p2 = px.copy()
    p2.iloc[-1, :3] = 1.0
    br = rg.breadth_pct200(p2, sma, dv, None)
    if abs(br.iloc[-1] - 70.0) > 1e-9:
        fails.append(f"breadth: expected 70% on the last day, got {br.iloc[-1]}")
    p3 = px.copy()
    p3.iloc[-1, :7] = 1.0
    on = rg.regime_on("breadth", idx, bench_px=None, px=p3, sma200=sma, dv=dv, liq_floor=None)
    if on.iloc[-1] or not on.iloc[-2]:
        fails.append("breadth: 30% above the 200-day should be off that day only")
    # the liquidity floor narrows who is counted: make the 7 laggards illiquid -> 100% of the rest
    dv2 = dv.copy()
    dv2.iloc[-1, :7] = 1.0
    if not rg.regime_on("breadth", idx, bench_px=None, px=p3, sma200=sma, dv=dv2, liq_floor=1e6).iloc[-1]:
        fails.append("breadth: names under the turnover floor were counted")

    # both = and
    both = rg.regime_on("both", idx, bench_px=bench, px=p3, sma200=sma, dv=dv, liq_floor=None)
    if both.iloc[-1] or not both.iloc[-2]:
        fails.append("both: should be off exactly when either test is off")

    try:
        rg.regime_on("vix", idx, bench_px=bench, px=px, sma200=sma, dv=dv, liq_floor=None)
        fails.append("an unknown regime kind was accepted")
    except ValueError:
        pass

    for f in fails:
        print("FAIL", f)
    print("OK — regime switch is point-in-time and counts as documented" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
