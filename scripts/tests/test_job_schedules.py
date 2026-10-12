"""Schedules keep their own clock: a market routine fires at that market's local time, through daylight
saving, on that market's weekdays.

    PYTHONPATH=. .venv/bin/python -m tests.test_job_schedules
"""

import datetime as dt
import sys
from zoneinfo import ZoneInfo

from jobs import queue as q
from jobs.registry import PIPELINES
from jobs.runner import plan

IST = ZoneInfo("Asia/Kolkata")
FAILS: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}" + (f"  — {detail}" if detail and not ok else ""))
    if not ok:
        FAILS.append(what)


def at(y, mo, d, h, mi, tz=IST) -> dt.datetime:
    return dt.datetime(y, mo, d, h, mi, tzinfo=tz)


def main() -> int:
    us_open = {"days": "mon,tue,wed,thu,fri", "monthday": None, "at_time": "08:00", "tz": "America/New_York", "enabled": True}
    local = {"days": "mon,tue,wed,thu,fri", "monthday": None, "at_time": "18:30", "enabled": True}

    # US clocks fall back on Sun 1 Nov 2026: 08:00 New York is 17:30 IST before, 18:30 IST after
    n = q.next_slot(us_open, at(2026, 10, 30, 12, 0))
    check("08:00 New York is 17:30 IST under EDT", n.astimezone(IST) == at(2026, 10, 30, 17, 30), str(n))
    n = q.next_slot(us_open, at(2026, 11, 2, 12, 0))
    check("08:00 New York is 18:30 IST under EST", n.astimezone(IST) == at(2026, 11, 2, 18, 30), str(n))
    # weekdays are the market's: Saturday 03:00 IST is still Friday afternoon in New York — no slot that day
    n = q.next_slot(us_open, at(2026, 10, 31, 3, 0))
    check("a Mon-Fri New York schedule skips the weekend", n.astimezone(IST) == at(2026, 11, 2, 18, 30), str(n))
    last = q.latest_slot(us_open, at(2026, 11, 2, 12, 0))
    check("the latest slot before Monday's is Friday's", last.astimezone(IST) == at(2026, 10, 30, 17, 30), str(last))
    # a schedule without tz keeps this machine's clock, as before
    n = q.next_slot(local, at(2026, 10, 13, 9, 0))
    check("no tz: the machine's local time", n == at(2026, 10, 13, 18, 30).astimezone(n.tzinfo), str(n))
    try:   # validated before anything is written
        q.save_schedule({"targets": ["open"], "market": "us", "days": "mon", "at_time": "08:00", "tz": "Mars/Olympus"})
        rejected = False
    except ValueError:
        rejected = True
    check("an unknown zone name is rejected", rejected)

    # the routines are pipelines of registered jobs, and the open routine only re-runs what is stale
    for name in ("close", "open"):
        check(f"pipeline '{name}' exists", name in PIPELINES)
    steps = [e.step for e in plan(["close"], ["india"], {"strategies": ["all"]})]
    check("close: data before setups before the report", steps.index("prices") < steps.index("screens")
          < min(i for i, s in enumerate(steps) if s.startswith("strategy:")) < steps.index("report") < steps.index("ingest"))
    opts = next((j[1] for j in PIPELINES["open"]["jobs"] if isinstance(j, tuple) and j[0] == "strategies"), {})
    check("open: strategies run only when stale", opts.get("only_stale") is True)

    print(f"\n{'OK — schedules keep their clocks.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
