"""Breadth refuses a day whose turnover jumps away from the day before (a partial price load).

`breadth.plausible` on hand-made rows: 2026-11-12's US row read $128 billion between $696 and $686 billion
and, stored, cut every turnover floor scaled on it about fivefold for a day.

    PYTHONPATH=. .venv/bin/python -m tests.test_breadth_guard
"""

import sys

from swing_screener.analytics import breadth

FAILS: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def days(kept):
    return [r[0] for r in kept]


def main() -> int:
    print("the turnover guard")
    r = lambda d, t: (d, 1000, 600, 400, t)  # noqa: E731 -- date, n, adv, dec, turnover
    kept, held = breadth.plausible([r("11", 696e9), r("12", 128e9), r("13", 686e9)], 690e9)
    check("a lone collapse between two normal days is held back", days(kept) == ["11", "13"] and days(held) == ["12"],
          f"{days(kept)} / {days(held)}")
    kept, held = breadth.plausible([r("11", 696e9), r("12", 128e9)], 690e9)
    check("a collapse on the latest day, with nothing to confirm it, is held back", days(held) == ["12"], days(held))
    kept, held = breadth.plausible([r("11", 696e9), r("12", 1.8e12), r("13", 1.75e12)], 690e9)
    check("a jump the next day confirms is a new level and kept", not held, days(held))
    kept, held = breadth.plausible([r(str(d), 690e9 * (1 + 0.03 * (d % 3))) for d in range(10)], 690e9)
    check("ordinary day-to-day moves are all kept", not held, days(held))
    kept, held = breadth.plausible([r("1", 5e9)], None)
    check("the first day ever stored has nothing to compare with and is kept", days(kept) == ["1"], days(kept))
    print(f"\n{'FAILED: ' + ', '.join(FAILS) if FAILS else 'breadth stores only complete days'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
