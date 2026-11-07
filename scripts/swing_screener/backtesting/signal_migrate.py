"""Move the signal cache (`backtest_signals`) onto its partitioned form without a second copy on disk.

Pruning an unpartitioned table frees space only for Postgres to reuse (backtesting/signal_cache.py); a
VACUUM FULL would need room for a copy of every kept row, and on 2026-11-07 the disk had ~22 GB free
beside a 234 GB table. A plain VACUUM does return the pages at the END of a file. So the rows move
tail first:

  1. the old table is renamed `backtest_signals_legacy`, and a partitioned `backtest_signals` (strategy,
     then spec id: marketdata/db.py `ensure_signal_partition`) takes its name, with a table per rule set;
  2. legacy's primary key is dropped -- nothing reads legacy by key any more, and it is 13 GB of disk
     and a slower VACUUM each step;
  3. repeatedly: the rows in legacy's last CHUNK_GB of pages are copied into the new table and deleted
     from legacy in one transaction, then a VACUUM cuts those pages off the file -- the disk gives back
     about what the copy took;
  4. legacy, empty, is dropped.

Every row present moves; which rule sets to keep stays signal_cache.prune's decision. Each step is one
transaction, so an interruption loses nothing and a re-run resumes where it stopped. It stops between
steps when free disk falls below MIN_FREE_GB, and refuses to start while a job is running (stop the job
worker first: a backtest writing or reading the cache mid-move would miss rows still in legacy), or while
another session holds a long transaction (VACUUM could not truncate behind it).

    PYTHONPATH=. python3 -m swing_screener.backtesting.signal_migrate                  # report only
    PYTHONPATH=. python3 -m swing_screener.backtesting.signal_migrate --apply          # migrate
    PYTHONPATH=. python3 -m swing_screener.backtesting.signal_migrate --apply --max-steps 1   # one chunk
"""

import argparse
import logging
import os
import shutil
import socket
import time

from .. import paths
from ..marketdata import db

logger = logging.getLogger(__name__)

CHUNK_GB = 4          # pages of legacy moved per step: the most the disk ever holds twice
MIN_FREE_GB = 8       # stop between steps below this much free disk
LEGACY_SUFFIX = "_legacy"
_KEY = "market, strategy, symbol, date, spec_id"


def _free_gb() -> float:
    return shutil.disk_usage(paths.REPO_ROOT).free / 1e9


def _exists(cur, name: str) -> bool:
    cur.execute("SELECT to_regclass(%s) IS NOT NULL", (name,))
    return cur.fetchone()[0]


def _blocks(cur, name: str) -> int:
    cur.execute("SELECT pg_relation_size(%s::regclass) / current_setting('block_size')::int", (name,))
    return cur.fetchone()[0]


def _running_jobs(cur) -> list[tuple]:
    """Runs on this host whose process is alive (job_runs keeps rows of runs that died as 'running')."""
    try:
        cur.execute("SELECT id, job, pid FROM job_runs WHERE status='running' AND host=%s AND pid <> %s",
                    (socket.gethostname(), os.getpid()))
        rows = cur.fetchall()
    except Exception:  # noqa: BLE001 — no run log: nothing is recorded as running
        return []
    return [r for r in rows if r[2] and db._pid_alive(r[2])]


def _old_transactions(cur, older_than_s: int = 60) -> list[tuple]:
    """Other sessions with a transaction open longer than `older_than_s`: while one is, VACUUM cannot
    remove rows deleted after it began, so it cannot truncate the file (the weekly prune's DELETEs did
    exactly that to the first test run)."""
    cur.execute("""SELECT pid, now() - xact_start, left(query, 80) FROM pg_stat_activity
                   WHERE pid <> pg_backend_pid() AND (backend_xmin IS NOT NULL OR backend_xid IS NOT NULL)
                     AND xact_start < now() - make_interval(secs => %s)""", (older_than_s,))
    return cur.fetchall()


def state(table: str = db.SIGNALS) -> dict:
    legacy = table + LEGACY_SUFFIX
    with db.get_connection().cursor() as cur:
        out = {"partitioned": db.signals_partitioned(cur, table), "legacy": _exists(cur, legacy),
               "free_gb": round(_free_gb(), 1)}
        if out["legacy"]:
            cur.execute("SELECT pg_total_relation_size(%s::regclass)", (legacy,))
            out["legacy_gb"] = round(cur.fetchone()[0] / 1e9, 1)
        elif not out["partitioned"] and _exists(cur, table):
            cur.execute("SELECT pg_total_relation_size(%s::regclass)", (table,))
            out["table_gb"] = round(cur.fetchone()[0] / 1e9, 1)
        out["rule_sets"] = len(db.signal_leaves(table))
    return out


