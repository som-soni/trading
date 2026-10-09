"""Company names for every symbol, stored in Postgres (`symbol_names`).

Tickers alone are hard to read, so the web app shows the company name next to
each one and symbol search matches names too ("apple", "reliance ind").
Names come from the exchanges' own symbol directories — one request per file,
no rate limits:

  US     Nasdaq Trader's nasdaqlisted.txt + otherlisted.txt (NASDAQ, NYSE, NYSE
         American, ARCA, BATS), "Security Name" with the share-class wording
         trimmed ("Apple Inc. Common Stock" -> "Apple Inc.").
  India  NSE's EQUITY_L.csv (main board), SME_EQUITY_L.csv (SME platform) and
         eq_etfseclist.csv (ETFs, named by what they track: "Nifty 50 ETF").

    python3 -m swing_screener.marketdata.names              # refresh both markets
    python3 -m swing_screener.marketdata.names --market us

The web server fills an empty table on startup, and a universe refresh
(`universe.py`) refreshes names as well, so this rarely needs running by hand.
"""

import argparse
import csv
import io
import logging
import re

import requests

from . import db

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS symbol_names (
    market VARCHAR(16) NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    source TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, symbol)
);
ALTER TABLE symbol_names ADD COLUMN IF NOT EXISTS is_adr BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE symbol_names ADD COLUMN IF NOT EXISTS country TEXT;
"""

US_URLS = ("https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
           "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt")
INDIA_URLS = ("https://archives.nseindia.com/content/equities/EQUITY_L.csv",
              "https://archives.nseindia.com/emerge/corporates/content/SME_EQUITY_L.csv")
INDIA_ETF_URL = "https://archives.nseindia.com/content/equities/eq_etfseclist.csv"
_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}

# Index symbols in `prices` and series in `index_series` (no exchange list names these)
INDEX_NAMES = {
    "india": {"^NSEI": "Nifty 50", "^NSEBANK": "Nifty Bank", "^CNXIT": "Nifty IT", "^CNXAUTO": "Nifty Auto", "^CNXFMCG": "Nifty FMCG",
              "^CNXMEDIA": "Nifty Media", "^CNXMETAL": "Nifty Metal", "^CNXPHARMA": "Nifty Pharma", "^CNXPSUBANK": "Nifty PSU Bank",
              "^CNXREALTY": "Nifty Realty", "^CRSLDX": "Nifty 500", "^INDIAVIX": "India VIX", "NIFTY_FIN_SERVICE.NS": "Nifty Financial Services",
              "NIFTY_HEALTHCARE.NS": "Nifty Healthcare", "NIFTY_PVT_BANK.NS": "Nifty Private Bank",
              "NIFTY50": "Nifty 50", "NIFTY50_TR": "Nifty 50 Total Return", "NIFTY500": "Nifty 500", "NEXT50": "Nifty Next 50",
              "MIDCAP": "Nifty Midcap 100", "SENSEX": "BSE Sensex", "INDIAVIX": "India VIX", "GOLD": "Gold (INR)",
              "USDINR": "US dollar in rupees", "US_IN_INR": "S&P 500 in rupees", "CASH_FUND": "Liquid fund (cash proxy)"},
    "us": {"^VIX": "CBOE Volatility Index", "SPX": "S&P 500", "SP500_TR": "S&P 500 Total Return", "SP500_PRICE_LONG": "S&P 500 (long history)",
           "NDX": "Nasdaq 100", "NASDAQ100": "Nasdaq 100", "RUT": "Russell 2000", "RUSSELL2000": "Russell 2000", "VIX": "CBOE Volatility Index",
           "TOTAL_MKT": "US total market", "INTL": "International stocks", "BONDS": "US bonds", "BONDS_LONG": "Long-term US Treasuries",
           "GOLD": "Gold", "CASH_YIELD": "Cash (T-bill yield)"},
}

# "Apple Inc. Common Stock", "Alphabet Inc. - Class A Common Stock", "Shell plc American Depositary Shares ..."
_US_SUFFIX = re.compile(
    r"\s*(?:[-,]\s*)?(?:Class [A-Z]\b.*|(?:New )?(?:Common|Ordinary|Capital|Subordinate Voting|Voting)\s+(?:Stock|Shares?|Units?).*|"
    r"American Depositary (?:Shares|Receipts?).*|Depositary (?:Shares|Receipts?).*|Common Units?.*|Shares of Beneficial Interest.*|"
    r"Units?\b.*|Warrants?\b.*|Rights?\b.*)$", re.I)


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def clean_us_name(raw: str) -> str:
    name = raw.strip()
    head = name.split(" - ")[0].strip()  # "ATA Creativity Global - American Depositary Shares, ..."
    head = _US_SUFFIX.sub("", head).strip(" ,-")
    if head.endswith(" (The)"):  # "Coca-Cola Company (The)" -> "The Coca-Cola Company"
        head = "The " + head[:-6]
    return head or name


ADRS: set[str] = set()   # US listings of foreign companies (ADRs and foreign ordinaries), filled by fetch_us
COUNTRY: dict[str, str] = {}
NASDAQ_SCREENER_URL = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&download=true"


def fetch_us_countries() -> dict[str, str]:
    """Country of incorporation per US-listed stock, from Nasdaq's stock screener (one request). The
    symbol directories do not say reliably whether a listing is an ADR; the country does."""
    try:
        resp = requests.get(NASDAQ_SCREENER_URL, timeout=60, headers=_UA)
        resp.raise_for_status()
        rows = resp.json()["data"]["rows"]
    except Exception as exc:  # noqa: BLE001 - names are still useful without countries
        logger.warning("names: country lookup failed (%s)", exc)
        return {}
    return {r["symbol"].strip().replace("/", "-").replace(".", "-"): r["country"].strip()
            for r in rows if r.get("symbol") and r.get("country")}


def fetch_us() -> dict[str, str]:
    out: dict[str, str] = {}
    for url in US_URLS:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        lines = resp.text.splitlines()
        header = lines[0].split("|")
        sym_i = header.index("Symbol") if "Symbol" in header else header.index("ACT Symbol")
        name_i = header.index("Security Name")
        for line in lines[1:]:
            f = line.split("|")
            if len(f) <= max(sym_i, name_i) or line.startswith("File Creation Time"):
                continue
            sym = f[sym_i].strip().replace(".", "-")  # BRK.B is BRK-B in the price data
            if sym and f[name_i].strip():
                out.setdefault(sym, clean_us_name(f[name_i]))
                if re.search(r"Depositary (Shares?|Receipts?)|\bADRs?\b|\bADS\b", f[name_i], re.I):
                    ADRS.add(sym)
    return out


def fetch_india() -> dict[str, str]:
    out: dict[str, str] = {}
    for url in INDIA_URLS:
        try:
            resp = requests.get(url, timeout=30, headers=_UA)
            resp.raise_for_status()
        except requests.RequestException as exc:  # the SME list is a nice-to-have
            logger.warning("names: %s failed (%s)", url, exc)
            continue
        rows = csv.reader(io.StringIO(resp.text))
        header = [h.strip().upper().replace(" ", "_") for h in next(rows)]
        sym_i, name_i = header.index("SYMBOL"), header.index("NAME_OF_COMPANY")
        for r in rows:
            if len(r) > max(sym_i, name_i) and r[sym_i].strip():
                out.setdefault(r[sym_i].strip() + ".NS", r[name_i].strip())
    try:  # ETFs: the list's own SecurityName is an internal code (NIPINDETFNIFTYBEES), so use the underlying
        resp = requests.get(INDIA_ETF_URL, timeout=30, headers=_UA)
        resp.raise_for_status()
        for r in csv.DictReader(io.StringIO(resp.text)):
            sym, under = (r.get("Symbol") or "").strip(), (r.get("Underlying Asset") or "").strip()
            if sym and under:
                out.setdefault(sym + ".NS", under if re.search(r"\b(ETF|Fund|BeES)\b", under, re.I) else f"{under} ETF")
    except requests.RequestException as exc:
        logger.warning("names: %s failed (%s)", INDIA_ETF_URL, exc)
    return out


def refresh(market: str) -> int:
    """Download the market's names and upsert them. Returns how many were stored."""
    init_schema()
    names = fetch_us() if market == "us" else fetch_india()
    if market == "us":
        COUNTRY.update(fetch_us_countries())
        ADRS.update(s for s, c in COUNTRY.items() if c != "United States")
    if not names:
        return 0
    names.update(INDEX_NAMES[market])
    src = "nasdaqtrader" if market == "us" else "nse"
    db.execute_values(
        """INSERT INTO symbol_names (market, symbol, name, source, is_adr, country) VALUES %s
           ON CONFLICT (market, symbol) DO UPDATE SET name=EXCLUDED.name, source=EXCLUDED.source,
             is_adr=EXCLUDED.is_adr, country=EXCLUDED.country, updated_at=now()""",
        [(market, s, n, src, s in ADRS, COUNTRY.get(s) if market == "us" else "India") for s, n in names.items()])
    logger.info("names %s: %d stored", market, len(names))
    return len(names)


def load(market: str) -> dict[str, str]:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol, name FROM symbol_names WHERE market=%s", (market,))
        return dict(cur.fetchall())


def lookup(names: dict[str, str], symbol: str) -> str | None:
    """A symbol's name; NSE series suffixes ("ZTECH-SM.NS") fall back to the base symbol."""
    if symbol in names:
        return names[symbol]
    m = re.match(r"^(.+)-[A-Z]{1,2}\.NS$", symbol)
    return names.get(m.group(1) + ".NS") if m else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", choices=["us", "india"])
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from .. import runlog
    for m in [a.market] if a.market else ["us", "india"]:
        with runlog.track("names", market=m, label=f"{m.upper()} company names") as st:
            n = refresh(m)
            st.detail = f"{n:,} names stored"
            print(m, n)


if __name__ == "__main__":
    main()
