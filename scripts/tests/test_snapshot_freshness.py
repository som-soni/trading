"""The snapshot's staleness check must stay honest as the snapshot grows.

`screens/snapshot.py` copies fundamentals, peer RS, classification and earnings into the
daily snapshot. That is deliberate — they have no history of their own, so the snapshot is
the only point-in-time record of them — but it means a source that lands afterwards leaves
the columns it feeds wrong until the next build, with nothing in the data to show it. That
is how "Minervini leaders in Stage 2" came to return 0 while six US stocks qualified.

`stale_inputs` compares each source's last write against the snapshot file. It is only
useful if it stays complete and cheap, so this checks:

  * every source names columns that really are present-only, and every present-only column
    that comes from a source is claimed by one — a new field must not slip in unwatched;
  * a source whose table is missing is skipped, not reported (no false staleness);
  * the check is fast enough to run on every request;
  * a past snapshot is never called stale — its inputs having moved on is the point.

    PYTHONPATH=. .venv/bin/python -m tests.test_snapshot_freshness
"""

import sys
import time

from swing_screener.config import MARKETS
from swing_screener.screens import snapshot as S

BUDGET_MS = 250        # generous: it runs per request, and a cold DB connection is most of it

# present-only columns that no source feeds, with why they are exempt
NOT_FROM_A_SOURCE = {
    "sub_industry",     # data/sub_industries.csv, hand-maintained and effectively static
    "market_cap_usd",   # derived in _add_usd_cap from market_cap (already covered) and the FX rate
}


def main() -> int:
    bad = []

    claimed = {f for _k, _l, fields, _h in S.PRESENT_INPUTS for f in fields}

    # 1. every claimed column is real and present-only
    for key, _label, fields, _how in S.PRESENT_INPUTS:
        for f in fields:
            if f not in S.PRESENT_ONLY:
                bad.append(f"PRESENT_INPUTS[{key}] names {f!r}, which is not in PRESENT_ONLY")
            if f not in S.FIELD_KEYS:
                bad.append(f"PRESENT_INPUTS[{key}] names {f!r}, which is not a snapshot field")

    # 2. every present-only column is claimed, or explicitly exempt
    for f in S.PRESENT_ONLY:
        if f not in claimed and f not in NOT_FROM_A_SOURCE:
            bad.append(f"{f!r} is present-only but no PRESENT_INPUTS source claims it — "
                       f"staleness will never be reported for it (add it, or to NOT_FROM_A_SOURCE)")
    for f in NOT_FROM_A_SOURCE:
        if f in claimed:
            bad.append(f"{f!r} is exempt in this test but a source now claims it — drop the exemption")

    # 3. the two source lists stay distinct: a key in both would be reported twice, and a
    #    whole-snapshot source listed in PRESENT_INPUTS would be asked for fields it has none of
    overlap = set(S.WHOLE_SNAPSHOT_SOURCES) & {k for k, *_ in S.PRESENT_INPUTS}
    if overlap:
        bad.append(f"{sorted(overlap)} is in both WHOLE_SNAPSHOT_SOURCES and PRESENT_INPUTS")
    if not S.WHOLE_SNAPSHOT_SOURCES:
        bad.append("WHOLE_SNAPSHOT_SOURCES is empty — newer prices would no longer be reported")

    # 4. a source we cannot read is skipped, never reported as stale
    if S._source_changed_at("us", ("sql", "SELECT max(x) FROM a_table_that_does_not_exist")) is not None:
        bad.append("an unreadable source must return None, not a timestamp")

    for market in MARKETS:
        ds = S.dates(market)
        if not ds:
            print(f"  {market}: no snapshots — skipped")
            continue

        # 4. shape, and cheap enough to run on every request
        S.stale_inputs(market)                      # warm the connection, as a live server's would be
        t = time.time()
        stale = S.stale_inputs(market)
        ms = (time.time() - t) * 1000
        if ms > BUDGET_MS:
            bad.append(f"{market}: stale_inputs took {ms:.0f}ms, over the {BUDGET_MS}ms budget for a per-request check")
        # Not every source feeds particular present-only columns: newer PRICES make the whole
        # snapshot stale. SOURCE_KEYS is the module's own list of what it may emit, so this
        # still catches a key invented in stale_inputs and never declared.
        for x in stale:
            if x["key"] not in S.SOURCE_KEYS:
                bad.append(f"{market}: reported source {x['key']!r}, which is in neither "
                           f"PRESENT_INPUTS nor WHOLE_SNAPSHOT_SOURCES")
            if not (x["changed_at"] > x["built_at"]):
                bad.append(f"{market}: reported {x['key']} stale but changed_at {x['changed_at']} <= built_at {x['built_at']}")

        # 5. a past snapshot is a record, not something to be called out of date
        if len(ds) > 1 and S.stale_inputs(market, ds[0]):
            bad.append(f"{market}: the oldest snapshot ({ds[0]}) was reported stale; past snapshots are records")

        print(f"  {market}: {len(stale)} stale of {len(S.SOURCE_KEYS)} sources, {ms:.0f}ms"
              + (f" — {', '.join(x['key'] for x in stale)}" if stale else ""))

    if bad:
        print("FAIL — snapshot freshness:")
        for x in bad:
            print("  " + x)
        return 1
    print(f"OK — {len(S.SOURCE_KEYS)} sources ({len(S.PRESENT_INPUTS)} feeding named fields, "
          f"{len(S.WHOLE_SNAPSHOT_SOURCES)} making the whole snapshot stale) cover {len(claimed)} fields, "
          f"unreadable sources are skipped, past snapshots are never stale")
    return 0


if __name__ == "__main__":
    sys.exit(main())
