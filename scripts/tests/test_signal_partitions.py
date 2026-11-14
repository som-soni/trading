"""The partitioned signal cache: migration, a rule set's table made on demand, prune dropping tables.

Runs on temporary tables shaped like `backtest_signals` (the real table is only read for its column
definitions). Temporary, too, because VACUUM truncates a temp table whatever other sessions' transactions
hold back -- a weekly prune running beside the test would otherwise stop the migration part.

  - signal_migrate moves an unpartitioned table, tail first in small chunks, with every row kept, into
    one table per (strategy, spec id), and drops the emptied legacy table;
  - ensure_signal_partition is idempotent, and a write to a new rule set lands in its own table;
  - signal_cache.prune drops the tables of rule sets it does not keep (an unregistered strategy's,
    with the strategy's own table) and leaves the kept ones' rows untouched -- an unregistered strategy's
    old runs never keep its rows as a "better run";
  - on a table not yet partitioned, prune still deletes the rows.

Run:  PYTHONPATH=. .venv/bin/python -m tests.test_signal_partitions
"""

import sys

from swing_screener.backtesting import signal_cache, signal_migrate
from swing_screener.marketdata import db
from swing_screener.strategies import get_strategy

T = "pg_temp.zz_signals"
KEPT = ("donchian", get_strategy("donchian").spec_id())
OLD = ("zz_unregistered", "v0.1-00000000")
OLDER_KEPT_STRATEGY = ("donchian", "v0.0-00000000")   # donchian, but a version long gone


def _q(sql, args=None):
    with db.get_connection().cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall() if cur.description else cur.rowcount


def _make(table: str, rows_each: int) -> None:
    _q(f"CREATE TABLE {table} (LIKE public.backtest_signals INCLUDING DEFAULTS, "
       f"PRIMARY KEY (market, strategy, symbol, date, spec_id))")
    for s, sp in (KEPT, OLD, OLDER_KEPT_STRATEGY):
        _q(f"""INSERT INTO {table} (market, strategy, symbol, date, hard_gates_passed, has_setup, spec_id, extras)
               SELECT 'us', %s, 'S' || (g %% 50), date '2015-01-01' + (g / 50), g %% 3 = 0, false, %s,
                      jsonb_build_object('pad', repeat('x', 400), 'g', g)
               FROM generate_series(1, %s) g""", (s, sp, rows_each))


def _counts(table: str) -> dict:
    return {(s, sp): n for s, sp, n in _q(f"SELECT strategy, spec_id, count(*) FROM {table} GROUP BY 1, 2")}


def run() -> list[str]:
    problems = []
    check = lambda ok, msg: ok or problems.append(msg)  # noqa: E731

    # --- migration ---
    _make(T, 1500)
    before = _counts(T)
    blocks = _q(f"SELECT pg_relation_size('{T}') / 8192")[0][0]
    r = signal_migrate.migrate(apply=True, table=T, chunk_blocks=max(1, blocks // 8), check_jobs=False, min_free_gb=0)
    check(r["partitioned"] and not r["legacy"], f"migration did not finish: {r}")
    check(_counts(T) == before, f"rows changed in the migration: {before} -> {_counts(T)}")
    leaves = {(s, sp) for s, sp, _, _ in db.signal_leaves(T)}
    check(leaves == set(before), f"one table per rule set expected, got {leaves}")
    check(_q(f"SELECT to_regclass('{T}_legacy')")[0][0] is None, "the legacy table was not dropped")
    pk = _q(f"SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = '{T}'::regclass AND contype = 'p'")
    check(pk and "spec_id" in pk[0][0], f"the partitioned table lost its key: {pk}")
    check(signal_migrate.migrate(apply=True, table=T, check_jobs=False, min_free_gb=0)["partitioned"],
          "a re-run of a finished migration failed")

    # --- a new rule set gets its table on demand, once ---
    new = ("donchian", "v9.9-99999999")
    db.ensure_signal_partition(*new, table=T)
    db._SIGNAL_PARTS.clear()
    db.ensure_signal_partition(*new, table=T)
    _q(f"""INSERT INTO {T} (market, strategy, symbol, date, hard_gates_passed, has_setup, spec_id)
           VALUES ('us', %s, 'X', '2020-01-01', true, false, %s)
           ON CONFLICT (market, strategy, symbol, date, spec_id) DO UPDATE SET spec_id = EXCLUDED.spec_id""", new)
    check(_counts(T).get(new) == 1, "a row of a new rule set did not land")
    check(sum(1 for s, sp, *_ in db.signal_leaves(T) if (s, sp) == new) == 1, "the new rule set has two tables")

    # --- prune drops tables ---
    kept_before = _counts(T)[KEPT]
    r = signal_cache.prune(apply=True, table=T)
    left = {(s, sp) for s, sp, _, _ in db.signal_leaves(T)}
    check(KEPT in left and _counts(T).get(KEPT) == kept_before, f"a kept rule set lost rows: {r}")
    check(OLD not in left and OLDER_KEPT_STRATEGY not in left and new not in left, f"not dropped: {left}")
    check(r["gb_freed"] >= 0 and r["dropped"] == 3, f"prune report: {r}")
    mids = _q(f"SELECT pg_get_expr(c.relpartbound, c.oid) FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid "
              f"WHERE i.inhparent = '{T}'::regclass")
    check(not any(OLD[0] in m for (m,) in mids), f"the unregistered strategy's table is left: {mids}")

    # --- an unregistered strategy's old runs never count as "better" (it has no kept rule set to beat) ---
    from swing_screener.strategies import list_strategies
    gone = {(s, sp) for s, sp in _q("SELECT DISTINCT strategy, spec_id FROM report_runs "
                                    "WHERE kind = 'backtest' AND spec_id IS NOT NULL")
            if s not in set(list_strategies())}
    kept_gone = signal_cache.better_runs(gone, set())
    check(not kept_gone, f"better_runs keeps an unregistered strategy's rule sets: {sorted(kept_gone)[:3]}")

    # --- an unpartitioned table still prunes by DELETE ---
    U = "pg_temp.zz_unpartitioned"
    _make(U, 50)
    r = signal_cache.prune(apply=True, table=U)
    check(set(_counts(U)) == {KEPT} and r["rows_deleted"] == 100, f"unpartitioned prune: {r}, {_counts(U)}")
    return problems


def main() -> int:
    try:
        problems = run()
    finally:
        _q(f"DROP TABLE IF EXISTS {T}, {T}_legacy, pg_temp.zz_unpartitioned CASCADE")
        db._SIGNAL_PARTS.clear()
    if problems:
        print("FAIL —\n " + "\n ".join(problems))
        return 1
    print("OK — migration keeps every row, rule sets get their own tables, prune drops them")
    return 0


if __name__ == "__main__":
    sys.exit(main())
