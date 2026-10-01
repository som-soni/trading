"""Run history: every full pipeline run gets a timestamped snapshot CSV
(for eyeballing a single run) and an append-only row in a local DuckDB
file (for actually comparing across runs — e.g. "what changed since
yesterday"). Single local file, no server, same philosophy as the parquet
price cache.

Usage (standalone, without re-running the pipeline):
    python3 -m swing_screener.history --market india
    python3 -m swing_screener.history --market india --list
    python3 -m swing_screener.history --market india --from 2026-09-30_090000 --to 2026-10-01_090000
"""

import argparse
from pathlib import Path

import duckdb
import pandas as pd

REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"
HISTORY_DIR = REPORT_DIR / "history"
DB_PATH = REPORT_DIR / "history.duckdb"
TABLE = "universe_history"


def new_run_id() -> str:
    return pd.Timestamp.now().strftime("%Y-%m-%d_%H%M%S")


def _connect() -> duckdb.DuckDBPyConnection:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))


def _ensure_schema(con: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> None:
    """Create the table on first use, or add any new columns the report
    has grown since the table was created — so evolving output.py's
    column set doesn't break older history."""
    exists = con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [TABLE]
    ).fetchone()[0]
    if not exists:
        con.register("seed", df.iloc[0:0])
        con.execute(f"CREATE TABLE {TABLE} AS SELECT * FROM seed")
        return
    # PRAGMA table_info columns are (cid, name, type, notnull, dflt_value, pk) —
    # name is row[1], not row[0] (that's just the ordinal position)
    existing_cols = {
        row[1] for row in con.execute(f"PRAGMA table_info('{TABLE}')").fetchall()
    }
    for col in df.columns:
        if col not in existing_cols:
            con.execute(f'ALTER TABLE {TABLE} ADD COLUMN "{col}" VARCHAR')


def record_run(market: str, run_id: str, report_df: pd.DataFrame) -> Path:
    """Writes a timestamped snapshot CSV and appends to the history DB.
    Returns the snapshot CSV path."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_path = HISTORY_DIR / f"{market}_universe_{run_id}.csv"
    report_df.to_csv(snapshot_path, index=False)

    df = report_df.copy()
    df.insert(0, "run_id", run_id)
    df.insert(1, "market", market)

    con = _connect()
    try:
        _ensure_schema(con, df)
        con.register("new_rows", df)
        # BY NAME matches columns by name (filling any table columns the
        # new run doesn't have with NULL) instead of positionally — matters
        # once the report schema has grown since a column was last changed
        con.execute(f"INSERT INTO {TABLE} BY NAME SELECT * FROM new_rows")
    finally:
        con.close()
    return snapshot_path


def list_run_ids(market: str) -> list[str]:
    con = _connect()
    try:
        exists = con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [TABLE]
        ).fetchone()[0]
        if not exists:
            return []
        rows = con.execute(
            f"SELECT DISTINCT run_id FROM {TABLE} WHERE market = ? ORDER BY run_id", [market]
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        con.close()


def diff_decisions(market: str, run_a: str, run_b: str) -> pd.DataFrame:
    """Symbols present in both runs whose `decision` changed between them
    (run_a = older, run_b = newer)."""
    con = _connect()
    try:
        return con.execute(
            f"""
            SELECT a.symbol, a.sector,
                   a.decision AS decision_before, b.decision AS decision_after,
                   a.price AS price_before, b.price AS price_after,
                   a.tradeable AS tradeable_before, b.tradeable AS tradeable_after,
                   b.reason AS reason_after
            FROM {TABLE} a
            JOIN {TABLE} b USING (symbol)
            WHERE a.market = ? AND b.market = ? AND a.run_id = ? AND b.run_id = ?
              AND a.decision != b.decision
            ORDER BY b.symbol
            """,
            [market, market, run_a, run_b],
        ).df()
    finally:
        con.close()


def universe_changes(market: str, run_a: str, run_b: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(newly_present, dropped) — symbols that entered/left the filtered
    universe between the two runs (e.g. started/stopped passing the loose
    screener filter)."""
    con = _connect()
    try:
        new = con.execute(
            f"""
            SELECT symbol, sector, decision FROM {TABLE}
            WHERE market = ? AND run_id = ?
              AND symbol NOT IN (SELECT symbol FROM {TABLE} WHERE market = ? AND run_id = ?)
            ORDER BY symbol
            """,
            [market, run_b, market, run_a],
        ).df()
        dropped = con.execute(
            f"""
            SELECT symbol, sector, decision FROM {TABLE}
            WHERE market = ? AND run_id = ?
              AND symbol NOT IN (SELECT symbol FROM {TABLE} WHERE market = ? AND run_id = ?)
            ORDER BY symbol
            """,
            [market, run_a, market, run_b],
        ).df()
        return new, dropped
    finally:
        con.close()


def print_diff(market: str, run_a: str, run_b: str) -> None:
    changes = diff_decisions(market, run_a, run_b)
    new_syms, dropped_syms = universe_changes(market, run_a, run_b)

    print(f"=== Changes: {run_a} -> {run_b} ({market}) ===")
    if changes.empty:
        print("No decision changes for symbols present in both runs.")
    else:
        print(changes.to_string(index=False))
    if not new_syms.empty:
        print(f"\nNewly in filtered universe ({len(new_syms)}): {', '.join(new_syms['symbol'])}")
    if not dropped_syms.empty:
        print(f"\nDropped from filtered universe ({len(dropped_syms)}): {', '.join(dropped_syms['symbol'])}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Diff pipeline runs over time")
    parser.add_argument("--market", required=True)
    parser.add_argument("--list", action="store_true", help="list recorded run ids and exit")
    parser.add_argument("--from", dest="run_a", default=None, help="older run id (default: 2nd-to-last)")
    parser.add_argument("--to", dest="run_b", default=None, help="newer run id (default: latest)")
    args = parser.parse_args()

    runs = list_run_ids(args.market)
    if args.list or len(runs) < 2:
        print(f"{len(runs)} recorded run(s) for {args.market}:")
        for r in runs:
            print(f"  {r}")
        if len(runs) < 2 and not args.list:
            print("\nNeed at least 2 runs to diff.")
        return

    run_a = args.run_a or runs[-2]
    run_b = args.run_b or runs[-1]
    print_diff(args.market, run_a, run_b)


if __name__ == "__main__":
    main()
