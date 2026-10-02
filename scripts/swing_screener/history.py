"""Run history: every full pipeline run gets a timestamped snapshot CSV
(for eyeballing a single run) and an append-only row in Postgres (for
actually comparing across runs — e.g. "what changed since yesterday").
`sector`/`decision`/`price`/`tradeable`/`reason` are real indexed columns
since those drive the diff queries; the full row is also kept as JSONB so
nothing is lost even as output.py's column set evolves.

Usage (standalone, without re-running the pipeline):
    python3 -m swing_screener.history --market india
    python3 -m swing_screener.history --market india --list
    python3 -m swing_screener.history --market india --from 2026-09-30_090000 --to 2026-10-01_090000
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from . import db

REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"
HISTORY_DIR = REPORT_DIR / "history"


def new_run_id() -> str:
    return pd.Timestamp.now().strftime("%Y-%m-%d_%H%M%S")


def record_run(
    market: str, run_id: str, report_df: pd.DataFrame,
    strategy_key: str = "trend_pullback",
) -> Path:
    """Writes a timestamped snapshot CSV and appends to Postgres.
    Returns the snapshot CSV path."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_path = HISTORY_DIR / f"{market}_{strategy_key}_universe_{run_id}.csv"
    report_df.to_csv(snapshot_path, index=False)

    rows = []
    for _, row in report_df.iterrows():
        full_row = {c: db.py_value(row.get(c)) for c in report_df.columns}
        rows.append((
            run_id, market, strategy_key,
            full_row.get("symbol"), full_row.get("sector"), full_row.get("decision"),
            full_row.get("price"), full_row.get("tradeable"), full_row.get("reason"),
            json.dumps(full_row),
        ))

    query = """
        INSERT INTO universe_history
            (run_id, market, strategy, symbol, sector, decision, price, tradeable, reason, full_row)
        VALUES %s
        ON CONFLICT (run_id, market, strategy, symbol) DO UPDATE SET
            sector=EXCLUDED.sector, decision=EXCLUDED.decision, price=EXCLUDED.price,
            tradeable=EXCLUDED.tradeable, reason=EXCLUDED.reason, full_row=EXCLUDED.full_row
    """
    db.execute_values(query, rows)
    return snapshot_path


def list_run_ids(market: str, strategy_key: str = "trend_pullback") -> list[str]:
    conn = db.get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT run_id FROM universe_history WHERE market=%s AND strategy=%s "
            "ORDER BY run_id",
            (market, strategy_key),
        )
        return [r[0] for r in cur.fetchall()]


def diff_decisions(
    market: str, run_a: str, run_b: str, strategy_key: str = "trend_pullback"
) -> pd.DataFrame:
    """Symbols present in both runs whose `decision` changed between them
    (run_a = older, run_b = newer)."""
    conn = db.get_connection()
    cols = [
        "symbol", "sector", "decision_before", "decision_after",
        "price_before", "price_after", "tradeable_before", "tradeable_after", "reason_after",
    ]
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.symbol, a.sector,
                   a.decision AS decision_before, b.decision AS decision_after,
                   a.price AS price_before, b.price AS price_after,
                   a.tradeable AS tradeable_before, b.tradeable AS tradeable_after,
                   b.reason AS reason_after
            FROM universe_history a
            JOIN universe_history b USING (symbol)
            WHERE a.market=%s AND b.market=%s AND a.strategy=%s AND b.strategy=%s
              AND a.run_id=%s AND b.run_id=%s
              AND a.decision IS DISTINCT FROM b.decision
            ORDER BY b.symbol
            """,
            (market, market, strategy_key, strategy_key, run_a, run_b),
        )
        rows = cur.fetchall()
    return db.rows_to_df(rows, cols)


def universe_changes(
    market: str, run_a: str, run_b: str, strategy_key: str = "trend_pullback"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(newly_present, dropped) — symbols that entered/left the filtered
    universe between the two runs (e.g. started/stopped passing the loose
    screener filter)."""
    conn = db.get_connection()
    cols = ["symbol", "sector", "decision"]
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT symbol, sector, decision FROM universe_history
            WHERE market=%s AND strategy=%s AND run_id=%s
              AND symbol NOT IN (
                  SELECT symbol FROM universe_history
                  WHERE market=%s AND strategy=%s AND run_id=%s)
            ORDER BY symbol
            """,
            (market, strategy_key, run_b, market, strategy_key, run_a),
        )
        new = db.rows_to_df(cur.fetchall(), cols)
        cur.execute(
            """
            SELECT symbol, sector, decision FROM universe_history
            WHERE market=%s AND strategy=%s AND run_id=%s
              AND symbol NOT IN (
                  SELECT symbol FROM universe_history
                  WHERE market=%s AND strategy=%s AND run_id=%s)
            ORDER BY symbol
            """,
            (market, strategy_key, run_a, market, strategy_key, run_b),
        )
        dropped = db.rows_to_df(cur.fetchall(), cols)
    return new, dropped


def print_diff(
    market: str, run_a: str, run_b: str, strategy_key: str = "trend_pullback"
) -> None:
    changes = diff_decisions(market, run_a, run_b, strategy_key)
    new_syms, dropped_syms = universe_changes(market, run_a, run_b, strategy_key)

    print(f"=== Changes: {run_a} -> {run_b} ({market}/{strategy_key}) ===")
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
    parser.add_argument("--strategy", default="trend_pullback")
    parser.add_argument("--list", action="store_true", help="list recorded run ids and exit")
    parser.add_argument("--from", dest="run_a", default=None, help="older run id (default: 2nd-to-last)")
    parser.add_argument("--to", dest="run_b", default=None, help="newer run id (default: latest)")
    args = parser.parse_args()

    runs = list_run_ids(args.market, args.strategy)
    if args.list or len(runs) < 2:
        print(f"{len(runs)} recorded run(s) for {args.market}:")
        for r in runs:
            print(f"  {r}")
        if len(runs) < 2 and not args.list:
            print("\nNeed at least 2 runs to diff.")
        return

    run_a = args.run_a or runs[-2]
    run_b = args.run_b or runs[-1]
    print_diff(args.market, run_a, run_b, args.strategy)


if __name__ == "__main__":
    main()
