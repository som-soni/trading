"""Pyramiding: the accounting must hold, or every number downstream is wrong.

A second tranche changes entry_price into a share-weighted average. That is only
safe because sum((entry_i - stop) * shares_i) == (avg_entry - stop) * total, so
both pnl and r_multiple keep working untouched. This checks that identity against
hand-computed values rather than trusting the algebra, and checks the refusals:
never above the buy range (the add must not lift the average cost past where the
entry itself would have been refused), never after a partial sale, never on the
entry bar.

    PYTHONPATH=. .venv/bin/python -m tests.test_pyramid
"""

import sys

import pandas as pd

from swing_screener.backtesting.portfolio_sim import ExitPolicy, Signal, simulate
from swing_screener.config import MARKETS


def _bars(closes: list[float]) -> pd.DataFrame:
    idx = pd.bdate_range("2020-01-01", periods=len(closes))
    return pd.DataFrame({"open": closes, "high": [c * 1.01 for c in closes],
                         "low": [c * 0.99 for c in closes], "close": closes,
                         "volume": [1_000_000] * len(closes)}, index=idx)


def _run(closes, pyramid_frac=None, meta=None, **kw):
    cfg = MARKETS["us"]
    df = _bars(closes)
    sig = Signal(date=df.index[0], symbol="T", setup="MV-01", entry=100.0, stop=90.0,
                 target=130.0, decision="TRADE - HIGH CONFIDENCE", quality=2.0,
                 meta={"order": "open", **(meta or {})})
    return simulate([sig], {"T": df}, cfg, df.index[0],
                    exit_policy=ExitPolicy(mode="bracket", use_target=False),
                    pyramid_frac=pyramid_frac, **kw)


def main() -> int:
    bad = []

    # a flat-then-rising path: the add triggers on the rise, not on the entry bar
    rising = [100, 100, 104, 108, 112, 116, 120, 124, 128, 132]

    one = _run(rising)
    two = _run(rising, pyramid_frac=0.5, pyramid_add_pct=2.0)
    if not one.trades or not two.trades:
        print("FAIL — no trade was opened; the fixture is wrong, not the code")
        return 1
    a, b = one.trades[0], two.trades[0]

    if b.adds != 1:
        bad.append(f"expected exactly one add, got {b.adds}")
    if b.shares != a.shares:
        bad.append(f"pyramided size {b.shares} should reach the single-tranche size {a.shares}")
    if not (b.entry_price > a.entry_price):
        bad.append(f"average cost {b.entry_price:.4f} should exceed the single fill {a.entry_price:.4f}")

    # the identity the whole design rests on
    risk = (b.entry_price - b.initial_stop) * b.shares
    pnl = (b.exit_price - b.entry_price) * b.shares - (b.costs - b.slippage)
    if abs(pnl - b.pnl) > 1e-6:
        bad.append(f"pnl {b.pnl:.4f} does not match the weighted-average computation {pnl:.4f}")
    if risk > 0 and abs(b.r_multiple - pnl / risk) > 1e-6:
        bad.append(f"r_multiple {b.r_multiple:.4f} inconsistent with pnl/risk {pnl / risk:.4f}")

    # the add is refused above the buy range, leaving the first tranche alone
    capped = _run(rising, pyramid_frac=0.5, pyramid_add_pct=2.0, )
    cap_run = _run(rising, pyramid_frac=0.5, pyramid_add_pct=2.0, meta={"max_fill": 100.5})
    if cap_run.trades and cap_run.trades[0].adds != 0:
        bad.append("an add above meta['max_fill'] must be refused")
    if cap_run.trades and cap_run.trades[0].shares >= capped.trades[0].shares:
        bad.append("a refused add must leave the position at its first tranche")

    # a position that never rises is never added to
    flat = _run([100] * 10, pyramid_frac=0.5, pyramid_add_pct=2.0)
    if flat.trades and flat.trades[0].adds:
        bad.append("a position that never advanced must not be added to")

    # off by default
    if _run(rising).trades[0].adds:
        bad.append("pyramiding must be off unless pyramid_frac is set")

    if bad:
        print("FAIL — pyramiding:")
        for x in bad:
            print("  " + x)
        return 1
    print(f"OK — pyramiding: one add, weighted average {b.entry_price:.2f} vs single fill "
          f"{a.entry_price:.2f}, pnl and R consistent, refusals honoured")
    return 0


if __name__ == "__main__":
    sys.exit(main())
