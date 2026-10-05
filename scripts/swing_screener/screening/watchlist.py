"""Watchlist: names worth watching, from two sources.

* **screener** — refreshed by every full pipeline run (``history.record_run``
  calls :func:`sync_from_run`). A name is on it when the screener marks it
  ``tradeable`` or ``watchlist_candidate`` — the same rule ``daily.py`` uses
  for its "watchlist candidates" section. Entries are kept per
  (market, strategy): a re-run updates them, and names the strategy no longer
  flags drop off.
* **manual** — added and removed by hand (web UI or this CLI); a screener run
  never touches them.

Removing a screener entry *dismisses* it rather than deleting it, so the next
run doesn't put it straight back; it returns only after it has dropped off the
screen and been flagged again.

    python3 -m swing_screener.screening.watchlist --list
    python3 -m swing_screener.screening.watchlist --add AAPL --market us --note "earnings 28th"
    python3 -m swing_screener.screening.watchlist --remove AAPL --market us
    python3 -m swing_screener.screening.watchlist --sync-latest   # rebuild screener entries from the latest runs
"""

import argparse
import logging

import pandas as pd

from ..marketdata import db

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
    market VARCHAR(16) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    source VARCHAR(16) NOT NULL,           -- manual | screener
    strategy VARCHAR(32) NOT NULL DEFAULT '', -- '' for manual entries
    decision VARCHAR(32),
    reason TEXT,
    setup TEXT,
    entry DOUBLE PRECISION,
    stop DOUBLE PRECISION,
    target_r DOUBLE PRECISION,
    run_id VARCHAR(32),
    note TEXT,
    dismissed BOOLEAN NOT NULL DEFAULT false,
    added_at TIMESTAMPTZ NOT NULL DEFAULT now(),   -- first time this source flagged it
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, symbol, source, strategy)
);
"""

_FIELDS = ("decision", "reason", "strategy_setup", "entry", "stop", "target_r")


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _flagged(rec: dict) -> bool:
    return bool(rec.get("tradeable")) or bool(rec.get("watchlist_candidate"))


def _num(v):
    v = db.py_value(v)
    try:
        return float(v) if v is not None and v != "" else None
    except (TypeError, ValueError):
        return None


def sync_records(market: str, strategy: str, run_id: str, records: list[dict]) -> int:
    """Make the screener entries for (market, strategy) match one run's flagged names.
    Returns how many names are on the list for that strategy afterwards."""
    init_schema()
    flagged = [r for r in records if r.get("symbol") and _flagged(r)]
    rows = [(
        market, r["symbol"], "screener", strategy, db.py_value(r.get("decision")), db.py_value(r.get("reason")),
        db.py_value(r.get("strategy_setup")), _num(r.get("entry")), _num(r.get("stop")), _num(r.get("target_r")), run_id,
    ) for r in flagged]
    conn = db.get_connection()
    with conn.cursor() as cur:
        if rows:
            # upsert keeps added_at (first flagged) and any dismissal; refreshes the plan
            db.execute_values("""
                INSERT INTO watchlist (market, symbol, source, strategy, decision, reason, setup, entry, stop, target_r, run_id)
                VALUES %s
                ON CONFLICT (market, symbol, source, strategy) DO UPDATE SET
                    decision=EXCLUDED.decision, reason=EXCLUDED.reason, setup=EXCLUDED.setup, entry=EXCLUDED.entry,
                    stop=EXCLUDED.stop, target_r=EXCLUDED.target_r, run_id=EXCLUDED.run_id, updated_at=now()
            """, rows)
        # names this strategy no longer flags drop off (and so lose any dismissal)
        cur.execute(
            "DELETE FROM watchlist WHERE source='screener' AND market=%s AND strategy=%s AND run_id IS DISTINCT FROM %s",
            (market, strategy, run_id),
        )
    logger.info("watchlist: %s/%s -> %d screener names (run %s)", market, strategy, len(rows), run_id)
    return len(rows)


def sync_from_run(market: str, strategy: str, run_id: str, report_df: pd.DataFrame) -> int:
    """Called by the pipeline after each full run."""
    return sync_records(market, strategy, run_id, report_df.to_dict("records"))


def sync_latest() -> dict:
    """Rebuild screener entries from the most recent recorded run of each
    (market, strategy) — for backfilling, or after runs made while the
    watchlist didn't exist yet. Idempotent."""
    init_schema()
    conn = db.get_connection()
    out = {}
    with conn.cursor() as cur:
        cur.execute("SELECT market, strategy, max(run_id) FROM universe_history GROUP BY 1, 2")
        latest = cur.fetchall()
        for market, strategy, run_id in latest:
            cur.execute("SELECT run_id FROM watchlist WHERE source='screener' AND market=%s AND strategy=%s LIMIT 1", (market, strategy))
            have = cur.fetchone()
            if have and have[0] == run_id:
                continue  # already in sync with this run
            cur.execute("SELECT full_row FROM universe_history WHERE market=%s AND strategy=%s AND run_id=%s", (market, strategy, run_id))
            out[f"{market}/{strategy}"] = sync_records(market, strategy, run_id, [r[0] for r in cur.fetchall()])
    return out


