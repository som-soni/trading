"""`--rank-by setup_momentum`: the strategy's own score decides, momentum only breaks exact ties.

Strategies with a few discrete setup-quality levels tie constantly, and a tie fell through to
Python's stable sort -- the order the market was scanned in, i.e. alphabetical. Measured on
stored runs, US donchian bought A-H tickers in 77% of its trades from a pool where they were 43%.
The other rank modes replace the score outright, which would discard a strategy's own ordering
(breakout's confirmed-over-unconfirmed, stage_analysis's low-volume queueing). This one keeps it.

Synthetic prices, no database.

    PYTHONPATH=. .venv/bin/python -m tests.test_rank_tiebreak
"""

import sys

import numpy as np
import pandas as pd

from swing_screener.backtesting.backtest import TIEBREAK_SCALE, rerank_signals
from swing_screener.backtesting.portfolio_sim import Signal

FAILS: list[str] = []
IDX = pd.bdate_range("2020-01-01", periods=300)
DAY = IDX[-1]


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def _px(growth: float, bars: int = 300) -> pd.DataFrame:
    c = 100 * np.exp(np.linspace(0, growth, bars))
    return pd.DataFrame({"open": c, "high": c, "low": c, "close": c, "volume": 1e6},
                        index=IDX[-bars:])


def _sig(sym: str, q: float) -> Signal:
    return Signal(date=DAY, symbol=sym, setup="S1", entry=100, stop=95, target=120,
                  decision="TRADE - HIGH CONFIDENCE", quality=q)


def _order(sigs):
    return [s.symbol for s in sorted(sigs, key=lambda s: s.quality, reverse=True)]


def main() -> int:
    prices = {"AAA": _px(0.05), "MMM": _px(0.40), "ZZZ": _px(0.90),   # ZZZ strongest, AAA weakest
              "BIG": _px(2.00), "NEW": _px(0.90, bars=100)}           # NEW: too short for 12-1

    print("ties are broken by momentum, not by the alphabet")
    tied = [_sig("AAA", 2.0), _sig("MMM", 2.0), _sig("ZZZ", 2.0)]
    check("the default 'setup' mode leaves the scan order (the old behaviour)",
          _order(rerank_signals(tied, prices, "setup")) == ["AAA", "MMM", "ZZZ"])
    check("setup_momentum orders three tied signals strongest first",
          _order(rerank_signals(tied, prices, "setup_momentum")) == ["ZZZ", "MMM", "AAA"],
          str(_order(rerank_signals(tied, prices, "setup_momentum"))))

    print("the strategy's own score always wins")
    mixed = [_sig("BIG", 1.5), _sig("AAA", 2.0)]          # huge momentum, lower score
    check("a lower setup score never overtakes a higher one, however strong its momentum",
          _order(rerank_signals(mixed, prices, "setup_momentum")) == ["AAA", "BIG"])
    out = rerank_signals([_sig("ZZZ", 2.0)], prices, "setup_momentum")
    check("the nudge stays below the tie-break scale", 0 < out[0].quality - 2.0 < TIEBREAK_SCALE,
          f"{out[0].quality - 2.0}")
    check("the scale is far below the smallest gap between quality levels (0.5)",
          TIEBREAK_SCALE < 0.5 / 10)

    print("unknown momentum never wins a tie by accident")
    unk = [_sig("NEW", 2.0), _sig("AAA", 2.0)]
    check("a stock without 12-1 history sorts below a known one at the same level",
          _order(rerank_signals(unk, prices, "setup_momentum")) == ["AAA", "NEW"])

    print(f"\n{'OK — the alphabet no longer breaks ties.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
