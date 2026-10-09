"""Chart drawings: the lines, text and callout annotations drawn on the web chart,
stored per (market, symbol) in Postgres (`chart_drawings`) so they survive browsers
and machines.

The web app is the only writer (GET/PUT /api/drawings/{market}/{symbol}). Items are
an opaque JSON list owned by web/static/drawings.js ({id, type, pts: [{t, p}], ...});
the server stores and returns them without interpreting them. A row persists even
when its list is emptied, so "cleared drawings" is itself durable: the client only
migrates a browser's old localStorage drawings when no row exists yet, and an
existing empty row blocks that.
"""

import json

from .marketdata import db

SCHEMA = """
CREATE TABLE IF NOT EXISTS chart_drawings (
    market VARCHAR(16) NOT NULL,
    symbol VARCHAR(64) NOT NULL,
    items JSONB NOT NULL DEFAULT '[]',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, symbol)
);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def get(market: str, symbol: str) -> dict:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT items FROM chart_drawings WHERE market=%s AND symbol=%s", (market, symbol))
        r = cur.fetchone()
    return {"exists": r is not None, "items": r[0] if r else []}


def put(market: str, symbol: str, items: list) -> dict:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute(
            """INSERT INTO chart_drawings (market, symbol, items, updated_at) VALUES (%s, %s, %s, now())
               ON CONFLICT (market, symbol) DO UPDATE SET items = EXCLUDED.items, updated_at = now()""",
            (market, symbol, json.dumps(items)),
        )
    return {"exists": True, "items": items}