def add(market: str, symbol: str, note: str | None = None) -> None:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("""
            INSERT INTO watchlist (market, symbol, source, strategy, note) VALUES (%s, %s, 'manual', '', %s)
            ON CONFLICT (market, symbol, source, strategy) DO UPDATE SET note=COALESCE(EXCLUDED.note, watchlist.note), updated_at=now()
        """, (market, symbol, note))


def remove(market: str, symbol: str) -> None:
    """Drop the manual entry and dismiss any screener entries for the symbol."""
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("DELETE FROM watchlist WHERE market=%s AND symbol=%s AND source='manual'", (market, symbol))
        cur.execute("UPDATE watchlist SET dismissed=true WHERE market=%s AND symbol=%s AND source='screener'", (market, symbol))


def set_note(market: str, symbol: str, note: str | None) -> None:
    """Notes live on the manual entry; noting a screener-only name pins it manually too."""
    add(market, symbol, None)
    with db.get_connection().cursor() as cur:
        cur.execute("UPDATE watchlist SET note=%s, updated_at=now() WHERE market=%s AND symbol=%s AND source='manual'",
                    (note or None, market, symbol))


def entries(market: str | None = None) -> list[dict]:
    """One dict per (market, symbol): sources merged, dismissed screener rows excluded."""
    init_schema()
    sql = "SELECT market, symbol, source, strategy, decision, reason, setup, entry, stop, target_r, run_id, note, added_at FROM watchlist WHERE NOT dismissed"
    args: tuple = ()
    if market:
        sql += " AND market=%s"
        args = (market,)
    with db.get_connection().cursor() as cur:
        cur.execute(sql + " ORDER BY added_at", args)
        rows = cur.fetchall()
    merged: dict[tuple, dict] = {}
    for m, sym, src, strat, dec, reason, setup, entry, stop, tr, run, note, added in rows:
        e = merged.setdefault((m, sym), {"market": m, "symbol": sym, "manual": False, "strategies": [], "note": None, "added_at": added})
        e["added_at"] = min(e["added_at"], added)
        if src == "manual":
            e["manual"] = True
            e["note"] = note
        else:
            e["strategies"].append({"strategy": strat, "decision": dec, "reason": reason, "setup": setup,
                                    "entry": entry, "stop": stop, "target_r": tr, "run_id": run})
    return list(merged.values())


def main() -> None:
    ap = argparse.ArgumentParser(description="Manage the watchlist")
    ap.add_argument("--market", default="us")
    ap.add_argument("--add")
    ap.add_argument("--remove")
    ap.add_argument("--note")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--sync-latest", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if a.sync_latest:
        print(sync_latest())
    if a.add:
        add(a.market, a.add.upper(), a.note)
    if a.remove:
        remove(a.market, a.remove.upper())
    if a.list or not (a.add or a.remove or a.sync_latest):
        for e in entries():
            src = (["manual"] if e["manual"] else []) + [s["strategy"] for s in e["strategies"]]
            print(f"{e['market']:6s} {e['symbol']:14s} {', '.join(src):40s} {e['note'] or ''}")


if __name__ == "__main__":
    main()
