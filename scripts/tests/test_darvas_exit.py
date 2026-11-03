"""The darvas exit trails the stop by Darvas boxes, and the boxes it reads are causal.

A stepping-up series of boxes on synthetic bars: each higher box raises the stop to one tick under its
bottom on the session that completes it (acting from the next), the stop is never lowered, and the
trade exits when the last box's bottom breaks. The box detector (core/darvas.py) is checked to find on
`bars[:t+1]` exactly the boxes of the full history completed by bar t -- the no-look-ahead property
the exit relies on -- and the strategy's resumable scan cache to agree with fresh scans.

Synthetic bars, no database and no cached prices.

    PYTHONPATH=. .venv/bin/python -m tests.test_darvas_exit
"""

import sys

import pandas as pd

from swing_screener.backtesting.portfolio_sim import ExitPolicy, Signal, simulate
from swing_screener.config import MARKETS
from swing_screener.core import darvas
from swing_screener.strategies import darvas as dv

FAILS: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


# (high, low) after a 260-session climb from 50 to 100; open and close sit mid-range unless given.
# Box 1: top 102 (b0), bottom 97 (b2), complete b5. Bought b7. Box 2: top 110 (b10), bottom 105 (b12),
# complete b15. Box 3: top 118 (b18), bottom 113 (b20), complete b23. b24 breaks 113.
STEPS = [
    (102, 100), (101, 99), (100.5, 97), (100.8, 98), (101, 98), (101.5, 98.5),         # b0-b5 box 1
    (101, 99), (104, 101, 101.5, 103.5),                                               # b6, b7 breakout
    (106, 103), (108, 105.5), (110, 107), (109, 106), (108, 105), (109, 105.5),        # b8-b13
    (108.5, 106), (109.5, 106.5),                                                      # b14, b15 box 2
    (112, 108), (115, 111), (118, 114), (117, 114.5), (116, 113), (117, 113.5),        # b16-b21
    (116.5, 114), (117, 114.5),                                                        # b22, b23 box 3
    (116, 112, 115, 112.5),                                                            # b24 breaks it
    (113, 111), (112, 110),
]
WARMUP = 260


def _frame() -> pd.DataFrame:
    rows = []
    for i in range(WARMUP):
        p = 50 + 50 * i / (WARMUP - 1)
        rows.append((p, p + 0.5, p - 0.5, p))
    for st in STEPS:
        h, lo = st[0], st[1]
        o, c = (st[2], st[3]) if len(st) == 4 else ((h + lo) / 2, (h + lo) / 2)
        rows.append((o, h, lo, c))
    idx = pd.bdate_range("2021-01-04", periods=len(rows))
    df = pd.DataFrame(rows, index=idx, columns=["open", "high", "low", "close"])
    df["volume"] = 1e6
    return df


def b(k: int) -> int:
    return WARMUP + k


def _run(df, stop: float, end_bar: int | None = None):
    sig = Signal(date=df.index[b(5)], symbol="TEST", setup="S1", entry=102.11, stop=stop, target=10_000.0,
                 decision="TRADE - HIGH CONFIDENCE", quality=2.0, meta={"box_top": 102.0, "box_bottom": 97.0})
    res = simulate([sig], {"TEST": df}, MARKETS["us"], start=df.index[200],
                   end=df.index[end_bar] if end_bar is not None else None,
                   exit_policy=ExitPolicy(mode="darvas", use_target=False), slippage_bps=0.0)
    return res.trades[0] if res.trades else None


