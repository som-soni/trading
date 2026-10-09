"""Market breadth: how the most-traded stocks are doing as a group.

Breadth answers "how risky is the market?", not "which way will it go?". It
is computed from the daily prices already in Postgres, for the BREADTH_N
most-traded stocks of each market on each day (ranked by 20-day average
turnover, so the set follows liquidity through time), and stored one row per
market per day in `breadth_daily`:

  advancers / decliners, big movers (±4% on the day), new 52-week highs and
  lows (today's high/low is the 252-bar extreme, with at least ~a year of
  history), % above the 5- and 50-day averages, and stocks up/down 25% / 50%
  over the last month (21 bars).

Only common stocks count. The US universe file already excludes ETFs; the
India one does not, so India symbols are classified once (yfinance quoteType,
cached in `symbol_kind`) and anything that is not an equity is left out.

Index levels and volatility indices (India VIX / VIX) are fetched into the
existing `index_series` table for the index cards and the options card.

    PYTHONPATH=. python3 -m jobs run breadth --market us                                # catch up on new days
    PYTHONPATH=. python3 -m swing_screener.analytics.breadth --market india --full    # all history since 2015
    PYTHONPATH=. python3 -m jobs run classify --market india                          # (re)classify stocks vs funds

The web app also tops up `breadth_daily` by itself whenever newer prices exist.
"""

import argparse
import logging
import time
import warnings

import pandas as pd

from ..marketdata import db, universe

logger = logging.getLogger(__name__)

BREADTH_N = 1000          # stocks per day: the most-traded by 20-day average turnover
HISTORY_START = "2015-01-01"
MIN_HISTORY_BARS = 200    # a 52-week high/low needs roughly a year of bars behind it
BIG_MOVE = 0.04           # "up/down 4%+" on the day
MONTH_BARS = 21

# index series this page needs, stored in index_series (key, yfinance ticker); price indices, not total return
INDEXES = {
    "india": [("NIFTY50", "^NSEI", "Nifty 50"), ("MIDCAP", "^NSEMDCP50", "Nifty Midcap 50"), ("NIFTY500", "^CRSLDX", "Nifty 500")],
    "us": [("SPX", "^GSPC", "S&P 500"), ("NDX", "^NDX", "Nasdaq 100"), ("RUT", "^RUT", "Russell 2000")],
}
VOL_INDEX = {"india": ("INDIAVIX", "^INDIAVIX", "India VIX"), "us": ("VIX", "^VIX", "VIX")}

