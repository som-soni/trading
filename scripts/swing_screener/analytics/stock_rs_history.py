"""Each stock's RS rating (1–99) as it stood on past Fridays — the history behind the chart's RS strip.

The rating is `backtesting/spec.rs_ratings`: the weighted RS score (core/indicators.rs_score) ranked across
the market's tradable universe on that date, from stored prices up to that date — the same number the
daily screen's C8 and the backtest's `filter_min_rs` apply. Ranking a whole market takes tens of seconds
for a few years of dates, too slow for a chart request, so it is kept here weekly:

  * one row per (market, Friday, rated stock); a Friday that was a holiday is rated on the session before
    it, and stored under the Friday (so a reader forward-filling from that date never looks ahead);
  * a stock outside the rated universe that week (too cheap, too thin, too new) has no row;
  * `ensure(market)` rates the Fridays from START not stored yet, a year at a time, up to the last stored
    session — the weekly job (`stock_rs_history` in jobs/registry.py) adds each new week.

    PYTHONPATH=. python3 -m swing_screener.analytics.stock_rs_history --market india
    PYTHONPATH=. python3 -m swing_screener.analytics.stock_rs_history --market us --rebuild   # after a rule change
"""

import argparse
import logging
import time

import pandas as pd

from ..marketdata import asof, db

logger = logging.getLogger(__name__)

START = "2010-01-01"     # first Friday rated (the rating needs 252 sessions before it, so data from 2009 on)

SCHEMA = """
CREATE TABLE IF NOT EXISTS stock_rs_history (
    market VARCHAR(16) NOT NULL, symbol TEXT NOT NULL, date DATE NOT NULL, rs SMALLINT NOT NULL,
    PRIMARY KEY (market, symbol, date)
);
CREATE INDEX IF NOT EXISTS stock_rs_history_date ON stock_rs_history (market, date);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def stored_dates(market: str) -> set:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT DISTINCT date FROM stock_rs_history WHERE market=%s", (market,))
        return {d for (d,) in cur.fetchall()}


def _last_session(market: str):
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT max(date) FROM prices WHERE market=%s AND symbol NOT LIKE '^%%'", (market,))
        return cur.fetchone()[0]


def ensure(market: str, rebuild: bool = False) -> dict:
    """Rate every Friday from START to the last stored session that is not stored yet. Returns
    {"dates": n added, "rows": n, "latest": date}."""
    from ..backtesting.spec import rs_ratings
    init_schema()
    if rebuild:
        with db.get_connection().cursor() as cur:
            cur.execute("DELETE FROM stock_rs_history WHERE market=%s", (market,))
    last = _last_session(market)
    fridays = [d.date() for d in pd.date_range(START, last, freq="W-FRI")]
    have = stored_dates(market)
    todo = [d for d in fridays if d not in have]
    added = rows = 0
    for year in sorted({d.year for d in todo}):         # a year per call keeps the price frame small
        chunk = [d for d in todo if d.year == year]
        t0 = time.time()
        rated = rs_ratings(market, chunk)
        out = [(market, sym, pd.Timestamp(d).date(), int(v)) for d, ser in rated.items()
               for sym, v in ser.dropna().items()]
        db.execute_values("""INSERT INTO stock_rs_history (market, symbol, date, rs) VALUES %s
                             ON CONFLICT (market, symbol, date) DO UPDATE SET rs=EXCLUDED.rs""", out)
        added += len(rated); rows += len(out)
        logger.info("stock RS %s %d: %d Fridays, %d ratings (%.0fs)", market, year, len(rated), len(out), time.time() - t0)
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT max(date) FROM stock_rs_history WHERE market=%s", (market,))
        latest = cur.fetchone()[0]
    return {"dates": added, "rows": rows, "latest": latest}


def load(market: str, symbol: str, since=None) -> tuple[list, dict]:
    """(every stored Friday of the market, {Friday: rating} for the symbol) — a Friday on which the stock
    went unrated is in the first and not the second, so a reader can tell "unrated that week" from "not
    stored". Honours a backtest stage's boundary (marketdata/asof)."""
    init_schema()
    end = asof.end_date()
    q, args = "WHERE market=%s", [market]
    if since is not None:
        q += " AND date >= %s"; args.append(since)
    if end is not None:
        q += " AND date <= %s"; args.append(end)
    with db.get_connection().cursor() as cur:
        cur.execute(f"SELECT DISTINCT date FROM stock_rs_history {q} ORDER BY date", args)
        dates = [d for (d,) in cur.fetchall()]
        cur.execute(f"SELECT date, rs FROM stock_rs_history {q} AND symbol=%s", args + [symbol])
        mine = dict(cur.fetchall())
    return dates, mine


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True)
    ap.add_argument("--rebuild", action="store_true", help="drop the market's stored ratings and rate again")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(ensure(a.market, rebuild=a.rebuild))


if __name__ == "__main__":
    main()
