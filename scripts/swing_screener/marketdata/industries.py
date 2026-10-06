"""Sector and industry for every stock, stored in Postgres (`symbol_industry`).

The Sectors page groups stocks by industry, so it needs a finer split than the
11 broad sectors: "Technology" mixes semiconductors, software and IT services,
which often move in opposite directions. Yahoo's classification (11 sectors,
~145 industries, GICS-like) is used for both markets so groups are comparable.

It is fetched one *industry* at a time through Yahoo's equity screener — about
150 requests per market, a couple of minutes — rather than one request per
symbol, which would take an hour and trip the rate limit. Each row also carries
the market cap, used to cap-weight group returns.

    python3 -m swing_screener.marketdata.industries               # both markets
    python3 -m swing_screener.marketdata.industries --market india

Classifications change rarely; refresh monthly or after a universe refresh.
"""

import argparse
import logging
import time

from . import db

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS symbol_industry (
    market VARCHAR(16) NOT NULL,
    symbol TEXT NOT NULL,
    sector TEXT NOT NULL,
    industry TEXT NOT NULL,
    market_cap DOUBLE PRECISION,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, symbol)
);
"""
_REGION = {"us": [("region", "us")], "india": [("region", "in"), ("exchange", "NSI")]}
PAGE = 250


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _screen(query, offset: int) -> dict:
    import yfinance as yf
    for wait in (0, 20, 60, 180):  # Yahoo answers bursts with HTTP 429: back off rather than hammer it
        time.sleep(wait)
        try:
            return yf.screen(query, size=PAGE, offset=offset, sortField="intradaymarketcap", sortAsc=False) or {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("industries: screen failed (%s), retrying", exc)
    return {}


def fetch(market: str) -> list[tuple]:
    """(symbol, sector, industry, market_cap) for every equity Yahoo lists in the market."""
    from yfinance import EquityQuery as Q
    from yfinance.const import SECTOR_INDUSTY_MAPPING
    rows, seen = [], set()
    for sector, industries in SECTOR_INDUSTY_MAPPING.items():
        for industry in sorted(industries):
            query = Q("and", [Q("eq", ["industry", industry]), *[Q("eq", [k, v]) for k, v in _REGION[market]]])
            offset = 0
            while True:
                resp = _screen(query, offset)
                quotes = resp.get("quotes", [])
                for x in quotes:
                    sym = x.get("symbol")
                    if sym and sym not in seen and x.get("quoteType") == "EQUITY":
                        seen.add(sym)
                        rows.append((sym, sector, industry, x.get("marketCap")))
                offset += PAGE
                if not quotes or offset >= (resp.get("total") or 0):
                    break
                time.sleep(0.4)
            time.sleep(0.4)
        logger.info("industries %s: %s done (%d stocks so far)", market, sector, len(rows))
    return rows


def refresh(market: str) -> int:
    init_schema()
    rows = fetch(market)
    if not rows:
        return 0
    db.execute_values(
        """INSERT INTO symbol_industry (market, symbol, sector, industry, market_cap) VALUES %s
           ON CONFLICT (market, symbol) DO UPDATE SET sector=EXCLUDED.sector, industry=EXCLUDED.industry,
             market_cap=EXCLUDED.market_cap, updated_at=now()""",
        [(market, *r) for r in rows])
    logger.info("industries %s: %d stored", market, len(rows))
    return len(rows)


def load(market: str) -> dict[str, tuple]:
    """symbol -> (sector, industry, market_cap)."""
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol, sector, industry, market_cap FROM symbol_industry WHERE market=%s", (market,))
        return {s: (sec, ind, cap) for s, sec, ind, cap in cur.fetchall()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", choices=["us", "india"])
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    from .. import runlog
    for m in [a.market] if a.market else ["us", "india"]:
        with runlog.track("industries", market=m, label=f"{m.upper()} industry classification") as st:
            n = refresh(m)
            st.detail = f"{n:,} stocks classified"
            print(m, n)


if __name__ == "__main__":
    main()
