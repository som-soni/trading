"""Delivery: how much of each Indian stock's traded volume was taken into delivery, per session.

NSE publishes a security-wise delivery position file every session (`MTO_DDMMYYYY.DAT` on its public
archive, back to before 2013): for every security, the quantity traded, the quantity marked for delivery
(gross across client level) and the delivery percentage. Intraday trades square off and never deliver, so
a high delivery % on heavy volume means shares changed hands to be held -- the signal the delivery-%
breakout strategy reads.

Stored in `delivery_daily` (market, date, symbol, traded_qty, deliv_qty, deliv_pct); the symbol is the
stored price symbol (`RELIANCE.NS`). Only ordinary equity series are kept (NSE_SERIES: EQ, BE, BZ, SM, ST).
`load` honours a backtest stage's boundary (marketdata/asof.py), like every loader a backtest reads.

    PYTHONPATH=. python3 -m swing_screener.marketdata.delivery --market india --start 2012-12-01   # backfill
    PYTHONPATH=. python3 -m swing_screener.marketdata.delivery --market india                     # catch up
"""

import argparse
import datetime as dt
import logging

import pandas as pd

from ..config import MARKETS
from . import asof, db

logger = logging.getLogger(__name__)

FIRST_DAY = dt.date(2012, 12, 1)     # a month of history before the 2013 optimise window opens
NSE_SERIES = ("EQ", "BE", "BZ", "SM", "ST")

SCHEMA = """
CREATE TABLE IF NOT EXISTS delivery_daily (
    market VARCHAR(16) NOT NULL,
    date DATE NOT NULL,
    symbol TEXT NOT NULL,
    traded_qty BIGINT,
    deliv_qty BIGINT,
    deliv_pct DOUBLE PRECISION,
    PRIMARY KEY (market, date, symbol)
);
CREATE INDEX IF NOT EXISTS delivery_daily_symbol ON delivery_daily (market, symbol, date);
CREATE TABLE IF NOT EXISTS delivery_days (
    market VARCHAR(16) NOT NULL,
    date DATE NOT NULL,
    status TEXT NOT NULL,                 -- ok | none (no file: holiday or weekend)
    rows INT,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, date)
);
"""


def covers(cfg) -> bool:
    """Whether a market publishes delivery data: NSE's cash market (its end-of-day file is `nse_cm`)."""
    return cfg.eod_file == "nse_cm"


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def url(d: dt.date) -> str:
    from .derivatives import ARCHIVE
    return f"{ARCHIVE}/archives/equities/mto/MTO_{d:%d%m%Y}.DAT"


def parse(text: str, suffix: str = ".NS") -> pd.DataFrame:
    """The file's security rows (record type 20) as symbol -> traded, delivered, %. Header lines are skipped."""
    rows = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 7 or parts[0] != "20" or parts[3] not in NSE_SERIES:
            continue
        try:
            rows.append((parts[2] + suffix, parts[3], int(float(parts[4])), int(float(parts[5])), float(parts[6])))
        except ValueError:
            continue
    df = pd.DataFrame(rows, columns=["symbol", "series", "traded_qty", "deliv_qty", "deliv_pct"])
    # one row per symbol: EQ first when a symbol trades in two series that day
    return (df.assign(_eq=df["series"] != "EQ").sort_values("_eq").drop_duplicates("symbol")
              .drop(columns=["series", "_eq"]).set_index("symbol"))


def fetch_day(d: dt.date, suffix: str = ".NS") -> pd.DataFrame | None:
    """One session's delivery rows; None when NSE has no file for the day (holiday, weekend, not yet out)."""
    import time
    from .derivatives import NSE_PAUSE, _sess
    time.sleep(NSE_PAUSE)
    try:
        r = _sess().get(url(d), timeout=60)
    except Exception as exc:  # noqa: BLE001 - a network blip is retried on the next run
        logger.warning("delivery %s: %s", d, exc)
        raise
    if r.status_code == 404 or (r.ok and "Security Wise Delivery Position" not in r.text[:200]):
        return None
    r.raise_for_status()
    return parse(r.text, suffix)


def _done(market: str) -> set:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT date FROM delivery_days WHERE market=%s", (market,))
        return {row[0] for row in cur.fetchall()}


def ingest(market: str, start: dt.date | None = None, end: dt.date | None = None, progress=None) -> dict:
    """Store every weekday from `start` (default: the day after the last stored, else FIRST_DAY) to `end`
    (default today) not stored yet. Recent days with no file are not marked done, so a late upload is
    picked up next time; days older than a week with no file are marked `none` (holidays)."""
    cfg = MARKETS[market]
    init_schema()
    done = _done(market)
    end = end or dt.date.today()
    if start is None:
        start = (max(done) + dt.timedelta(days=1)) if done else FIRST_DAY
    days = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
    days = [d for d in days if d.weekday() < 5 and d not in done]
    got = none = rows = 0
    for i, d in enumerate(days, 1):
        df = fetch_day(d, cfg.symbol_suffix or "")
        if df is None:
            if (end - d).days > 7:
                with db.get_connection().cursor() as cur:
                    cur.execute("""INSERT INTO delivery_days (market, date, status, rows) VALUES (%s,%s,'none',0)
                                   ON CONFLICT (market, date) DO NOTHING""", (market, d))
            none += 1
            continue
        db.execute_values("""INSERT INTO delivery_daily (market, date, symbol, traded_qty, deliv_qty, deliv_pct) VALUES %s
                             ON CONFLICT (market, date, symbol) DO UPDATE SET traded_qty=EXCLUDED.traded_qty,
                             deliv_qty=EXCLUDED.deliv_qty, deliv_pct=EXCLUDED.deliv_pct""",
                          [(market, d, s, int(r.traded_qty), int(r.deliv_qty), float(r.deliv_pct)) for s, r in df.iterrows()])
        with db.get_connection().cursor() as cur:
            cur.execute("""INSERT INTO delivery_days (market, date, status, rows) VALUES (%s,%s,'ok',%s)
                           ON CONFLICT (market, date) DO UPDATE SET status='ok', rows=EXCLUDED.rows, fetched_at=now()""",
                        (market, d, len(df)))
        got += 1
        rows += len(df)
        if progress:
            progress(f"{d}: {i} of {len(days)} days", done=i, total=len(days))
    return {"days": got, "no_file": none, "rows": rows, "from": str(start), "to": str(end)}


def load(market: str, symbols: list[str] | None = None, since=None) -> pd.DataFrame:
    """Stored delivery rows (date, symbol, traded_qty, deliv_qty, deliv_pct), never past a backtest stage's
    boundary (asof.end)."""
    init_schema()
    sql = "SELECT date, symbol, traded_qty, deliv_qty, deliv_pct FROM delivery_daily WHERE market=%s"
    params: list = [market]
    if symbols is not None:
        sql += " AND symbol = ANY(%s)"
        params.append(list(symbols))
    if since is not None:
        sql += " AND date >= %s"
        params.append(pd.Timestamp(since).date())
    end = asof.end_date()
    if end is not None:
        sql += " AND date <= %s"
        params.append(end)
    with db.get_connection().cursor() as cur:
        cur.execute(sql, params)
        df = pd.DataFrame(cur.fetchall(), columns=["date", "symbol", "traded_qty", "deliv_qty", "deliv_pct"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", default="india")
    ap.add_argument("--start", default=None, help="YYYY-MM-DD (default: after the last stored day)")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(ingest(a.market, start=pd.Timestamp(a.start).date() if a.start else None))


if __name__ == "__main__":
    main()