def main() -> int:
    df = _frame()
    h, lo = df["high"].to_numpy(), df["low"].to_numpy()
    lb, tc, bc = dv.NEW_HIGH_LOOKBACK, dv.TOP_CONFIRM, dv.BOTTOM_CONFIRM

    print("the detector finds the three boxes, each on the bar that confirms its bottom")
    found = darvas.boxes(h, lo, lb, tc, bc)
    got = [(x.top, x.bottom, x.top_i - WARMUP, x.bottom_i - WARMUP, x.done_i - WARMUP) for x in found]
    want = [(102, 97, 0, 2, 5), (110, 105, 10, 12, 15), (118, 113, 18, 20, 23)]
    check("boxes are (102/97 done b5), (110/105 done b15), (118/113 done b23)", got == want, str(got))

    print("no look-ahead: the boxes of bars[:t+1] are the full scan's boxes completed by t")
    bad = [t for t in range(WARMUP - 5, len(df))
           if darvas.boxes(h[:t + 1], lo[:t + 1], lb, tc, bc) != [x for x in found if x.done_i <= t]]
    check("every prefix agrees with the full scan", not bad, f"differs at bars {bad[:5]}")

    print("restart: a high above the top before the bottom is confirmed means no box")
    h2, lo2 = h.copy(), lo.copy()
    h2[b(4)] = 102.5          # b4 takes out the 102 top before box 1's bottom (b2) is held 3 sessions
    tops = [x.top for x in darvas.boxes(h2, lo2, lb, tc, bc)]
    check("box 1 is gone; the later boxes remain", 102 not in tops and 110 in tops and 118 in tops, str(tops))

    print("the strategy's resumable scan agrees with fresh scans on a growing history")
    dv.DarvasStrategy._scans.clear()
    mism = [t for t in range(WARMUP - 5, len(df))
            if dv.DarvasStrategy._boxes("TEST", df.iloc[:t + 1]) != darvas.boxes(h[:t + 1], lo[:t + 1], lb, tc, bc)]
    check("growing slices", not mism, f"differs at bars {mism[:5]}")
    short = dv.DarvasStrategy._boxes("TEST", df.iloc[:b(16)])
    check("a shorter slice after a longer one keeps only its own boxes", [x.top for x in short] == [102, 110])

    print("the stop steps up with each higher box, from the session after it completes")
    tick = MARKETS["us"].tick_size
    s0, s2, s3 = 97 - tick, dv.stop_below(105, tick), dv.stop_below(113, tick)
    for end, want_stop, what in ((b(14), s0, "before box 2 completes: the initial stop"),
                                 (b(15), s2, "box 2 completes: one tick under 105"),
                                 (b(22), s2, "between boxes: unchanged"),
                                 (b(23), s3, "box 3 completes: one tick under 113")):
        t = _run(df, s0, end)
        check(what, t is not None and t.exit_reason == "OPEN" and abs(t.stop - want_stop) < 1e-9,
              f"{t.exit_reason if t else None} stop {t.stop if t else None}, want {want_stop}")

    print("never lowered: a higher box whose stop level is under the current stop leaves it")
    # any low under the stop sells, so only a bottom inside the tick above the stop can test it: box 2's
    # bottom moved from 105 to 96.995, whose own stop level (one tick under) is below the initial 96.99
    deep = df.copy()
    deep.iloc[b(12), deep.columns.get_loc("low")] = s0 + tick / 2
    t = _run(deep, s0, b(15))
    check(f"stop {s0:g} stays when box 2 would set {dv.stop_below(s0 + tick / 2, tick):g}",
          t is not None and t.exit_reason == "OPEN" and abs(t.stop - s0) < 1e-9, f"stop {t.stop if t else None}")
    t = _run(deep, s0, b(23))
    check("...and box 3 still raises it", t is not None and abs(t.stop - s3) < 1e-9, f"stop {t.stop if t else None}")

    print("the trade exits when the last box's bottom breaks")
    t = _run(df, s0)
    check("bought on b7 at the buy-stop", t is not None and t.entry_date == df.index[b(7)]
          and abs(t.entry_price - 102.11) < 1e-9, f"{t.entry_date if t else None} {t.entry_price if t else None}")
    check("sold on b24 at one tick under 113, as TRAIL_STOP",
          t is not None and t.exit_date == df.index[b(24)] and abs(t.exit_price - s3) < 1e-9
          and t.exit_reason == "TRAIL_STOP",
          f"{t.exit_date if t else None} {t.exit_price if t else None} {t.exit_reason if t else None}")
    check("its R is measured against the initial stop", t is not None and t.initial_stop == s0 and t.r_multiple > 1,
          f"{t.r_multiple if t else None}")

    print(f"\n{'OK — the darvas exit trails by causal boxes.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
