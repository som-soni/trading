"""Stage analysis's earlier sells (2.8) fire where they should and nowhere else.

The weekly_ma exit can sell on an earlier warning that Stage 2 is failing -- Stage 3, distribution
weeks, a lower high -- read from `stage_analysis.deterioration` (`portfolio_sim._weekly_early_exit`).
The warnings are found on the whole price history, so the dangerous cases are the ones from BEFORE the
entry: a lower high or a distribution week inside the base must not sell the breakout bought out of
it. This pins each rule with controlled flags in place of `deterioration`, on a steadily rising price
that never touches the stop or the 30-week line, so the early exit is the only way out.

No database and no cached prices.

    PYTHONPATH=. .venv/bin/python -m tests.test_weekly_early_exit
"""

import sys

import pandas as pd

from swing_screener.backtesting import portfolio_sim as ps
from swing_screener.backtesting.portfolio_sim import ExitPolicy, Signal, simulate
from swing_screener.config import MARKETS
from swing_screener.strategies import stage_analysis as sa

FAILS: list[str] = []
DAYS = pd.bdate_range("2020-01-06", periods=26 * 5)          # 26 weeks, Monday start
SIGNAL, ENTRY = pd.Timestamp("2020-01-10"), pd.Timestamp("2020-01-13")
FRI = lambda n: pd.Timestamp("2020-01-10") + pd.Timedelta(weeks=n)   # n weeks after the signal Friday


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def frame() -> pd.DataFrame:
    c = pd.Series(range(len(DAYS)), index=DAYS, dtype=float) * 0.2 + 100.0
    return pd.DataFrame({"open": c * 0.999, "high": c * 1.005, "low": c * 0.995, "close": c,
                         "volume": 1e6}, index=DAYS)


def run(policy: ExitPolicy, stage3=(), dist=(), lh=()):
    """`lh` is [(confirmed_on, swing_date)]."""
    def fake(df):
        out = pd.DataFrame({sa.DET_STAGE3: False, sa.DET_DIST: False, sa.DET_LH: pd.NaT}, index=df.index)
        for d in stage3: out.loc[d, sa.DET_STAGE3] = True
        for d in dist: out.loc[d, sa.DET_DIST] = True
        for d, sw in lh: out.loc[d, sa.DET_LH] = sw
        return out
    real, ps._sa.deterioration = ps._sa.deterioration, fake
    try:
        df = frame()
        sig = Signal(date=SIGNAL, symbol="X", setup="S1", entry=float(df.close[SIGNAL]),
                     stop=float(df.close[SIGNAL]) * 0.85, target=float(df.close[SIGNAL]) * 3,
                     decision="TRADE - HIGH CONFIDENCE", meta={"order": "open"})
        res = simulate([sig], {"X": df}, MARKETS["us"], start=DAYS[0], end=DAYS[-1],
                       max_positions=5, exit_policy=policy)
    finally:
        ps._sa.deterioration = real
    t = res.trades[0] if res.trades else None
    return (t.exit_reason, pd.Timestamp(t.exit_date)) if t else (None, None)


def P(**kw):
    return ExitPolicy(mode="weekly_ma", use_target=False, **{"wk_stage3": 0, "wk_dist_weeks": 0,
                                                             "wk_lower_high": 0, **kw})


def main() -> int:
    print("off by default")
    r, _ = run(P(), stage3=[FRI(4)], dist=[FRI(3), FRI(4), FRI(5)], lh=[(FRI(6), FRI(3))])
    check("every switch off: the warnings are ignored", r == "OPEN", str(r))

    print("Stage 3")
    r, d = run(P(wk_stage3=1), stage3=[FRI(4)])
    check("sells at the close of the week it reads Stage 3", (r, d) == ("STAGE3_EXIT", FRI(4)), f"{r} {d}")
    r, _ = run(P(wk_stage3=1), stage3=[pd.Timestamp("2020-01-10")])
    check("a Stage 3 reading from before the entry does not sell", r == "OPEN", str(r))

    print("lower high")
    r, d = run(P(wk_lower_high=1), lh=[(FRI(6), FRI(4))])
    check("sells when a post-entry swing high is confirmed lower", (r, d) == ("LOWER_HIGH_EXIT", FRI(6)),
          f"{r} {d}")
    r, _ = run(P(wk_lower_high=1), lh=[(FRI(2), pd.Timestamp("2020-01-10"))])
    check("a lower high made before the entry, confirmed after it, does not sell", r == "OPEN", str(r))

    print("distribution")
    r, _ = run(P(wk_dist_weeks=3, wk_dist_window=8), dist=[FRI(3), FRI(5)])
    check("two distribution weeks are not three", r == "OPEN", str(r))
    r, d = run(P(wk_dist_weeks=3, wk_dist_window=8), dist=[FRI(3), FRI(5), FRI(7)])
    check("sells on the third inside the window", (r, d) == ("DISTRIBUTION_EXIT", FRI(7)), f"{r} {d}")
    r, _ = run(P(wk_dist_weeks=3, wk_dist_window=8), dist=[FRI(1), FRI(6), FRI(12)])
    check("three spread wider than the window do not sell", r == "OPEN", str(r))
    r, _ = run(P(wk_dist_weeks=2, wk_dist_window=8), dist=[pd.Timestamp("2020-01-10"), FRI(3)])
    check("a distribution week before the entry is not counted", r == "OPEN", str(r))

    print("the switches reach the policy through the strategy's constants (--const)")
    sa.EXIT_ON_STAGE3, sa.EXIT_DIST_WEEKS = 1, 4
    try:
        p = ExitPolicy(mode="weekly_ma")
        check("factories read the patched constants", (p.wk_stage3, p.wk_dist_weeks) == (1, 4),
              f"{p.wk_stage3} {p.wk_dist_weeks}")
    finally:
        sa.EXIT_ON_STAGE3, sa.EXIT_DIST_WEEKS = 0, 0

    print(f"\n{'OK — the early exits sell only on post-entry warnings.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
