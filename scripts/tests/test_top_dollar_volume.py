"""The traded-value rank, which stands in for index membership.

Index membership cannot be reconstructed point in time here — nothing stores constituents,
and today's membership is an outcome of having grown, so applying it backwards would be
lookahead. This filter asks instead to be among the N most-traded stocks ON THE SIGNAL
DATE, which is computable from prices alone and means the same thing in 2010 as in 2026.

The whole value of it rests on that "on the signal date", so that is what this checks:
the rank must be built only from bars at or before the date it judges.

    PYTHONPATH=. .venv/bin/python -m tests.test_top_dollar_volume
"""

import datetime as dt
import sys
from dataclasses import dataclass, field

import pandas as pd

from swing_screener.backtesting import spec


@dataclass
class Sig:
    symbol: str
    date: object
    meta: dict = field(default_factory=dict)


def main() -> int:
    bad = []
    dates = [pd.Timestamp("2012-06-29"), pd.Timestamp("2018-06-29"), pd.Timestamp("2024-06-28")]

    # 1. the rank is a rank: exactly N names, and nesting as N grows
    r500 = spec.top_dollar_volume("us", dates, 500)
    r100 = spec.top_dollar_volume("us", dates, 100)
    for d in dates:
        if d not in r500 or len(r500[d]) != 500:
            bad.append(f"{d.date()}: expected 500 names, got {len(r500.get(d, ()))}")
        if d in r100 and not r100[d] <= r500[d]:
            bad.append(f"{d.date()}: the top 100 is not inside the top 500")

    # 2. POINT IN TIME: the ranking on an early date must not know about later bars.
    #    Asking for one date alone and asking for it inside a longer list must agree.
    alone = spec.top_dollar_volume("us", [dates[0]], 500)
    if alone.get(dates[0]) != r500.get(dates[0]):
        n = len(alone.get(dates[0], set()) ^ r500.get(dates[0], set()))
        bad.append(f"the {dates[0].date()} ranking changed when later dates were also requested "
                   f"({n} names differ) — it is reading bars from the future")

    # 3. membership really does change over time (a static list would pass test 1 too)
    if r500[dates[0]] == r500[dates[-1]]:
        bad.append("the top 500 is identical in 2012 and 2024 — the rank is not being recomputed")
    churn = len(r500[dates[0]] - r500[dates[-1]])
    if churn < 50:
        bad.append(f"only {churn} names left the top 500 between 2012 and 2024; suspiciously static")

    # 4. the filter keeps what the rank keeps, and never silently drops an unrankable date
    keep = next(iter(r500[dates[-1]]))
    drop = "A_SYMBOL_THAT_DOES_NOT_EXIST"
    sigs = [Sig(keep, dates[-1].date()), Sig(drop, dates[-1].date())]
    kept, stats = spec.filter_top_dollar_volume(sigs, "us", 500)
    if [s.symbol for s in kept] != [keep]:
        bad.append(f"filter kept {[s.symbol for s in kept]}, expected only {keep}")
    if stats["outside"] != 1:
        bad.append(f"stats say {stats['outside']} outside, expected 1")

    far = [Sig("NVDA", dt.date(1900, 1, 2))]          # genuinely before any stored price
    kept2, st2 = spec.filter_top_dollar_volume(far, "us", 500)
    if len(kept2) != 1 or st2["unranked"] != 1:
        bad.append("a date with no ranking must keep the signal and count it unranked, not drop it")

    if bad:
        print("FAIL — traded-value rank:")
        for x in bad:
            print("  " + x)
        return 1
    print(f"OK — top-N is a point-in-time rank ({churn} of 500 names turned over 2012->2024); "
          f"an unrankable date keeps the signal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
