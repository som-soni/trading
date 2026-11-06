"""A screen's members, recorded each session — the forward record a screen is judged on later.

A screen query is recomputed from the snapshot whenever it is asked, so today's code answers for every
past date. A screen being validated forward needs the opposite: what it said on the day, kept, so a later
change to a field or a threshold cannot rewrite its record. `record` stores the members of the screens in
FORWARD_SCREENS after each snapshot (the `breakout_watch` job); analytics/breakout_study.py `forward`
scores them with the study's own outcome rule.

Stored in `screen_alerts` (market, screen, date, symbol, close, pivot, high_252, group_rs, rs_rank).
"""

import pandas as pd
import psycopg2.extras

from ..marketdata import db
from . import definitions

# screen key -> the snapshot columns kept beside each member
FORWARD_SCREENS = {"breakout_watch": ("close", "pivot_55", "high_252", "group_rs", "rs_rank")}

SCHEMA = """
CREATE TABLE IF NOT EXISTS screen_alerts (
    market TEXT NOT NULL,
    screen TEXT NOT NULL,
    date DATE NOT NULL,
    symbol TEXT NOT NULL,
    close DOUBLE PRECISION,
    pivot DOUBLE PRECISION,
    high_252 DOUBLE PRECISION,
    group_rs DOUBLE PRECISION,
    rs_rank DOUBLE PRECISION,
    logged_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, screen, date, symbol)
);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def markets(screen: str) -> tuple:
    return tuple(definitions.presets()[screen].get("markets") or ())


def record(market: str, df: pd.DataFrame) -> dict:
    """Store today's members of every forward screen offered in this market; {screen: members}. Re-running
    a session replaces that session's rows, so a rebuilt snapshot cannot leave a stale member behind."""
    init_schema()
    d = df.attrs["date"]
    out = {}
    for key, cols in FORWARD_SCREENS.items():
        p = definitions.presets()[key]
        if market not in (p.get("markets") or [market]):
            continue
        hit = df[definitions.mask(df, p["conditions"])]
        num = lambda v: None if v is None or v != v else float(v)
        rows = [(market, key, d, r["symbol"], *(num(r[c]) for c in cols)) for _, r in hit.iterrows()]
        with db.get_connection().cursor() as cur:
            cur.execute("DELETE FROM screen_alerts WHERE market=%s AND screen=%s AND date=%s", (market, key, d))
            if rows:
                psycopg2.extras.execute_values(
                    cur, "INSERT INTO screen_alerts (market, screen, date, symbol, close, pivot, high_252, group_rs, rs_rank) VALUES %s", rows)
        out[key] = len(rows)
    return out


def load(market: str, screen: str) -> pd.DataFrame:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT date, symbol, close, pivot, high_252, group_rs, rs_rank FROM screen_alerts "
                    "WHERE market=%s AND screen=%s ORDER BY date, symbol", (market, screen))
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=["date", "symbol", "close", "pivot", "high_252", "group_rs", "rs_rank"])
    df["date"] = pd.to_datetime(df["date"])
    return df
