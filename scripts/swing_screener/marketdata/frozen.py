"""Drop the placeholder quotes the price source fills a non-trading stretch with.

When a stock is not trading — suspended, delisted and relisted, or simply missing from the source's history —
the source often fills the gap with a *frozen* bar: no volume, and open, high, low and close all at one price,
repeated day after day. GVT&D (then Areva T&D) shows ₹4.97 for 1,456 sessions from Oct 2002 to Jun 2008, and its
first real bar after that is ₹250.20; Nestlé India sits at ₹527.05 from 2003 to 2010 and reappears at ₹124.73.
Those bars are not trades. Left in, the first real bar reads as a 50x gain (or a 76% crash), and every look-back
across the stretch — 52-week highs, relative strength, moving averages — is computed on numbers that never
traded. A re-download does not help: the source serves the same placeholder.

So `drop_frozen` removes, from a symbol's history:
  1. every run of at least FROZEN_MIN_BARS frozen bars at one price (a few flat zero-volume days are normal in
     a thin stock; a month of them is a placeholder), and
  2. when such a run lasts FROZEN_RESET_BARS or more and real trading follows it, everything before the run as
     well: after a year or more with no trades the earlier history is often on another scale (GVT&D's 2002 bars
     sit at ₹6), and no indicator usefully spans the gap. The history restarts where trading resumes.
A run that reaches the latest bar (a stock suspended now) loses only its frozen bars.

`cache.save_cached` applies it on every write — all writers pass a symbol's full history — and deletes the
dropped dates from storage, so a later re-fetch cannot bring them back. `repair` applies it to what is already
stored, keeping every removed row in `prices_frozen_backup`.

    PYTHONPATH=. python3 -m swing_screener.marketdata.frozen --market india            # report
    PYTHONPATH=. python3 -m swing_screener.marketdata.frozen --market india --repair   # and remove
"""

import argparse
import logging

import pandas as pd

from . import db

logger = logging.getLogger(__name__)

FROZEN_MIN_BARS = 20       # this many consecutive frozen bars at one price is a placeholder, not a quiet stock
FROZEN_RESET_BARS = 250    # a run this long (about a year) followed by trading restarts the history after it

BACKUP_SCHEMA = """
CREATE TABLE IF NOT EXISTS prices_frozen_backup (LIKE prices INCLUDING DEFAULTS);
ALTER TABLE prices_frozen_backup ADD COLUMN IF NOT EXISTS removed_at TIMESTAMPTZ NOT NULL DEFAULT now();
"""


def frozen_runs(df: pd.DataFrame) -> list[tuple[pd.Timestamp, pd.Timestamp, int]]:
    """(first date, last date, bars) of each run of >= FROZEN_MIN_BARS frozen bars at one price, oldest first."""
    if df is None or df.empty:
        return []
    c = df["close"]
    flat = (df["volume"].fillna(0) == 0) & (df["open"] == c) & (df["high"] == c) & (df["low"] == c)
    run_id = (~flat | (c != c.shift())).cumsum()          # a new run at every traded bar or change of price
    out = []
    for _, g in df[flat].groupby(run_id[flat]):
        if len(g) >= FROZEN_MIN_BARS:
            out.append((g.index[0], g.index[-1], len(g)))
    return out


def drop_frozen(df: pd.DataFrame) -> pd.DataFrame:
    """`df` without its frozen runs, and without the history before the last long run that trading follows.
    Repeated until nothing more qualifies: removing one run can join frozen bars either side of it into another."""
    while True:
        out = _drop_once(df)
        if len(out) == len(df):
            return out
        df = out


def _drop_once(df: pd.DataFrame) -> pd.DataFrame:
    runs = frozen_runs(df)
    if not runs:
        return df
    keep = pd.Series(True, index=df.index)
    for d0, d1, _ in runs:
        keep[(df.index >= d0) & (df.index <= d1)] = False
    resets = [d1 for _, d1, n in runs if n >= FROZEN_RESET_BARS and keep[df.index > d1].any()]
    if resets:
        keep[df.index <= max(resets)] = False
    return df[keep]


def repair(market: str, apply: bool = False) -> dict:
    """Every stored symbol with a frozen run: report it, and with `apply` re-save it through `save_cached`
    (which drops the runs, deletes them from storage and recomputes the indicators), backing up what goes."""
    from . import cache
    with db.get_connection().cursor() as cur:   # candidates: any symbol with FROZEN_MIN_BARS frozen bars at all
        cur.execute("""SELECT symbol FROM prices WHERE market=%s AND coalesce(volume, 0) = 0
                       AND open = close AND high = close AND low = close
                       GROUP BY symbol HAVING count(*) >= %s ORDER BY symbol""", (market, FROZEN_MIN_BARS))
        cands = [r[0] for r in cur.fetchall()]
    if apply:
        with db.get_connection().cursor() as cur:
            cur.execute(BACKUP_SCHEMA)
    symbols, bars = 0, 0
    for sym in cands:
        df = cache.load_cached(market, sym)
        clean = drop_frozen(df)
        gone = len(df) - len(clean)
        if not gone:
            continue
        symbols, bars = symbols + 1, bars + gone
        logger.info("%s %s: %d of %d bars frozen or before a long frozen run%s", market, sym, gone, len(df),
                    f"; history now starts {clean.index[0].date()}" if len(clean) and clean.index[0] > df.index[0] else "")
        if apply:
            cache.save_cached(market, sym, df)
    return {"market": market, "candidates": len(cands), "symbols": symbols, "bars_removed": bars, "applied": apply}


def backup_and_delete(market: str, symbol: str, dates: list) -> int:
    """Copy the given stored bars into prices_frozen_backup, then delete them. Returns the rows deleted."""
    if not dates:
        return 0
    with db.get_connection().cursor() as cur:
        cur.execute(BACKUP_SCHEMA)
        cur.execute("""INSERT INTO prices_frozen_backup SELECT p.*, now() FROM prices p
                       WHERE market=%s AND symbol=%s AND date = ANY(%s)""", (market, symbol, dates))
        cur.execute("DELETE FROM prices WHERE market=%s AND symbol=%s AND date = ANY(%s)", (market, symbol, dates))
        n = cur.rowcount
        if n:   # the strategies' cached signals were computed on the frozen bars
            cur.execute("DELETE FROM backtest_signals WHERE market=%s AND symbol=%s", (market, symbol))
    return n


def main() -> None:
    from ..config import MARKETS
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=list(MARKETS))
    ap.add_argument("--repair", action="store_true", help="remove the frozen bars (backed up in prices_frozen_backup)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(repair(args.market, apply=args.repair))


if __name__ == "__main__":
    main()