SCHEMA = """
CREATE TABLE IF NOT EXISTS breadth_daily (
    market VARCHAR(16) NOT NULL, date DATE NOT NULL,
    n INT NOT NULL,                     -- stocks counted that day
    adv INT, dec INT, up4 INT, dn4 INT, -- rising / falling / up 4%+ / down 4%+
    highs INT, lows INT,                -- new 52-week highs / lows
    above5 INT, above50 INT,            -- closes above the 5- / 50-day average
    up25m INT, dn25m INT, up50m INT, dn50m INT,   -- up/down 25% and 50% over the last month
    PRIMARY KEY (market, date)
);
CREATE TABLE IF NOT EXISTS symbol_kind (
    market VARCHAR(16) NOT NULL, symbol VARCHAR(32) NOT NULL,
    kind VARCHAR(24) NOT NULL,          -- yfinance quoteType: EQUITY, ETF, MUTUALFUND, ...
    sector VARCHAR(64),                 -- yfinance sector, for the sector-leadership table
    checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, symbol)
);
ALTER TABLE symbol_kind ADD COLUMN IF NOT EXISTS sector VARCHAR(64);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


# ---------------------------------------------------------------- which symbols count

def _known_kinds(market: str) -> dict[str, str]:
    """Stock-vs-fund labels already known: symbol_kind, plus what the fundamentals fetch learnt."""
    kinds = {}
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol, kind FROM symbol_kind WHERE market=%s", (market,))
        kinds.update(dict(cur.fetchall()))
        cur.execute("SELECT to_regclass('fundamentals_raw') IS NOT NULL")
        if cur.fetchone()[0]:
            cur.execute("""SELECT symbol, COALESCE(raw->>'not_equity', raw->'info'->>'quoteType', 'EQUITY') FROM fundamentals_raw
                           WHERE market=%s AND (raw ? 'not_equity' OR raw->'income' <> '{}'::jsonb)""", (market,))
            for s, k in cur.fetchall():
                kinds.setdefault(s, k)
    return kinds


# Unambiguous fund naming conventions only (a name ENDING in ETF/BEES, LIQUID, NIFTY, fund-house gold/silver
# products...) — a loose pattern catches real companies (JETFREIGHT, GOLDENTOBC, CHEMBOND). Applied only to India
# symbols not yet classified; classify() is the real test, this is the stopgap until it has run.
import re
_FUND_NAME = re.compile(r"(BEES|IETF|ETF)$|LIQUID|NIFTY|SENSEX|GILT|GSEC|LOWVOL|^(AONE|BBNPP|CHOICE|GROWW|HSBC|MO|UNION|LICNETF)(GOLD|SILVER)")


def eligible(market: str) -> list[str]:
    """Common stocks of the market's universe: US as listed (the universe file already drops ETFs);
    India minus everything classified as not an equity."""
    syms = [s for s in universe.load_universe(market) if not s.startswith("^")]
    if market == "us":  # closed-end funds / income trusts, flagged by the `classify` job (marketdata/subindustries.py)
        kinds = _known_kinds(market)
        return [s for s in syms if kinds.get(s) != "FUND"]
    if market == "india":
        kinds = _known_kinds(market)
        syms = [s for s in syms if kinds.get(s) == "EQUITY" or (s not in kinds and not _FUND_NAME.search(s.removesuffix(".NS")))]
    return syms


def classify(market: str, top: int = 1800, workers: int = 2) -> dict:
    """Label the most-traded unclassified symbols as equity / fund via yfinance quoteType.
    One-off for the bulk (minutes); later runs only check newly-liquid names."""
    import yfinance as yf
    init_schema()
    known = _known_kinds(market)
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT symbol FROM (SELECT DISTINCT ON (symbol) symbol, dollar_vol_sma20 FROM prices
                         WHERE market=%s AND date >= (SELECT max(date) FROM prices WHERE market=%s) - 10
                           AND dollar_vol_sma20 IS NOT NULL AND symbol NOT LIKE '^%%' ORDER BY symbol, date DESC) l
                       ORDER BY dollar_vol_sma20 DESC LIMIT %s""", (market, market, top))
        todo = [s for (s,) in cur.fetchall() if s not in known]
    counts: dict[str, int] = {}

    def look(sym):
        # the data source rate-limits bursts (HTTP 429): back off and retry rather than hammering it
        for wait in (0, 30, 120):
            time.sleep(wait)
            try:
                return sym, yf.Ticker(sym).info or {}
            except Exception as exc:  # noqa: BLE001
                if "Too Many Requests" not in str(exc) and "429" not in str(exc):
                    logger.warning("classify %s failed: %s", sym, exc)
                    return sym, None
        logger.warning("classify %s: still rate-limited, left for the next run", sym)
        return sym, None

    # the lookups are network waits, so run several at once; database writes stay on this thread
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, (sym, info) in enumerate(pool.map(look, todo), 1):
            if info is None:
                continue
            kind = info.get("quoteType") or "UNKNOWN"
            with db.get_connection().cursor() as cur:
                cur.execute("""INSERT INTO symbol_kind (market, symbol, kind, sector) VALUES (%s, %s, %s, %s)
                               ON CONFLICT (market, symbol) DO UPDATE SET kind=EXCLUDED.kind, sector=EXCLUDED.sector, checked_at=now()""",
                            (market, sym, kind, info.get("sector")))
            counts[kind] = counts.get(kind, 0) + 1
            if i % 100 == 0:
                logger.info("classified %d/%d %s", i, len(todo), counts)
    return {"checked": len(todo), **counts}


# ---------------------------------------------------------------- the daily computation

_SQL = """
WITH base AS (
  SELECT symbol, date, close, high, low, sma50, dollar_vol_sma20,
         lag(close) OVER w AS prev,
         lag(close, %(month)s) OVER w AS month_ago,
         avg(close) OVER (w ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS sma5,
         max(high) OVER (w ROWS BETWEEN 251 PRECEDING AND CURRENT ROW) AS hi252,
         min(low) OVER (w ROWS BETWEEN 251 PRECEDING AND CURRENT ROW) AS lo252,
         count(*) OVER (w ROWS BETWEEN 251 PRECEDING AND CURRENT ROW) AS bars
  FROM prices
  WHERE market = %(market)s AND symbol = ANY(%(symbols)s) AND date >= %(lookback)s
  WINDOW w AS (PARTITION BY symbol ORDER BY date)
), ranked AS (
  SELECT *, row_number() OVER (PARTITION BY date ORDER BY dollar_vol_sma20 DESC) AS rnk
  FROM base WHERE date >= %(start)s AND dollar_vol_sma20 IS NOT NULL AND prev IS NOT NULL AND prev > 0
)
SELECT date, count(*),
  count(*) FILTER (WHERE close > prev), count(*) FILTER (WHERE close < prev),
  count(*) FILTER (WHERE close / prev - 1 >= %(big)s), count(*) FILTER (WHERE close / prev - 1 <= -%(big)s),
  count(*) FILTER (WHERE bars >= %(minbars)s AND high >= hi252), count(*) FILTER (WHERE bars >= %(minbars)s AND low <= lo252),
  count(*) FILTER (WHERE close > sma5), count(*) FILTER (WHERE sma50 IS NOT NULL AND close > sma50),
  count(*) FILTER (WHERE month_ago > 0 AND close / month_ago - 1 >= 0.25), count(*) FILTER (WHERE month_ago > 0 AND close / month_ago - 1 <= -0.25),
  count(*) FILTER (WHERE month_ago > 0 AND close / month_ago - 1 >= 0.50), count(*) FILTER (WHERE month_ago > 0 AND close / month_ago - 1 <= -0.50)
FROM ranked WHERE rnk <= %(n)s
GROUP BY date ORDER BY date
"""


