"""The paper breakout list's verdicts follow the rules its notes state. Synthetic bars, no database.

    PYTHONPATH=. .venv/bin/python -m tests.test_breakout_tracking
"""

import sys

import pandas as pd

from swing_screener.screening import breakout_tracking as bt

FAILS: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def bars(tail: list[tuple[float, float, float]]) -> pd.DataFrame:
    """60 quiet sessions at 100 on volume 1000, then `tail` as (close, high, volume)."""
    rows = [(100.0, 101.0, 1000.0)] * 60 + tail
    idx = pd.bdate_range("2026-01-01", periods=len(rows))
    df = pd.DataFrame(rows, index=idx, columns=["close", "high", "volume"])
    df["open"], df["low"] = df["close"], df["close"] * 0.99
    return df


PLAN = {"from_date": str(pd.bdate_range("2026-01-01", periods=60)[-1].date()), "ref_price": 100.0, "pivot": 102.0, "stop": 98.0}


def main() -> int:
    v = bt.judge(bars([(101, 101.5, 900)]), PLAN)
    check("below the pivot: waiting", v["status"] == "waiting", v)
    v = bt.judge(bars([(103, 103.5, 1000)]), PLAN)
    check("above the pivot on light volume: not a breakout", v["status"] == "waiting" and "light volume" in v["detail"], v)
    v = bt.judge(bars([(103, 103.5, 2000)]), PLAN)
    check("above the pivot on 2x volume: open", v["status"] == "open" and v["breakout_date"], v)
    v = bt.judge(bars([(103, 103.5, 2000), (101, 103, 900)]), PLAN)
    check("back below the pivot within 3 sessions: failed", v["status"] == "failed", v)
    v = bt.judge(bars([(103, 103.5, 2000), (106, 110.5, 1500)]), PLAN)
    check("a high at pivot + 2R: success", v["status"] == "success", v)
    v = bt.judge(bars([(97, 99, 1200)]), PLAN)
    check("a close below the stop before breaking out: stopped", v["status"] == "stopped", v)
    v = bt.judge(bars([(101, 101.5, 900)] * bt.WINDOW_SESSIONS), PLAN)
    check(f"no breakout in {bt.WINDOW_SESSIONS} sessions: expired", v["status"] == "expired", v)
    p = bt.parse_plan("Added 2026-11-10 at 3,882.60 (close 2026-11-09). Pivot 4,049.35, stop 3673.30 (9.3%). x")
    check("the plan is read from a note", p == {"ref_price": 3882.6, "from_date": "2026-11-09", "pivot": 4049.35, "stop": 3673.3}, p)
    check("a status line is replaced, not stacked", bt._STATUS_LINE.sub("", "Status 2026-11-11: OPEN -- x\nAdded ...") == "Added ...")
    print(f"\n{'OK — the paper breakout verdicts follow their rules.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
