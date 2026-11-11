"""How current the stored prices are — one definition shared by the jobs, the web app and analytics.

  expected_session(market)  the latest trading day whose bars should exist by now: a weekday's
                            session counts once its close plus a data delay has passed
                            (US 17:30 New York, India 17:00 Kolkata).
  sessions(market)          trading days in the database (from a few always-traded anchor symbols),
                            dropping recent days that hold fewer than COMPLETE_SHARE of a typical
                            day's rows — a load still running, or a holiday with a few stray rows.
  price_status(market)      latest complete session, how many trading days it lags the expected
                            one, and any newer, partly loaded day.

Exchange holidays come from the market's `holiday_calendar` (python-holidays' financial calendars,
NYSE and NSE) plus its `extra_closures`, so a holiday is neither expected nor counted as a lag. A
one-off closure announced late and not yet in either still reads as one day behind.

Rows per day come from `price_day_counts`, which triggers on `prices` keep exact for every
writer; counting them from `prices` itself takes 15-20 s, because recently rewritten rows
cost a heap fetch each. The prices job installs it (ensure_day_counts); until then the
count falls back to `prices`.
"""

import datetime as dt
import functools
import threading
import time
from zoneinfo import ZoneInfo

import numpy as np

from . import db

MARKET_CLOSE = {"us": ("America/New_York", dt.time(17, 30)), "india": ("Asia/Kolkata", dt.time(17, 0))}
ANCHORS = {"us": ("SPY", "AAPL", "MSFT", "JPM", "XOM"),
           "india": ("RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "INFY.NS", "ICICIBANK.NS")}
COMPLETE_SHARE = 0.8      # a recent day needs this share of a typical day's rows to count as a session
_counts_cache: dict[str, tuple[float, dict]] = {}
_counts_locks: dict[str, threading.Lock] = {}

# Counted on INSERT (an upsert's NEW TABLE holds only the rows it inserted) and DELETE, once per
# statement. Nothing updates a row's market or date, so UPDATE needs no trigger.
DAY_COUNTS_SCHEMA = """
CREATE TABLE price_day_counts (
    market VARCHAR(16) NOT NULL,
    date DATE NOT NULL,
    n_rows INTEGER NOT NULL,
    PRIMARY KEY (market, date)
);
CREATE OR REPLACE FUNCTION price_day_counts_add() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO price_day_counts (market, date, n_rows)
        SELECT market, date, count(*) FROM new_rows GROUP BY market, date ORDER BY market, date
    ON CONFLICT (market, date) DO UPDATE SET n_rows = price_day_counts.n_rows + EXCLUDED.n_rows;
    RETURN NULL;
END $$;
CREATE OR REPLACE FUNCTION price_day_counts_sub() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    UPDATE price_day_counts c SET n_rows = c.n_rows - g.n
        FROM (SELECT market, date, count(*) AS n FROM old_rows GROUP BY market, date) g
        WHERE c.market = g.market AND c.date = g.date;
    DELETE FROM price_day_counts c USING (SELECT DISTINCT market, date FROM old_rows) g
        WHERE c.market = g.market AND c.date = g.date AND c.n_rows <= 0;
    RETURN NULL;
END $$;
CREATE OR REPLACE FUNCTION price_day_counts_clear() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM price_day_counts;
    RETURN NULL;
END $$;
CREATE OR REPLACE TRIGGER price_day_counts_ins AFTER INSERT ON prices
    REFERENCING NEW TABLE AS new_rows FOR EACH STATEMENT EXECUTE FUNCTION price_day_counts_add();
CREATE OR REPLACE TRIGGER price_day_counts_del AFTER DELETE ON prices
    REFERENCING OLD TABLE AS old_rows FOR EACH STATEMENT EXECUTE FUNCTION price_day_counts_sub();
CREATE OR REPLACE TRIGGER price_day_counts_trunc AFTER TRUNCATE ON prices
    FOR EACH STATEMENT EXECUTE FUNCTION price_day_counts_clear();
"""


def _q(sql: str, params: tuple) -> list:
    with db.get_connection().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


@functools.lru_cache(maxsize=None)
def _closures(market: str, year: int) -> frozenset:
    from ..config import MARKETS
    cfg = MARKETS.get(market)
    if cfg is None:
        return frozenset()
    out = {dt.date.fromisoformat(x) for x in cfg.extra_closures if x.startswith(str(year))}
    if cfg.holiday_calendar:
        import holidays
        out |= set(holidays.financial_holidays(cfg.holiday_calendar, years=year))
    return frozenset(out)


def holidays_between(market: str, start: dt.date, end: dt.date) -> list:
    """Weekday exchange closures from `start` to `end` inclusive."""
    return sorted(d for y in range(start.year, end.year + 1) for d in _closures(market, y)
                  if start <= d <= end and d.weekday() < 5)


def is_trading_day(market: str, d: dt.date) -> bool:
    return d.weekday() < 5 and d not in _closures(market, d.year)


def expected_session(market: str, now: dt.datetime | None = None) -> dt.date:
    tz, cutoff = MARKET_CLOSE[market]
    local = (now or dt.datetime.now(dt.timezone.utc)).astimezone(ZoneInfo(tz))
    d = local.date()
    if is_trading_day(market, d) and local.time() >= cutoff:
        return d
    d -= dt.timedelta(days=1)
    while not is_trading_day(market, d):
        d -= dt.timedelta(days=1)
    return d


def lag(d: dt.date | None, expected: dt.date, market: str | None = None) -> int | None:
    """Trading days `d` is behind `expected`: weekdays, less the market's exchange holidays when named."""
    if d is None:
        return None
    if d >= expected:
        return 0
    # trading days after `d` up to and including `expected` -- so a date that is itself a holiday (a NAV
    # published on an exchange holiday) still counts the sessions after it
    start, end = d + dt.timedelta(days=1), expected + dt.timedelta(days=1)
    hol = holidays_between(market, start, expected) if market else []
    return int(np.busday_count(start, end, holidays=hol))


def ensure_day_counts() -> bool:
    """Create and fill `price_day_counts` with its triggers, once. Returns True if it did so now.

    The fill counts every stored row (a few minutes) while holding a lock that pauses writes to `prices`
    (reads go on), so the triggers count exactly the rows the fill did not see."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT to_regclass('price_day_counts') IS NOT NULL")
        if cur.fetchone()[0]:
            return False
        cur.execute("BEGIN")
        try:
            cur.execute("LOCK TABLE prices IN SHARE ROW EXCLUSIVE MODE")
            cur.execute("SELECT to_regclass('price_day_counts') IS NOT NULL")   # another process got here first
            if cur.fetchone()[0]:
                cur.execute("ROLLBACK")
                return False
            cur.execute(DAY_COUNTS_SCHEMA)
            cur.execute("INSERT INTO price_day_counts SELECT market, date, count(*) FROM prices GROUP BY market, date")
            cur.execute("COMMIT")
        except Exception:
            cur.execute("ROLLBACK")
            raise
    return True


def _has_day_counts() -> bool:
    return _q("SELECT to_regclass('price_day_counts') IS NOT NULL", ())[0][0]


def recent_counts(market: str, max_age_s: float = 60) -> dict:
    """date -> rows stored, for the last ~6 weeks (one fast query, cached briefly; concurrent misses query once)."""
    hit = _counts_cache.get(market)
    if hit and time.time() - hit[0] <= max_age_s:
        return hit[1]
    with _counts_locks.setdefault(market, threading.Lock()):
        hit = _counts_cache.get(market)
        if not hit or time.time() - hit[0] > max_age_s:
            sql = ("SELECT date, n_rows FROM price_day_counts WHERE market=%s AND date >= current_date - 45 AND n_rows > 0"
                   if _has_day_counts() else
                   "SELECT date, count(*) FROM prices WHERE market=%s AND date >= current_date - 45 GROUP BY date")
            hit = (time.time(), dict(_q(sql, (market,))))
            _counts_cache[market] = hit
    return hit[1]


def sessions(market: str, complete: bool = True, since_days: int = 800) -> list:
    rows = _q("""SELECT date FROM prices WHERE market=%s AND symbol = ANY(%s) AND date > current_date - %s
                 GROUP BY date HAVING count(*) >= 3 ORDER BY date""", (market, list(ANCHORS[market]), since_days))
    days = [r[0] for r in rows]
    if complete:
        counts = recent_counts(market)
        if counts:
            typical = float(np.median(list(counts.values())))
            days = [d for d in days if d not in counts or counts[d] >= COMPLETE_SHARE * typical]
    return days


def price_status(market: str) -> dict:
    days = sessions(market, since_days=30)
    exp = expected_session(market)
    last = days[-1] if days else None
    counts = recent_counts(market)
    newer = sorted(d for d in counts if last is None or d > last)
    return {"market": market, "latest": last, "expected": exp, "lag": lag(last, exp, market),
            "rows": counts.get(last, 0) if last else 0,
            "partial": (newer[-1], counts[newer[-1]]) if newer else None}


def describe(st: dict) -> str:
    """One line for logs and errors: "prices end 1 Oct 2026, expected 6 Oct 2026 (3 trading days behind)"."""
    if st["latest"] is None:
        return "no prices stored"
    s = f"prices end {st['latest']:%-d %b %Y}"
    if st["lag"]:
        s += f", expected {st['expected']:%-d %b %Y} ({st['lag']} trading day{'s' if st['lag'] > 1 else ''} behind)"
    if st["partial"]:
        s += f"; {st['partial'][0]:%-d %b} partly loaded ({st['partial'][1]:,} symbols)"
    return s
