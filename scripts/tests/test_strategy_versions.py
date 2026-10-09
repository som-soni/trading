"""Changing a strategy's rules must come with a version bump.

Without this the version is decoration. `strategies/versions.lock.json` records
each strategy's version and a fingerprint of its tunables; this fails when a
fingerprint has moved while the version stayed where it was.

Run:  PYTHONPATH=. python3 tests/test_strategy_versions.py
Fix:  bump `version`, add a `changelog` entry, then
      PYTHONPATH=. python3 -m swing_screener.strategies.versions --update
"""

import sys

from swing_screener.strategies import versions


def main() -> int:
    problems, notes = versions.check()
    for n in notes:
        print(n)
    if problems:
        print("\nFAIL — a strategy changed without a version bump:\n")
        for p in problems:
            print(p, "\n")
        return 1
    print("OK — every strategy's rules match its recorded version.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
