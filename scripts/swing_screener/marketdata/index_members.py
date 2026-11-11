"""Index membership lists — TODAY's members of an index, as published by its exchange.

One list so far: the Nasdaq 100, from Nasdaq's own quote-list endpoint. The masonson_tqqq strategy
reads it for its breadth rule (% of Nasdaq 100 members above their 50-day average), computed from
the members' stored daily bars.

What this is NOT: a point-in-time membership history. A backtest that reads it over past years ranks
today's members -- the survivors -- so a breadth reading for 2002 counts the companies that went on
to be in the index in 2026, and leaves out the ones that were dropped. The strategy's caveats say so.

    python3 -m swing_screener.marketdata.index_members --refresh
    python3 -m swing_screener.marketdata.index_members --list
"""

import argparse
import datetime as dt
import logging

from . import db

logger = logging.getLogger("index_members")

SCHEMA = """
CREATE TABLE IF NOT EXISTS index_members (
    market VARCHAR(16) NOT NULL,
    index_key VARCHAR(32) NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT,
    fetched_on DATE NOT NULL,
    PRIMARY KEY (market, index_key, symbol)
);
"""

# index key -> (market, URL). Nasdaq's endpoint wants a browser-like user agent and returns JSON.
SOURCES = {
    "NASDAQ100": ("us", "https://api.nasdaq.com/api/quote/list-type/nasdaq100"),
}
USER_AGENT = "Mozilla/5.0 (compatible; swing-screener research)"
#: a fetched list shorter than this is a broken response, not the index -- keep the stored one
MIN_MEMBERS = 90


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _symbol(raw: str) -> str:
    """Nasdaq writes share classes with a slash or dot (BRK/B); stored prices use a dash."""
    return raw.strip().upper().replace("/", "-").replace(".", "-")


def fetch(index_key: str) -> list[tuple[str, str]]:
    import requests
    _market, url = SOURCES[index_key]
    r = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, timeout=30)
    r.raise_for_status()
    rows = ((r.json().get("data") or {}).get("data") or {}).get("rows") or []
    out = [(_symbol(x["symbol"]), (x.get("companyName") or "").strip()) for x in rows if x.get("symbol")]
    if len(out) < MIN_MEMBERS:
        raise ValueError(f"{index_key}: only {len(out)} members returned -- not replacing the stored list")
    return out


def refresh(index_key: str = "NASDAQ100") -> int:
    """Replace the stored list with today's. Returns the member count."""
    init_schema()
    market, _url = SOURCES[index_key]
    members = fetch(index_key)
    today = dt.date.today()
    conn = db.get_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM index_members WHERE market=%s AND index_key=%s", (market, index_key))
    db.execute_values("INSERT INTO index_members (market, index_key, symbol, name, fetched_on) VALUES %s",
                      [(market, index_key, s, n, today) for s, n in members])
    logger.info("%s:%s %d members (%s)", market, index_key, len(members), today)
    return len(members)


def load(market: str, index_key: str) -> tuple[list[str], dt.date | None]:
    """(symbols, the date the list was fetched). Raises if nothing is stored."""
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol, fetched_on FROM index_members WHERE market=%s AND index_key=%s ORDER BY symbol",
                    (market, index_key))
        rows = cur.fetchall()
    if not rows:
        raise ValueError(f"{market}:{index_key} members not stored -- run "
                         f"`python3 -m swing_screener.marketdata.index_members --refresh`")
    return [s for s, _ in rows], rows[0][1]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Index membership lists (today's members)")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    for key, (market, _url) in SOURCES.items():
        if a.refresh:
            refresh(key)
        syms, on = load(market, key)
        print(f"{market}:{key} {len(syms)} members, fetched {on}: {' '.join(syms)}")


if __name__ == "__main__":
    main()