def compute(market: str, start: str | None = None) -> int:
    """(Re)compute breadth from `start` (default: a week before the last stored day) to the latest prices."""
    init_schema()
    if start is None:
        with db.get_connection().cursor() as cur:
            cur.execute("SELECT max(date) FROM breadth_daily WHERE market=%s", (market,))
            last = cur.fetchone()[0]
        start = (pd.Timestamp(last) - pd.Timedelta(days=7)).date().isoformat() if last else HISTORY_START
    lookback = (pd.Timestamp(start) - pd.Timedelta(days=420)).date().isoformat()  # room for the 252-bar windows
    params = {"market": market, "symbols": eligible(market), "start": start, "lookback": lookback, "month": MONTH_BARS,
              "big": BIG_MOVE, "minbars": MIN_HISTORY_BARS, "n": BREADTH_N}
    t0 = time.time()
    with db.get_connection().cursor() as cur:
        cur.execute(_SQL, params)
        rows = cur.fetchall()
    # a day with only a few stray rows (a holiday or a partial load) is not a market day
    # ...and on a real session most stocks move: a holiday whose stray rows all repeat the previous close
    # shows ~no advancers or decliners
    rows = [r for r in rows if r[1] >= BREADTH_N * 0.5 and (r[2] or 0) + (r[3] or 0) >= 0.5 * r[1]]
    db.execute_values("""INSERT INTO breadth_daily (market, date, n, adv, dec, up4, dn4, highs, lows, above5, above50, up25m, dn25m, up50m, dn50m)
                         VALUES %s ON CONFLICT (market, date) DO UPDATE SET n=EXCLUDED.n, adv=EXCLUDED.adv, dec=EXCLUDED.dec,
                         up4=EXCLUDED.up4, dn4=EXCLUDED.dn4, highs=EXCLUDED.highs, lows=EXCLUDED.lows, above5=EXCLUDED.above5,
                         above50=EXCLUDED.above50, up25m=EXCLUDED.up25m, dn25m=EXCLUDED.dn25m, up50m=EXCLUDED.up50m, dn50m=EXCLUDED.dn50m""",
                      [(market, *r) for r in rows])
    logger.info("breadth %s: %d days from %s in %.1fs", market, len(rows), start, time.time() - t0)
    return len(rows)


def fetch_indexes(market: str) -> dict:
    """Refresh the index and volatility-index series the page needs (a few small downloads)."""
    import yfinance as yf
    out = {}
    for key, ticker, _ in [*INDEXES[market], VOL_INDEX[market]]:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                raw = yf.Ticker(ticker).history(period="max", interval="1d", auto_adjust=False)
            if raw is None or raw.empty:
                raise ValueError("no data")
            raw.index = pd.to_datetime(raw.index).tz_localize(None)
            raw = raw[raw.index >= "2010-01-01"]
            rows = [(market, key, d.date(), float(c)) for d, c in raw["Close"].dropna().items() if c > 0]
            db.execute_values("INSERT INTO index_series (market, series, date, close) VALUES %s "
                              "ON CONFLICT (market, series, date) DO UPDATE SET close = EXCLUDED.close", rows)
            out[key] = len(rows)
        except Exception as exc:  # noqa: BLE001 — one missing index must not stop the rest
            logger.warning("index %s (%s) failed: %s", key, ticker, exc)
            out[key] = 0
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Compute market breadth from stored prices")
    ap.add_argument("--market", required=True, choices=["us", "india"])
    ap.add_argument("--full", action="store_true", help=f"recompute everything since {HISTORY_START}")
    ap.add_argument("--classify", action="store_true", help="label the most-traded symbols as stock / fund first")
    ap.add_argument("--no-indexes", action="store_true", help="skip refreshing the index and VIX series")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    init_schema()
    from .. import runlog
    with runlog.track("breadth", market=a.market, label=f"{a.market.upper()} market breadth") as st:
        if a.classify:
            print("classified:", classify(a.market))
        if not a.no_indexes:
            print("indexes:", fetch_indexes(a.market))
        n = compute(a.market, HISTORY_START if a.full else None)
        print("breadth days written:", n)
        st.detail = f"{n} day(s) written" + (" (full history)" if a.full else "")


if __name__ == "__main__":
    main()
