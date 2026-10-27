"""earnings_gaps G3: a reaction is tied to results by a recorded announcement where one exists, and by
the quarter-end-to-filing window only where none does (strategies/earnings_gaps.py `_link`).

Announcements are injected into the strategy's cache, so no database is read. The cases are the
guide's worked example (Kaynes, published 2023-05-16, gapped on the 17th), the edges of the
ANNOUNCE_WINDOW_DAYS window, a Friday-evening publication reacting on Monday, and the fallback.

    PYTHONPATH=. .venv/bin/python -m tests.test_earnings_gaps_link
"""

import datetime as dt
import sys

import pandas as pd

from swing_screener.marketdata import asof
from swing_screener.strategies.earnings_gaps import ANNOUNCE_WINDOW_DAYS, EarningsGapStrategy as S

FAILS: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def main() -> int:
    saved_a, saved_q = dict(S._announced), dict(S._quarters)
    try:
        S._announced[("india", asof.end_date())] = {
            "KAYNES.NS": [dt.date(2023, 1, 31), dt.date(2023, 5, 16), dt.date(2023, 7, 31)],
            "TITAN.NS": [dt.date(2014, 5, 9)],                        # a Friday evening
        }
        # a US company has no announcements; only its quarter window (end 2021-09-30, filed 2021-11-01)
        S._quarters["us"] = {"AA": [(pd.Timestamp("2021-10-10"), pd.Timestamp("2021-11-06"))]}
        S._announced[("us", asof.end_date())] = {}
        L = lambda sym, d: S._link(sym, pd.Timestamp(d))

        print(f"recorded announcements, a {ANNOUNCE_WINDOW_DAYS}-day window")
        check("the guide's example: published 05-16, the 05-17 gap is tied", L("KAYNES.NS", "2023-05-17") is not None)
        check("a move on the publication day itself is tied", L("KAYNES.NS", "2023-05-16") is not None)
        check(f"{ANNOUNCE_WINDOW_DAYS} days after is still tied", L("KAYNES.NS", "2023-05-19") is not None)
        check(f"{ANNOUNCE_WINDOW_DAYS + 1} days after is not", L("KAYNES.NS", "2023-05-20") is None)
        check("a move BEFORE the publication is never tied", L("KAYNES.NS", "2023-05-15") is None)
        check("published Friday evening, the Monday move is tied", L("TITAN.NS", "2014-05-12") is not None)
        check("the note names the announcement", L("KAYNES.NS", "2023-05-17") == "results announced 2023-05-16",
              str(L("KAYNES.NS", "2023-05-17")))

        print("no recorded announcements: the window, unchanged")
        check("a US move inside its quarter window is tied", L("AA", "2021-10-15") == "inside a stored results window",
              str(L("AA", "2021-10-15")))
        check("a US move outside it is not", L("AA", "2021-12-01") is None)
        check("a company with neither is not", L("NOBODY.NS", "2023-05-17") is None)
    finally:
        S._announced.clear(); S._announced.update(saved_a)
        S._quarters.clear(); S._quarters.update(saved_q)

    print(f"\n{'OK — G3 ties a move to an announcement, and falls back only without one.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
