"""A date priced for only a handful of a market's symbols is a stray session, and nothing else is
(swing_screener/marketdata/sessions.py `find_stray`).

No database: synthetic per-date counts.

    PYTHONPATH=. .venv/bin/python -m tests.test_sessions
"""

import sys

import pandas as pd

from swing_screener.marketdata.sessions import SETTLE_SESSIONS, STRAY_MAX_SHARE, find_stray

FAILS: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}" + (f"  — {detail}" if detail and not ok else ""))
    if not ok:
        FAILS.append(what)


def counts(n: int = 120, usual: int = 1000, **at: int) -> pd.Series:
    s = pd.Series(float(usual), index=pd.bdate_range("2012-01-02", periods=n))
    for i, c in at.items():
        s.iloc[int(i.lstrip("_"))] = c
    return s


def main() -> int:
    print("stray sessions")
    s = counts()
    check("a full calendar has none", find_stray(s).empty)

    s = counts(_40=3)
    found = find_stray(s)
    check("a date priced for 3 of 1,000 is stray", list(found["date"]) == [s.index[40]], str(found))
    check("...with its count and the usual count", found["priced"].tolist() == [3] and found["usual"].tolist() == [1000])

    s = counts(_40=920)
    check("a real special session priced for most of the market is kept", find_stray(s).empty)

    s = counts(_40=int(1000 * STRAY_MAX_SHARE))
    check(f"exactly {STRAY_MAX_SHARE:.0%} of the usual count is kept", find_stray(s).empty)

    s = counts(_40=3, _41=2, _42=4)
    check("consecutive stray dates are all found", len(find_stray(s)) == 3)

    s = counts(**{f"_{len(counts()) - 1}": 40})
    check("the newest day, part-way through a refresh, is not judged", find_stray(s).empty)
    s = counts(**{f"_{len(counts()) - SETTLE_SESSIONS - 1}": 40})
    check(f"a sparse day with {SETTLE_SESSIONS} sessions after it is", len(find_stray(s)) == 1)

    growing = pd.Series([200.0 + 10 * i for i in range(120)], index=pd.bdate_range("2004-01-01", periods=120))
    growing.iloc[60] = 150
    found = find_stray(growing)
    check("the usual count follows a growing universe", list(found["date"]) == [growing.index[60]], str(found))

    print(f"\n{'FAILED: ' + ', '.join(FAILS) if FAILS else 'all passed'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
