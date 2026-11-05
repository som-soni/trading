"""Stage analysis's decisive-break switch (2.10) sells only on a weekly close far enough below the line.

The weekly_ma exit sells at the close of a week that ends below the 30-week simple average of weekly
closes. TREND_EXIT_BELOW_PCT (ExitPolicy.wk_below_pct) asks for that close to be more than this percent
below the line instead, so a shallow dip under a rising line is held. This pins it on a price that rises
for 40 weeks, closes one week 1.5% below its line, recovers, and later closes a week 5% below: off, the
first week sells; at 3, the second does; and a mid-week session below the line never sells either way.

No database and no cached prices.

    PYTHONPATH=. .venv/bin/python -m tests.test_trend_exit_below
"""

import sys

import pandas as pd

from swing_screener.backtesting.portfolio_sim import ExitPolicy, Signal, simulate
from swing_screener.config import MARKETS

FAILS: list[str] = []
DAYS = pd.bdate_range("2019-01-07", periods=60 * 5)           # 60 weeks, Monday start
FRIDAYS = [d for d in DAYS if d.weekday() == 4]
SIGNAL, ENTRY = FRIDAYS[33], FRIDAYS[33] + pd.Timedelta(days=3)
SHALLOW, DEEP = FRIDAYS[42], FRIDAYS[50]                       # 1.5% below, then 5% below


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def week_close_below(closes: list[float], frac: float) -> float:
    """The close c that puts this week at `frac` below a 30-week line which includes c itself:
    c = (1 - frac) * (S + c) / 30, S the previous 29 weekly closes."""
    s = sum(closes[-29:])
    return (1 - frac) * s / (30 - (1 - frac))


def frame() -> pd.DataFrame:
    rows, weekly = {}, []
    for i, fri in enumerate(FRIDAYS):
        level = 100.0 + 0.5 * i
        if fri == SHALLOW:
            level = week_close_below(weekly, 0.015)
        elif fri == DEEP:
            level = week_close_below(weekly, 0.05)
        weekly.append(level)
        for d in DAYS[(DAYS > fri - pd.Timedelta(days=7)) & (DAYS <= fri)]:
            # mid-week of the shallow week dips 4% below the line too: only the Friday close may count
            mid = fri == SHALLOW and d.weekday() == 2
            c = level * (0.96 if mid else 1.0)
            rows[d] = {"open": c, "high": c * 1.002, "low": c * 0.998, "close": c, "volume": 1e6}
    return pd.DataFrame.from_dict(rows, orient="index")


def run(below_pct: float):
    df = frame()
    sig = Signal(date=SIGNAL, symbol="X", setup="S1", entry=float(df.close[SIGNAL]),
                 stop=float(df.close[SIGNAL]) * 0.5, target=float(df.close[SIGNAL]) * 5,
                 decision="TRADE - HIGH CONFIDENCE", meta={"order": "open"})
    policy = ExitPolicy(mode="weekly_ma", use_target=False, wk_stage3=0, wk_dist_weeks=0, wk_lower_high=0,
                        wk_below_pct=below_pct)
    res = simulate([sig], {"X": df}, MARKETS["us"], start=DAYS[0], end=DAYS[-1],
                   max_positions=5, exit_policy=policy)
    t = res.trades[0] if res.trades else None
    return (t.exit_reason, pd.Timestamp(t.exit_date)) if t else (None, None)


def main() -> int:
    print("off (0): any weekly close below the line sells")
    r, d = run(0.0)
    check("sells at the close of the week 1.5% below", (r, d) == ("TREND_EXIT", SHALLOW), f"{r} {d}")
    print("at 3: only a close more than 3% below sells")
    r, d = run(3.0)
    check("holds the 1.5% week and sells the 5% one", (r, d) == ("TREND_EXIT", DEEP), f"{r} {d}")
    print("at 6: neither week is deep enough")
    r, _ = run(6.0)
    check("still held at the end", r == "OPEN", str(r))
    print("FAILED: " + ", ".join(FAILS) if FAILS else "OK — the decisive-break switch sells where it should")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