def _start(cur, table: str, legacy: str) -> None:
    """Step 1: rename the old table aside and put the partitioned one in its place, one transaction."""
    cur.execute(f"SELECT DISTINCT strategy, spec_id FROM {table}")
    keys = cur.fetchall()
    schema, name = (table.split(".", 1) if "." in table else (None, table))
    cur.execute("BEGIN")
    try:
        cur.execute(f"ALTER TABLE {table} RENAME TO {name}{LEGACY_SUFFIX}")
        cur.execute(f"ALTER INDEX IF EXISTS {(schema + '.') if schema else ''}{name}_pkey "
                    f"RENAME TO {name}{LEGACY_SUFFIX}_pkey")
        cur.execute(f"CREATE TABLE {table} (LIKE {legacy} INCLUDING DEFAULTS, PRIMARY KEY ({_KEY})) "
                    f"PARTITION BY LIST (strategy)")
        cur.execute("COMMIT")
    except Exception:
        cur.execute("ROLLBACK")
        raise
    for s, sp in keys:
        db.ensure_signal_partition(s, sp, table)
    logger.info("partitioned %s: %d rule sets; the old rows are in %s", table, len(keys), legacy)


def _move(cur, table: str, legacy: str, first_block: int) -> tuple[int, int]:
    """Copy legacy's rows from `first_block` on into the new table and delete them, one transaction.
    A row whose key the new table already holds is not copied over it (a re-run, or a write made after
    the switch -- the newer reading wins); either way the key is held, so no rule set loses a row."""
    rng = f"ctid >= '({first_block},0)'::tid"
    for attempt in range(2):
        cur.execute("BEGIN")
        try:
            cur.execute(f"INSERT INTO {table} SELECT * FROM {legacy} WHERE {rng} ON CONFLICT ({_KEY}) DO NOTHING")
            moved = cur.rowcount
            cur.execute(f"DELETE FROM {legacy} WHERE {rng}")
            deleted = cur.rowcount
            cur.execute("COMMIT")
            return moved, deleted
        except Exception as exc:
            cur.execute("ROLLBACK")
            if attempt or "no partition" not in str(exc):
                raise
            # a rule set written after step 1 listed them: give it its table and try again
            cur.execute(f"SELECT DISTINCT strategy, spec_id FROM {legacy} WHERE {rng}")
            for s, sp in cur.fetchall():
                db.ensure_signal_partition(s, sp, table)
    raise AssertionError("unreachable")


def migrate(apply: bool = False, table: str = db.SIGNALS, chunk_blocks: int | None = None,
            max_steps: int | None = None, min_free_gb: float = MIN_FREE_GB, check_jobs: bool = True) -> dict:
    legacy = table + LEGACY_SUFFIX
    st = state(table)
    if not apply or (st["partitioned"] and not st["legacy"]):
        return st
    conn = db.get_connection()
    chunk = chunk_blocks or CHUNK_GB * 10**9 // 8192
    with conn.cursor() as cur:
        if check_jobs and (jobs := _running_jobs(cur)):
            raise SystemExit(f"jobs still running (stop the job worker first): {jobs}")
        if check_jobs and (old := _old_transactions(cur)):
            raise SystemExit(f"long transactions open (VACUUM could not truncate behind them): {old}")
        if not st["partitioned"]:
            _start(cur, table, legacy)
        cur.execute(f"ALTER TABLE {legacy} DROP CONSTRAINT IF EXISTS {legacy.split('.')[-1]}_pkey")
        steps = 0
        while (n := _blocks(cur, legacy)) > 0:
            if max_steps is not None and steps >= max_steps:
                logger.info("stopped after %d step(s): %d blocks left in %s", steps, n, legacy)
                return state(table) | {"steps": steps}
            if (free := _free_gb()) < min_free_gb:
                raise SystemExit(f"stopped: {free:.1f} GB free, below {min_free_gb} GB; {n} blocks left in {legacy}")
            t0 = time.time()
            first = max(0, n - chunk)
            moved, deleted = _move(cur, table, legacy, first)
            cur.execute(f"VACUUM {legacy}")         # truncates the now-empty tail
            left = _blocks(cur, legacy)
            if left > first:
                # VACUUM could not truncate (it gives up on a conflicting lock): one retry, else stop
                # rather than loop over the same empty pages
                cur.execute(f"VACUUM {legacy}")
                if (left := _blocks(cur, legacy)) > first:
                    raise SystemExit(f"stopped: VACUUM did not truncate {legacy} below block {first}; "
                                     f"transactions holding it back: {_old_transactions(cur, 0)}. Re-run to resume")
            steps += 1
            logger.info("step %d: moved %d rows (%d deleted) from blocks %d..%d in %.0fs; %d blocks left, %.1f GB free",
                        steps, moved, deleted, first, n, time.time() - t0, left, _free_gb())
        cur.execute(f"SELECT count(*) FROM {legacy}")
        if cur.fetchone()[0] == 0:
            cur.execute(f"DROP TABLE {legacy}")
            logger.info("dropped %s: the migration is complete", legacy)
        cur.execute(f"ANALYZE {table}")
    return state(table)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="migrate (default: report the state only)")
    ap.add_argument("--max-steps", type=int, help="stop after this many chunks (re-run to resume)")
    a = ap.parse_args(argv)
    print(migrate(apply=a.apply, max_steps=a.max_steps))


if __name__ == "__main__":
    main()
