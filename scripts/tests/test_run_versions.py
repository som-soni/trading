"""A backtest result must always say which rule set produced it.

The only link between a stored report and the rules behind it is the spec_id the
backtester stamps into the run directory name, which ingest lifts into
report_runs.spec_id and the Strategies page groups by. That link is a naming
convention between two modules that do not import each other, so it can break
silently: rename the run directory and every result quietly becomes unattributable.

This ties the two ends together — the id each strategy produces must be the id the
parser recovers — and checks that what is already stored is attributed.

    PYTHONPATH=. .venv/bin/python -m tests.test_run_versions
"""

import re
import sys

from swing_screener.marketdata import db
from swing_screener.strategies import all_specs
from swing_screener.web.ingest import spec_id_of
from swing_screener.web.server import _run_versions


def main() -> int:
    bad = []

    # 1. the producer and the parser agree, for every strategy and every suffix the
    #    backtester appends after the spec id
    for key, cls in sorted(all_specs().items()):
        sid = cls.spec_id()
        if not re.fullmatch(r"v\d+(?:\.\d+)*-[0-9a-f]{8}", sid):
            bad.append(f"{key}: spec_id {sid!r} is not v<version>-<8 hex>")
            continue
        for tail in ("", "_NO-SIGNALS"):
            run = f"2013-01-01_{key}-sma50_rankrs_spec_TOT_{sid}{tail}"
            got = spec_id_of(run)
            if got != sid:
                bad.append(f"{key}: spec_id_of({run!r}) gave {got!r}, not {sid!r}")

    # 2. a name with no stamp is reported as unknown rather than guessed at
    if spec_id_of("2013-01-01_minervini-sma50_rankrs_spec_TOT") is not None:
        bad.append("an unstamped run name must give None, not a made-up version")

    # 3. what is stored is attributed
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT strategy, run_name, spec_id FROM report_runs WHERE kind='backtest'")
        rows = cur.fetchall()
    missing = [(s, r) for s, r, sid in rows if not sid]
    if missing:
        bad.append(f"{len(missing)} stored backtest(s) have no spec_id, e.g. {missing[0][1]}")
    for strat, run, sid in rows:
        if sid and sid != spec_id_of(run):
            bad.append(f"{strat}: stored spec_id {sid!r} disagrees with its run name {run!r}")

    # 4. the page's grouping: counts add up, the current spec is always offered, and a
    #    version covering two fingerprints is flagged rather than silently merged
    for key in sorted(all_specs()):
        d = {"changelog": [{"version": c[0], "date": c[1], "change": c[2]}
                           for c in (all_specs()[key].changelog or ())],
             "spec_id": all_specs()[key].spec_id(),
             "backtests": [{"spec_id": sid} for s, _r, sid in rows if s == key]}
        vs = _run_versions(d)
        if sum(v["runs"] for v in vs) != len([1 for s, _r, sid in rows if s == key and sid]):
            bad.append(f"{key}: version run counts do not add up to the stored runs")
        if not any(v["is_current"] for v in vs):
            bad.append(f"{key}: the current spec is not among the versions offered")
        by_version: dict[str, set] = {}
        for v in vs:
            by_version.setdefault(v["version"], set()).add(v["spec_id"])
        for v in vs:
            want = len(by_version[v["version"]]) > 1
            if v["ambiguous"] != want:
                bad.append(f"{key} {v['spec_id']}: ambiguous={v['ambiguous']}, expected {want}")

    if bad:
        print("FAIL — run versions:")
        for x in bad:
            print("  " + x)
        return 1
    stamped = len([1 for _s, _r, sid in rows if sid])
    print(f"OK — {len(all_specs())} strategies stamp a parseable spec id; "
          f"{stamped} of {len(rows)} stored backtests are attributed to one")
    return 0


if __name__ == "__main__":
    sys.exit(main())
