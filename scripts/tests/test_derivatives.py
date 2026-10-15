"""The F&O bhavcopy reader: two archive layouts that must mean the same thing.

NSE publishes derivatives in a legacy layout (to mid-2024) and UDiFF (2024 on). The whole
ingest rests on those agreeing, and they overlap for a few months — so it is checkable
rather than a matter of trust. That check already earned itself: a futures row leaves
OptnTp empty, pandas reads it as NaN, and NaN is TRUTHY, so `x or "XX"` kept the NaN and
str() made it the literal "nan". Every index future from mid-2024 on was silently dropped —
the exact series the futures work needs.

Network-dependent by nature: it reads NSE's public archive. Skips rather than fails when
the archive cannot be reached, so an offline run does not look like a code fault.

    PYTHONPATH=. .venv/bin/python -m tests.test_derivatives
"""

import datetime as dt
import sys

from swing_screener.marketdata import derivatives as D

OVERLAP = dt.date(2024, 6, 14)      # both layouts are published for this session


def main() -> int:
    bad = []

    legacy = D.fetch_day("india", OVERLAP, "legacy")
    udiff = D.fetch_day("india", OVERLAP, "udiff")
    if not legacy or not udiff:
        print(f"SKIP — NSE's archive is unreachable (legacy {len(legacy)} rows, udiff {len(udiff)})")
        return 0

    # 1. both layouts carry index FUTURES, not just options (the NaN bug)
    for name, rows in (("legacy", legacy), ("udiff", udiff)):
        futidx = [r for r in rows if r[2] == "FUTIDX"]
        if not futidx:
            bad.append(f"{name}: no FUTIDX rows — index futures are being dropped")
        for r in futidx:
            if r[6] != "XX":
                bad.append(f"{name}: a future has option_type {r[6]!r}, expected 'XX'")
                break
        opts = [r for r in rows if r[2] == "OPTIDX"]
        if not opts:
            bad.append(f"{name}: no OPTIDX rows")
        if {r[6] for r in opts} - {"CE", "PE"}:
            bad.append(f"{name}: option_type values beyond CE/PE: {sorted({r[6] for r in opts})[:4]}")

    # 2. the two layouts agree on the same session
    rec = D.reconcile("india", OVERLAP)
    if not rec.get("comparable"):
        bad.append(f"the overlap day is not comparable: {rec.get('note')}")
    else:
        for k in ("only_legacy", "only_udiff", "settle_differs", "open_interest_differs"):
            if rec[k]:
                bad.append(f"layouts disagree on {OVERLAP}: {k}={rec[k]} {rec.get('examples', '')}")

    # 3. the settle is read, and it is not the close. Most contracts do not trade on a given
    #    day; their open/high/low arrive as 0.00 while `close` carries a STALE last-traded
    #    price. The exchange marks them anyway, and that mark is `settle` — so a backtest that
    #    priced off `close` would use old prices on most of the book without noticing.
    untraded = [r for r in legacy if r[2] == "OPTIDX" and (r[12] or 0) == 0]
    if len(untraded) < 100:
        bad.append(f"only {len(untraded)} untraded strikes — cannot check the settle/close distinction")
    else:
        if not any((r[11] or 0) > 0 for r in untraded):
            bad.append("no untraded strike has a settle; the settle column is not being read")
        if not any((r[11] or 0) > 0 and abs((r[11] or 0) - (r[10] or 0)) > 0.01 for r in untraded):
            bad.append("settle never differs from close on an untraded strike — "
                       "one of the two columns is not being read")

    # 4. shape: expiry is a date in the future of the trade date, strike positive for options
    for r in legacy[:2000]:
        if r[4] is None or r[4] < r[1]:
            bad.append(f"expiry {r[4]} is not after the trade date {r[1]} for {r[3]}")
            break
        if r[2] == "OPTIDX" and not r[5] > 0:
            bad.append(f"an option has strike {r[5]} ({r[3]} {r[4]})")
            break

    if bad:
        print("FAIL — derivatives bhavcopy:")
        for x in bad:
            print("  " + x)
        return 1
    print(f"OK — both layouts agree on {OVERLAP} ({rec['in_both']:,} contracts, settle and open "
          f"interest identical); futures and options both present; untraded strikes keep a settle")
    return 0


if __name__ == "__main__":
    sys.exit(main())
