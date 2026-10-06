"""How current the stored prices are — one definition shared by the jobs, the web app and analytics.

  expected_session(market)  the latest trading day whose bars should exist by now: a weekday's
                            session counts once its close plus a data delay has passed
                            (US 17:30 New York, India 17:00 Kolkata).
  sessions(market)          trading days in the database (from a few always-traded anchor symbols),
                            dropping recent days that hold fewer than COMPLETE_SHARE of a typical
                            day's rows — a load still running, or a holiday with a few stray rows.
  price_status(market)      latest complete session, how many trading days it lags the expected
                            one, and any newer, partly loaded day.

Exchange holidays are not modelled, so a lag of one trading day may just be a
holiday; two or more means the prices job has not run.
"""

import datetime as dt
import time
from zoneinfo import ZoneInfo

import numpy as np

from . import db

MARKET_CLOSE = {"us": ("America/New_York", dt.time(17, 30)), "india": ("Asia/Kolkata", dt.time(17, 0))}
ANCHORS = {"us": ("SPY", "AAPL", "MSFT", "JPM", "XOM"),
           "india": ("RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "INFY.NS", "ICICIBANK.NS")}
COMPLETE_SHARE = 0.8      # a recent day needs this share of a typical day's rows to count as a session
_counts_cache: dict[str, tuple[float, dict]] = {}


def _q(sql: str, params: tuple) -> list:
    with db.get_connection().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def expected_session(market: str, now: dt.datetime | None = None) -> dt.date:
    tz, cutoff = MARKET_CLOSE[market]
    local = (now or dt.datetime.now(dt.timezone.utc)).astimezone(ZoneInfo(tz))
    d = local.date()
    if d.weekday() < 5 and local.time() >= cutoff:
        return d
    d -= dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def lag(d: dt.date | None, expected: dt.date) -> int | None:
    """Trading days (weekdays) `d` is behind `expected`."""
    if d is None:
        return None
    return int(np.busday_count(d, expected)) if d < expected else 0


def recent_counts(market: str, max_age_s: float = 60) -> dict:
    """date -> rows stored, for the last ~6 weeks (one fast query, cached briefly)."""
    hit = _counts_cache.get(market)
    if not hit or time.time() - hit[0] > max_age_s:
        hit = (time.time(), dict(_q("SELECT date, count(*) FROM prices WHERE market=%s AND date >= current_date - 45 GROUP BY date",
                                    (market,))))
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
    return {"market": market, "latest": last, "expected": exp, "lag": lag(last, exp),
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
