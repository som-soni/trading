"""A plan's reward-to-risk minimum is re-tested on the price actually paid, not only on the
signal close (`portfolio_sim`, the `min_structural_r` meta key; Minervini supplies it).

An order fills at the NEXT open. A gap up moves the entry without moving the stop or the
target, so it shortens the reward and lengthens the risk at once, and a plan that cleared the
minimum on the close can be bought below it. AKAM on 2013-01-28 is the case the rule is named
for: 2.09R on the 41.15 close, filled at the next open 41.27 plus 5bps = 41.2906, which is
1.92R as bought -- and it was bought, for -3.0R.

No database and no cached prices: the bars are synthetic, so the arithmetic is the only thing
under test.

    PYTHONPATH=. .venv/bin/python -m tests.test_fill_reward_risk
"""

import sys

import pandas as pd

from swing_screener.backtesting.portfolio_sim import Signal, simulate
from swing_screener.config import MARKETS

ENTRY, STOP, TARGET, SLIP_BPS = 41.15, 38.80, 46.06, 5.0

FAILS: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def _frame(next_open: float) -> pd.DataFrame:
    idx = pd.bdate_range("2013-01-25", periods=12)
    o = [ENTRY] + [next_open] * 11
    return pd.DataFrame(
        {"open": o, "high": [x * 1.01 for x in o], "low": [x * 0.995 for x in o],
         "close": o, "volume": [5e6] * 12}, index=idx)


def _run(next_open: float, min_r: float | None):
    meta = {"order": "open"}
    if min_r is not None:
        meta["min_structural_r"] = min_r
    sig = Signal(date=pd.Timestamp("2013-01-25"), symbol="AKAM", setup="S4", entry=ENTRY,
                 stop=STOP, target=TARGET, decision="TRADE - HIGH CONFIDENCE", meta=meta)
    res = simulate([sig], {"AKAM": _frame(next_open)}, MARKETS["us"],
                   start=pd.Timestamp("2013-01-25"), end=pd.Timestamp("2013-02-08"),
                   max_positions=5, slippage_bps=SLIP_BPS)
    if not res.trades:
        return None
    fill = float(res.trades[0].entry_price)
    return fill, (TARGET - fill) / (fill - STOP)


def main() -> int:
    print("the fill, not the signal close, decides")

    gap_off = _run(41.27, None)
    check("without the rule, the gap-up order fills", gap_off is not None)
    if gap_off:
        fill, r = gap_off
        check("...at AKAM's recorded entry price", abs(fill - 41.2906) < 5e-4, f"{fill:.4f}")
        check("...which is under the 2:1 it was accepted on", r < 2.0, f"{r:.3f}R")

    check("with the rule, the same gap-up order is refused", _run(41.27, 2.0) is None)

    flat = _run(ENTRY, 2.0)
    check("a fill that still clears 2:1 is NOT refused", flat is not None)
    if flat:
        check("...and clears it on the paid price", flat[1] >= 2.0, f"{flat[1]:.3f}R")

    # the rule is the strategy's to set: a strategy that names no minimum is untouched
    check("no minimum supplied means no new refusal", _run(41.27, None) is not None)

    print(f"\n{'OK — the reward-to-risk minimum is enforced on the fill.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
