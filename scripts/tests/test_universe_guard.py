"""A universe refresh never replaces the ticker list with an empty or badly shrunken one
(swing_screener/marketdata/universe.py `_write_universe`, UNIVERSE_MIN_KEEP).

No network and no real data file: the writer is pointed at a temporary CSV.

    PYTHONPATH=. .venv/bin/python -m tests.test_universe_guard
"""

import sys
import tempfile
from pathlib import Path

from swing_screener.marketdata import universe as U

FAILS: list[str] = []


def check(what: str, ok: bool) -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}")
    if not ok:
        FAILS.append(what)


def refused(rows) -> bool:
    try:
        U._write_universe("test", rows)
    except U.UniverseShrank:
        return True
    return False


def main() -> int:
    tmp = Path(tempfile.mkdtemp()) / "universe_test.csv"
    real_path = U.universe_csv_path
    U.universe_csv_path = lambda market: tmp
    try:
        base = [f"T{i:04d}" for i in range(1000)]
        check("an empty refresh with no list yet is refused", refused([]))
        check("a first refresh is written", not refused(base) and len(U.load_universe("test")) == 1000)
        check("an empty refresh does not replace the list", refused([]) and len(U.load_universe("test")) == 1000)
        keep = int(U.UNIVERSE_MIN_KEEP * 1000)
        check("a refresh shrunk below the floor is refused", refused(base[: keep - 1]))
        check("a refresh at the floor is written (delistings are normal)", not refused(base[:keep]))
        check("a larger refresh is written", not refused(base + ["NEW1", "NEW2"]))
    finally:
        U.universe_csv_path = real_path
    print("\nOK" if not FAILS else f"\n{len(FAILS)} failed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
