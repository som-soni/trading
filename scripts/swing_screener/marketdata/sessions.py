"""Drop the bars the price source dates on a day the market did not trade for most of its symbols.

Now and then the source serves a bar, for a handful of symbols, on a date the rest of the market has none: a
holiday (US 2026-05-25, Memorial Day, one symbol; 2026-09-07, Labor Day, one symbol), an exchange closure
(India 2004-04-26 and 2004-10-13, election days, about 200 of 520), or a Saturday special session the source
priced for almost nobody (India 2010-02-06, 39 of 930; 2012-01-07, 2012-03-03 and 2012-09-08, 3 of 1,050;
2015-02-28, 1 of 1,110). Each bar may be a real print, but the date is not a session for the market as a whole.

Left in, it costs far more than one bar. Anything that lines the whole market up on one calendar — a frame of
closes with a column per symbol — gains a row on that date with no price for every other symbol, and a rolling
statistic that needs a full window (the momentum strategies' 200-day average) is then missing for every one of
them for the next 200 sessions. India's momentum runs sat in cash from February to October 2010 and from
January 2012 to June 2013 for exactly this reason.

So a date is a STRAY SESSION when fewer than STRAY_MAX_SHARE of the symbols the market usually prices around it
(the median count over the USUAL_WINDOW sessions centred on it) have a bar on it. A real special session —
Diwali's Muhurat hour, a Saturday budget day — is priced for most of the market and is kept. Only dates followed
by SETTLE_SESSIONS sessions are judged, so the newest day, part-way through a refresh, is never mistaken for one.

`repair` finds them, records each in `prices_stray_sessions` and re-saves every symbol with a bar on one;
`cache.save_cached` drops a recorded date from every write (all writers pass a symbol's full history) and deletes
it from storage, so a later re-fetch cannot bring it back. Removed rows are kept in `prices_stray_backup`.
The `sessions` job (jobs/registry.py) runs `repair` after each price load.

    PYTHONPATH=. python3 -m swing_screener.marketdata.sessions --market india            # report
    PYTHONPATH=. python3 -m swing_screener.marketdata.sessions --market india --repair   # and remove
"""

import argparse
import logging

import pandas as pd

from . import db

logger = logging.getLogger(__name__)

STRAY_MAX_SHARE = 0.5   # a date priced for fewer than this share of the usual symbol count is not a market session
USUAL_WINDOW = 21       # sessions, centred on the date, whose median count is "usual"
SETTLE_SESSIONS = 5     # a date is judged only once this many sessions follow it

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices_stray_sessions (
    market VARCHAR(16) NOT NULL,
    date DATE NOT NULL,
    priced INTEGER NOT NULL,
    usual INTEGER NOT NULL,
    found_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, date)
);
CREATE TABLE IF NOT EXISTS prices_stray_backup (LIKE prices INCLUDING DEFAULTS);
ALTER TABLE prices_stray_backup ADD COLUMN IF NOT EXISTS removed_at TIMESTAMPTZ NOT NULL DEFAULT now();
"""
_schema_ready = False


def _ensure_schema(cur) -> None:
    global _schema_ready
    if not _schema_ready:
        cur.execute(SCHEMA)
        _schema_ready = True


def find_stray(counts: pd.Series) -> pd.DataFrame:
    """The stray sessions in `counts` (symbols priced per date): columns date, priced, usual."""
    counts = counts.sort_index()
    usual = counts.rolling(USUAL_WINDOW, center=True, min_periods=1).median()
    judged = counts.index[:-SETTLE_SESSIONS] if SETTLE_SESSIONS else counts.index
    stray = counts.index.isin(judged) & (counts < STRAY_MAX_SHARE * usual)
    return pd.DataFrame({"date": counts.index[stray], "priced": counts[stray].astype(int).values,
                         "usual": usual[stray].round().astype(int).values})


def stored_counts(market: str) -> pd.Series:
    """Symbols with a stored bar, per date."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT date, count(*) FROM prices WHERE market=%s GROUP BY date", (market,))
        rows = cur.fetchall()
    return pd.Series({pd.Timestamp(d): n for d, n in rows}, dtype=float)


def recorded(market: str) -> set[pd.Timestamp]:
    """The dates recorded as stray sessions for `market`."""
    with db.get_connection().cursor() as cur:
        _ensure_schema(cur)
        cur.execute("SELECT date FROM prices_stray_sessions WHERE market=%s", (market,))
        return {pd.Timestamp(r[0]) for r in cur.fetchall()}


def drop_stray(market: str, symbol: str, df: pd.DataFrame) -> pd.DataFrame:
    """`df` without its bars on recorded stray sessions; those bars are backed up and deleted from storage."""
    stray = recorded(market)
    if not stray:
        return df
    gone = df.index[df.index.isin(list(stray))]
    if not len(gone):
        return df
    dates = [d.date() for d in gone]
    with db.get_connection().cursor() as cur:
        cur.execute("""INSERT INTO prices_stray_backup SELECT p.*, now() FROM prices p
                       WHERE market=%s AND symbol=%s AND date = ANY(%s)""", (market, symbol, dates))
        cur.execute("DELETE FROM prices WHERE market=%s AND symbol=%s AND date = ANY(%s)", (market, symbol, dates))
        if cur.rowcount:   # the strategies' cached signals were computed with the stray bar in the history
            cur.execute("DELETE FROM backtest_signals WHERE market=%s AND symbol=%s", (market, symbol))
    return df.drop(gone)


def repair(market: str, apply: bool = False) -> dict:
    """Find the stray sessions in what is stored for `market`; with `apply`, record them and re-save every symbol
    with a bar on one through `save_cached`, which drops those bars, deletes them and recomputes the indicators."""
    from . import cache
    found = find_stray(stored_counts(market))
    for r in found.itertuples():
        logger.info("%s %s (%s): %d symbols priced, %d usual", market, r.date.date(), r.date.day_name(), r.priced, r.usual)
    out = {"market": market, "stray_sessions": [str(d.date()) for d in found["date"]], "symbols": 0,
           "bars_removed": int(found["priced"].sum()), "applied": apply}
    if not apply or found.empty:
        return out
    dates = [d.date() for d in found["date"]]
    with db.get_connection().cursor() as cur:
        _ensure_schema(cur)
        db_rows = [(market, r.date.date(), int(r.priced), int(r.usual)) for r in found.itertuples()]
        cur.executemany("""INSERT INTO prices_stray_sessions (market, date, priced, usual) VALUES (%s, %s, %s, %s)
                           ON CONFLICT (market, date) DO NOTHING""", db_rows)
        cur.execute("SELECT DISTINCT symbol FROM prices WHERE market=%s AND date = ANY(%s) ORDER BY symbol",
                    (market, dates))
        symbols = [r[0] for r in cur.fetchall()]
    for sym in symbols:
        df = cache.load_cached(market, sym)
        if df is not None and not df.empty:
            cache.save_cached(market, sym, df)
    out["symbols"] = len(symbols)
    return out


def main() -> None:
    from ..config import MARKETS
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=list(MARKETS))
    ap.add_argument("--repair", action="store_true",
                    help="remove the stray sessions' bars (backed up in prices_stray_backup)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(repair(args.market, apply=args.repair))


if __name__ == "__main__":
    main()
