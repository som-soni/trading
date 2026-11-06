"""The stage machine follows Weinstein's definitions (Stage analysis 2.11).

On one synthetic weekly history -- a decline, a flat base, a breakout and an advance, a sideways top that
crosses a flattening line, then a breakdown -- this pins what the book says and 2.10 got wrong:

- Stage 2 is drawn from the breakout week, and the gates know it only CONFIRM_WEEKS weeks later;
- a top never turns into a base or back into an advance without clearing its high (2.10 went 3 -> 1 -> 2);
- Stage 4 starts on the breakdown below the top's low, not when the line has fallen for weeks;
- a close above a rising line without a breakout is not Stage 2.

No database and no cached prices.

    PYTHONPATH=. .venv/bin/python -m tests.test_stage_machine
"""

import sys

import numpy as np
import pandas as pd

from swing_screener.strategies import stage_analysis as sa

FAILS: list[str] = []
BREAKOUT, TOP, BREAKDOWN = 130, 181, 240


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def weekly(closes: list[float]) -> pd.DataFrame:
    c = np.array(closes, dtype=float)
    idx = pd.date_range("2010-01-08", periods=len(c), freq="W-FRI")
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c, "volume": 1e6}, index=idx)


def history() -> list[float]:
    out = [200 * 0.985 ** i for i in range(60)]                          # a decline to about 81
    out += [81 + 4 * np.sin(i / 2.0) for i in range(70)]                 # a flat base, 77-85
    lvl = 92.0                                                           # the breakout week: well above 85
    for _ in range(BREAKOUT, TOP):
        out.append(lvl)
        lvl *= 1.012                                                     # an advance, the line rising
    top = out[-1]
    out += [top * (0.95 + 0.04 * np.sin(i / 1.5)) for i in range(TOP, BREAKDOWN)]  # a top, 91-99% of the high
    lvl = top * 0.85
    for _ in range(BREAKDOWN, 300):
        out.append(lvl)
        lvl *= 0.985                                                     # the decline
    return out


def main() -> int:
    wk = weekly(history())
    st = sa.stage_series(wk).tolist()
    periods = sa.stage_periods(wk)
    by_start = {p["start"]: p for p in periods}
    C = sa.CONFIRM_WEEKS

    print("the breakout")
    p2 = by_start.get(BREAKOUT)
    check("Stage 2 is drawn from the breakout week", p2 is not None and p2["stage"] == 2,
          str([(p["stage"], p["start"]) for p in periods]))
    check(f"and known {C} weeks later, not before", st[BREAKOUT + C - 1] == 2 and st[BREAKOUT + C - 2] != 2,
          str(st[BREAKOUT - 1:BREAKOUT + C + 1]))

    print("the top")
    after = [p for p in periods if p["start"] > BREAKOUT]
    seq = [p["stage"] for p in after]
    check("the advance ends in Stage 3, then Stage 4, and nothing else", seq[:2] == [3, 4] and 1 not in seq[:2]
          and 2 not in seq[:2], str([(p["stage"], p["start"]) for p in after]))
    s4 = next((p for p in after if p["stage"] == 4), None)
    check("Stage 4 starts on the breakdown below the top's low", s4 is not None and s4["start"] == BREAKDOWN,
          str(s4))

    print("no breakout, no Stage 2")
    # a decline, a flat base whose high is one spike to 115, then a creep from 100 to about 112: above a
    # line rising faster than the flat band, but never above the base's resistance
    base = [100.0 + 2 * np.sin(i / 2.0) for i in range(80)]
    base[40] = 115.0
    creep = [160 * 0.99 ** i for i in range(48)] + base + [100 * 1.003 ** i for i in range(40)]
    wk2 = weekly(creep)
    s2 = sa.stage_series(wk2).iloc[48 + 80:].tolist()
    line = sa.ma30(wk2)
    rising = (line / line.shift(sa.SLOPE_WEEKS) - 1) * 100 > sa.FLAT_BAND_PCT
    check("the creep is above a rising line (what 2.10 called Stage 2)",
          bool((wk2["close"] > line).iloc[-10:].all() and rising.iloc[-10:].all()))
    check("and it stays out of Stage 2", 2 not in s2, str(s2))

    print("FAILED: " + ", ".join(FAILS) if FAILS else "OK — the stage machine follows Weinstein's definitions")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
