"""Watchlists: TradingView-style named lists you manage, plus the screener's own list.

* **Your lists** (`watchlists` / `watchlist_items`) — as many named lists as you
  like ("My watchlist", "Breakouts to watch", ...), each mixing US and Indian
  symbols, managed from the web UI or this CLI. A screener run never touches them.
* **Screener picks** — the built-in list described below, kept up to date by
  every full pipeline run.

The screener list: names worth watching, from the screening runs.

* **screener** — refreshed by every full pipeline run (``history.record_run``
  calls :func:`sync_from_run`). A name is on it when the screener marks it
  ``tradeable`` or ``watchlist_candidate`` — the same rule ``daily.py`` uses
  for its "watchlist candidates" section. Entries are kept per
  (market, strategy): a re-run updates them, and names the strategy no longer
  flags drop off.
* **manual** — the original single hand-made list; it is migrated once into the
  named list "My watchlist" (see `init_schema`).

Removing a screener entry *dismisses* it rather than deleting it, so the next
run doesn't put it straight back; it returns only after it has dropped off the
screen and been flagged again.

    python3 -m swing_screener.screening.watchlist --show
    python3 -m swing_screener.screening.watchlist --add AAPL --market us --note "earnings 28th"
    python3 -m swing_screener.screening.watchlist --add RELIANCE.NS --market india --list "India longs"
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
CREATE TABLE IF NOT EXISTS watchlists (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS watchlist_items (
    list_id INT NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    market VARCHAR(16) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    note TEXT,
    added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (list_id, market, symbol)
);
"""
DEFAULT_LIST = "My watchlist"

_FIELDS = ("decision", "reason", "strategy_setup", "entry", "stop", "target_r")


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)
        # one-time migration: the old single manual list becomes the named list "My watchlist"
        cur.execute("SELECT count(*) FROM watchlists")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO watchlists (name) VALUES (%s) RETURNING id", (DEFAULT_LIST,))
            lid = cur.fetchone()[0]
            cur.execute("""INSERT INTO watchlist_items (list_id, market, symbol, note, added_at)
                           SELECT %s, market, symbol, note, added_at FROM watchlist WHERE source='manual'
                           ON CONFLICT DO NOTHING""", (lid,))
            cur.execute("DELETE FROM watchlist WHERE source='manual'")


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


# ---------------------------------------------------------------- named lists

def lists() -> list[dict]:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT w.id, w.name, count(i.symbol) FROM watchlists w LEFT JOIN watchlist_items i ON i.list_id=w.id
                       GROUP BY w.id ORDER BY w.created_at, w.id""")
        return [{"id": i, "name": n, "count": c} for i, n, c in cur.fetchall()]


def list_id(name: str, create: bool = False) -> int | None:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT id FROM watchlists WHERE name=%s", (name,))
        row = cur.fetchone()
        if row:
            return row[0]
        if not create:
            return None
        cur.execute("INSERT INTO watchlists (name) VALUES (%s) RETURNING id", (name,))
        return cur.fetchone()[0]


def create_list(name: str) -> int:
    name = name.strip()
    if not name:
        raise ValueError("a list needs a name")
    if list_id(name) is not None:
        raise ValueError(f"a list called “{name}” already exists")
    return list_id(name, create=True)


def rename_list(lid: int, name: str) -> None:
    name = name.strip()
    if not name:
        raise ValueError("a list needs a name")
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT id FROM watchlists WHERE name=%s AND id<>%s", (name, lid))
        if cur.fetchone():
            raise ValueError(f"a list called “{name}” already exists")
        cur.execute("UPDATE watchlists SET name=%s WHERE id=%s", (name, lid))


def delete_list(lid: int) -> None:
    with db.get_connection().cursor() as cur:
        cur.execute("DELETE FROM watchlists WHERE id=%s", (lid,))


def items(lid: int) -> list[dict]:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT market, symbol, note, added_at FROM watchlist_items WHERE list_id=%s ORDER BY added_at, symbol", (lid,))
        return [{"market": m, "symbol": s, "note": n, "added_at": a} for m, s, n, a in cur.fetchall()]


def add_item(lid: int, market: str, symbol: str, note: str | None = None) -> None:
    with db.get_connection().cursor() as cur:
        cur.execute("""INSERT INTO watchlist_items (list_id, market, symbol, note) VALUES (%s, %s, %s, %s)
                       ON CONFLICT (list_id, market, symbol) DO UPDATE SET note=COALESCE(EXCLUDED.note, watchlist_items.note)""",
                    (lid, market, symbol, note or None))


def remove_item(lid: int, market: str, symbol: str) -> None:
    with db.get_connection().cursor() as cur:
        cur.execute("DELETE FROM watchlist_items WHERE list_id=%s AND market=%s AND symbol=%s", (lid, market, symbol))


def set_item_note(lid: int, market: str, symbol: str, note: str | None) -> None:
    with db.get_connection().cursor() as cur:
        cur.execute("UPDATE watchlist_items SET note=%s WHERE list_id=%s AND market=%s AND symbol=%s", (note or None, lid, market, symbol))


def membership(market: str, symbol: str) -> list[int]:
    """The ids of your lists that contain this symbol."""
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT list_id FROM watchlist_items WHERE market=%s AND symbol=%s", (market, symbol))
        return [r[0] for r in cur.fetchall()]


def dismiss(market: str, symbol: str) -> None:
    """Hide a screener pick until it drops off the screen and is flagged again."""
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("UPDATE watchlist SET dismissed=true WHERE market=%s AND symbol=%s AND source='screener'", (market, symbol))


# the CLI's original verbs, now acting on a named list (default "My watchlist")
def add(market: str, symbol: str, note: str | None = None, list_name: str = DEFAULT_LIST) -> None:
    add_item(list_id(list_name, create=True), market, symbol, note)


def remove(market: str, symbol: str, list_name: str = DEFAULT_LIST) -> None:
    lid = list_id(list_name)
    if lid is not None:
        remove_item(lid, market, symbol)


def entries(market: str | None = None) -> list[dict]:
    """The Screener picks list: one dict per (market, symbol) with every strategy that flagged it,
    dismissed rows excluded."""
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
    ap.add_argument("--list", default=DEFAULT_LIST, help="which of your named lists --add / --remove act on")
    ap.add_argument("--show", action="store_true", help="print every list")
    ap.add_argument("--sync-latest", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if a.sync_latest:
        print(sync_latest())
    if a.add:
        add(a.market, a.add.upper(), a.note, a.list)
    if a.remove:
        remove(a.market, a.remove.upper(), a.list)
    if a.show or not (a.add or a.remove or a.sync_latest):
        for lst in lists():
            print(f"\n{lst['name']} ({lst['count']})")
            for e in items(lst["id"]):
                print(f"  {e['market']:6s} {e['symbol']:14s} {e['note'] or ''}")
        print("\nScreener picks")
        for e in entries():
            print(f"  {e['market']:6s} {e['symbol']:14s} {', '.join(s['strategy'] for s in e['strategies'])}")


if __name__ == "__main__":
    main()
