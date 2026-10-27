"""Keep the backtest signal cache (`backtest_signals`) to the rule sets that can still use it.

Every per-symbol backtest writes one row per symbol per scanned bar, keyed by the strategy's spec id,
so a run on a new version scans afresh and leaves the old version's rows behind. Nothing ever removed
them: by 2026-10-27 the table held 172 GB across 90 spec ids, only ~13% of it for the current rules,
and the disk filled -- every queued job then failed at start writing its log.

`prune` keeps, per strategy, the rows of its CURRENT version and the one BEFORE it (KEEP_VERSIONS),
every spec id of those versions included -- `--const` variants and the cached rows a `signal_version`
pin carries forward. The version before is kept because the next run of a post-scan-only bump copies
from it (backtest.seed_signal_cache). Rows of an older version, or of a strategy no longer registered,
are deleted. What that costs: the trade-anatomy chart of a run made on a pruned version can no longer
draw the structure the strategy saw (its trades, P&L and report are untouched), and a backtest of a
pruned version would rescan.

A DELETE does not hand space back to the operating system: Postgres keeps it for its own reuse, so the
VACUUM that follows stops the table growing rather than shrinking the file. Run weekly (jobs/registry.py
`prune_signals`), that keeps the table near its working size.

    PYTHONPATH=. python3 -m swing_screener.backtesting.signal_cache            # report what would go
    PYTHONPATH=. python3 -m swing_screener.backtesting.signal_cache --apply    # and delete it
"""

import argparse
import logging

from ..marketdata import db

logger = logging.getLogger(__name__)

KEEP_VERSIONS = 2     # the current version and the one before it


def kept_versions() -> dict[str, set[str]]:
    """strategy key -> the version numbers whose cached rows are kept."""
    from ..strategies import get_strategy, list_strategies
    out = {}
    for key in list_strategies():
        cls = type(get_strategy(key))
        versions = [str(cls.version)] + [str(e[0]) for e in (getattr(cls, "changelog", None) or ())]
        seen: list[str] = []
        for v in versions:                       # changelog is newest first; the current version leads
            if v not in seen:
                seen.append(v)
        out[key] = set(seen[:KEEP_VERSIONS])
    return out


def _version_of(spec_id: str) -> str:
    return spec_id.split("-")[0].lstrip("v")


def plan() -> list[tuple[str, str, bool]]:
    """(strategy, spec_id, keep) for every spec id stored, from its distinct keys -- not a table scan."""
    keep = kept_versions()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT DISTINCT strategy, spec_id FROM backtest_signals")
        rows = cur.fetchall()
    return [(s, sp, s in keep and _version_of(sp or "") in keep[s]) for s, sp in rows]


def prune(apply: bool = False) -> dict:
    """Delete the rows of every spec id outside kept_versions(), then VACUUM. Returns the counts."""
    p = plan()
    drop = [(s, sp) for s, sp, k in p if not k]
    deleted = 0
    if apply:
        conn = db.get_connection()
        with conn.cursor() as cur:
            for s, sp in drop:
                cur.execute("DELETE FROM backtest_signals WHERE strategy=%s AND spec_id IS NOT DISTINCT FROM %s", (s, sp))
                deleted += cur.rowcount
                logger.info("pruned %s %s: %d rows", s, sp, cur.rowcount)
        if drop:
            prev = conn.autocommit
            conn.autocommit = True               # VACUUM cannot run inside a transaction
            try:
                with conn.cursor() as cur:
                    cur.execute("VACUUM ANALYZE backtest_signals")
            finally:
                conn.autocommit = prev
    return {"spec_ids": len(p), "kept": len(p) - len(drop), "dropped": len(drop), "rows_deleted": deleted,
            "dropped_ids": [f"{s} {sp}" for s, sp in drop]}


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="delete (default: report only)")
    r = prune(apply=ap.parse_args(argv).apply)
    print(f"{r['spec_ids']} spec ids stored: keep {r['kept']}, drop {r['dropped']}"
          + (f" ({r['rows_deleted']} rows deleted)" if r["rows_deleted"] else ""))
    for x in r["dropped_ids"]:
        print("  drop", x)


if __name__ == "__main__":
    main()
