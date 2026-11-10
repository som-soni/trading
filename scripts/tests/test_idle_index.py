"""`--idle-index` (backtest.idle_index_overlay): idle cash held in the benchmark.

The overlay must be exact at both ends -- an all-cash account becomes the index (less the one
purchase), a fully invested one is unchanged -- and must never read a later price than the
session it is valuing.

    PYTHONPATH=. .venv/bin/python -m tests.test_idle_index
"""

import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd

from swing_screener.backtesting import backtest as bt

FAILS: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def main() -> int:
    idx = pd.bdate_range("2020-01-01", periods=250)
    rng = np.random.default_rng(7)
    bench = pd.Series(100 * np.cumprod(1 + rng.normal(0.0005, 0.01, len(idx))), index=idx)
    cfg = SimpleNamespace(benchmark_ticker="IDX")
    cost = bt.IDLE_INDEX_COST_BPS / 1e4

    # all cash: the account is the index from the first close on, less the one purchase
    flat = SimpleNamespace(equity=pd.Series(1000.0, index=idx), cash=pd.Series(1000.0, index=idx))
    bt.idle_index_overlay(flat, bench, cfg)
    want = 1000.0 * (1 - cost) * bench.iloc[-1] / bench.iloc[0]
    check("an all-cash account tracks the index, less the first purchase",
          abs(flat.equity.iloc[-1] / want - 1) < 1e-9, f"{flat.equity.iloc[-1]:.4f} vs {want:.4f}")

    # fully invested: nothing to put in the index, so nothing changes
    eq = pd.Series(1000 * np.cumprod(1 + rng.normal(0.001, 0.02, len(idx))), index=idx)
    full = SimpleNamespace(equity=eq.copy(), cash=pd.Series(0.0, index=idx))
    bt.idle_index_overlay(full, bench, cfg)
    check("a fully invested account is unchanged", np.allclose(full.equity.values, eq.values))

    # half in cash throughout, strategy flat: half the index's return, rebalanced daily
    half = SimpleNamespace(equity=pd.Series(1000.0, index=idx), cash=pd.Series(500.0, index=idx))
    bt.idle_index_overlay(half, bench, cfg)
    want = 1000.0 * (1 - 0.5 * cost) * float((1 + 0.5 * bench.pct_change().fillna(0)).prod())
    check("half in cash earns half the index's daily return", abs(half.equity.iloc[-1] / want - 1) < 1e-9)

    # point in time: changing the index after day k cannot change equity up to day k
    k = 120
    late = bench.copy()
    late.iloc[k + 1:] *= 3
    a = SimpleNamespace(equity=pd.Series(1000.0, index=idx), cash=pd.Series(600.0, index=idx))
    b = SimpleNamespace(equity=pd.Series(1000.0, index=idx), cash=pd.Series(600.0, index=idx))
    bt.idle_index_overlay(a, bench, cfg)
    bt.idle_index_overlay(b, late, cfg)
    check("a later index price never changes an earlier day's equity",
          np.allclose(a.equity.iloc[: k + 1].values, b.equity.iloc[: k + 1].values))
    check("the plain curve is kept beside the new one", hasattr(a, "equity_plain"))

    print(f"\n{'OK — idle cash in the index is exact at both ends and point in time.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
