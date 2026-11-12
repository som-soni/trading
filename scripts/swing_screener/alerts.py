"""Price alerts, in the app only: "tell me when SYMBOL trades above (or below) PRICE", stored in Postgres
(`price_alerts`) and checked against the stored daily bars by the `alerts` job (jobs/registry.py, screening
layer, after `prices`). A triggered alert keeps the session and the close that reached it until you dismiss it;
the Today page and the chart's near-trigger list show it. Nothing is sent anywhere, and nothing is ordered.

An alert usually comes from a near-trigger plan (a strategy's buy-stop not yet reached): `strategy` names it,
so the alert reads "Darvas box: buy 466.50" rather than a bare price.
"""

from __future__ import annotations

from .marketdata import db

SCHEMA = """
CREATE TABLE IF NOT EXISTS price_alerts (
    id SERIAL PRIMARY KEY,
    market TEXT NOT NULL,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('above', 'below')),
    price DOUBLE PRECISION NOT NULL,
    strategy TEXT,                  -- the plan it came from, if any
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    triggered_on DATE,              -- the stored session whose high (or low) reached the price
    triggered_close DOUBLE PRECISION,
    dismissed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS price_alerts_open ON price_alerts (market, symbol) WHERE dismissed_at IS NULL;
"""
_COLS = "id, market, symbol, direction, price, strategy, note, created_at, triggered_on, triggered_close, dismissed_at"


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _row(r) -> dict:
    d = dict(zip(_COLS.split(", "), r))
    for k in ("created_at", "triggered_on", "dismissed_at"):
        if d[k] is not None:
            d[k] = d[k].isoformat()
    return d


def listing(market: str | None = None, symbol: str | None = None) -> list[dict]:
    """Alerts not dismissed, triggered ones first."""
    sql, args = f"SELECT {_COLS} FROM price_alerts WHERE dismissed_at IS NULL", []
    if market:
        sql += " AND market = %s"; args.append(market)
    if symbol:
        sql += " AND symbol = %s"; args.append(symbol)
    sql += " ORDER BY triggered_on DESC NULLS LAST, created_at DESC"
    with db.get_connection().cursor() as cur:
        cur.execute(sql, tuple(args))
        return [_row(r) for r in cur.fetchall()]


def create(market: str, symbol: str, direction: str, price: float, strategy: str | None = None, note: str | None = None) -> dict:
    if direction not in ("above", "below"):
        raise ValueError("direction is 'above' or 'below'")
    if not (price and float(price) > 0):
        raise ValueError("an alert needs a price above zero")
    with db.get_connection().cursor() as cur:
        cur.execute(f"""INSERT INTO price_alerts (market, symbol, direction, price, strategy, note)
                        VALUES (%s, %s, %s, %s, %s, %s) RETURNING {_COLS}""",
                    (market, symbol, direction, float(price), strategy or None, (note or "").strip()[:200] or None))
        return _row(cur.fetchone())


def dismiss(aid: int) -> bool:
    with db.get_connection().cursor() as cur:
        cur.execute("UPDATE price_alerts SET dismissed_at = now() WHERE id = %s AND dismissed_at IS NULL", (aid,))
        return cur.rowcount > 0


def check(market: str) -> dict:
    """Mark the market's waiting alerts whose price a stored session has reached since the alert was set: the
    first such session after the day it was set (a high already printed that day is not news), by its high
    (above) or its low (below). Stored bars only."""
    init_schema()
    hit = 0
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT id, symbol, direction, price, created_at FROM price_alerts "
                    "WHERE market = %s AND dismissed_at IS NULL AND triggered_on IS NULL", (market,))
        waiting = cur.fetchall()
        for aid, sym, direction, price, created in waiting:
            cond = "high >= %s" if direction == "above" else "low <= %s"
            cur.execute(f"""SELECT date, close FROM prices WHERE market = %s AND symbol = %s AND date > %s::date
                            AND {cond} ORDER BY date LIMIT 1""", (market, sym, created.date(), price))
            r = cur.fetchone()
            if r:
                cur.execute("UPDATE price_alerts SET triggered_on = %s, triggered_close = %s WHERE id = %s", (r[0], r[1], aid))
                hit += 1
    return {"waiting": len(waiting) - hit, "triggered": hit}
