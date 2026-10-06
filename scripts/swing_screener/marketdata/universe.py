"""Universe (ticker list) + sector reference data.

Design: the ticker list changes rarely, so it's a CSV you refresh weekly/
monthly, not something re-derived every run (see STEP 2 in the prompts —
'this frozen list is the universe for the whole run'). Sector tags are
looked up lazily and cached forever, and ONLY for tickers that actually
survive the loose screener filter — looking up sector for a full
multi-thousand-ticker universe on every run would be slow for no benefit,
since the vast majority never reach a gate that needs their sector.
"""

import csv
import logging
import time
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

from ..paths import DATA_DIR  # noqa: F401

NASDAQ_TRADER_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
NYSE_TRADER_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"


def universe_csv_path(market: str) -> Path:
    return DATA_DIR / f"universe_{market}.csv"


def universe_age_days(market: str) -> float | None:
    """Days since the universe CSV was last written, or None if it
    doesn't exist yet (definitely needs a refresh)."""
    path = universe_csv_path(market)
    if not path.exists():
        return None
    return (time.time() - path.stat().st_mtime) / 86400


def sector_cache_path(market: str) -> Path:
    return DATA_DIR / f"sector_cache_{market}.csv"


def load_universe(market: str) -> list[str]:
    """Load the frozen ticker list for `market`. Raises FileNotFoundError
    with instructions if the CSV hasn't been created yet."""
    path = universe_csv_path(market)
    if not path.exists():
        raise FileNotFoundError(
            f"No universe file at {path}.\n"
            f"Create it with one ticker per line (header 'ticker'), or for "
            f"US markets run `fetch_us_universe_from_nasdaqtrader()` once "
            f"to generate it. For India, export the NSE equity list "
            f"(nseindia.com > Market Data > Securities Available for "
            f"Trading) and save it in this format."
        )
    df = pd.read_csv(path)
    if "ticker" not in df.columns:
        raise ValueError(f"{path} must have a 'ticker' column")
    return df["ticker"].dropna().astype(str).str.strip().unique().tolist()


_NON_COMMON_STOCK_KEYWORDS = (
    "warrant", "right", "rights", " unit", "units", "preferred",
    "depositary", "note", "debenture", " acquisition corp",
)


def fetch_us_universe_from_nasdaqtrader(min_price_hint: bool = True) -> Path:
    """One-time/occasional refresh of the US ticker universe from Nasdaq
    Trader's official symbol directory (free, no auth, no rate limit
    documented). Excludes test issues, ETFs, and common non-stock security
    types (warrants/rights/units/preferreds/SPAC-acquisition-corp shells)
    by a light heuristic on the Security Name — review the output before
    trusting it blindly, this isn't a perfect classifier."""
    rows: list[str] = []
    for url in (NASDAQ_TRADER_URL, NYSE_TRADER_URL):
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        text = resp.text
        lines = text.splitlines()
        if not lines:
            continue
        header = lines[0].split("|")
        try:
            sym_idx = header.index("Symbol")
        except ValueError:
            sym_idx = header.index("ACT Symbol") if "ACT Symbol" in header else 0
        name_idx = header.index("Security Name") if "Security Name" in header else None
        test_idx = header.index("Test Issue") if "Test Issue" in header else None
        etf_idx = header.index("ETF") if "ETF" in header else None
        for line in lines[1:-1]:  # last line is a file-creation-time footer
            fields = line.split("|")
            if len(fields) <= sym_idx:
                continue
            if test_idx is not None and fields[test_idx] == "Y":
                continue
            if etf_idx is not None and len(fields) > etf_idx and fields[etf_idx] == "Y":
                continue
            if name_idx is not None and len(fields) > name_idx:
                name_lower = fields[name_idx].lower()
                if any(kw in name_lower for kw in _NON_COMMON_STOCK_KEYWORDS):
                    continue
            sym = fields[sym_idx].strip()
            if not sym or "$" in sym or "." in sym:
                continue  # skip units/warrants/preferreds, simple heuristic
            rows.append(sym)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = universe_csv_path("us")
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ticker"])
        for sym in sorted(set(rows)):
            writer.writerow([sym])
    logger.info("Wrote %d US tickers to %s", len(rows), path)
    _refresh_names("us")
    return path


_NON_STOCK_NAME_KEYWORDS = ("INVIT", "TRUST", " FUND", "ETF")


def fetch_india_universe_from_yfinance_screener() -> Path:
    """One-time/occasional refresh of the NSE ticker universe via
    yfinance's screener wrapper (`yf.screen`), which proxies Yahoo
    Finance's own equity screener. Not an officially documented bulk
    listing API, but it works, needs no auth, and paginates cleanly (250
    results/page, ~3,500 NSE equities total as of writing). Excludes known
    test tickers and InvIT/REIT/trust/fund structures by a light heuristic
    on the name — review the output before trusting it blindly, same
    caveat as the US fetcher."""
    import time

    import yfinance as yf
    from yfinance import EquityQuery

    q = EquityQuery(
        "and", [EquityQuery("eq", ["region", "in"]), EquityQuery("eq", ["exchange", "NSI"])]
    )
    page_size = 250
    offset = 0
    rows: list[str] = []
    total = None

    while True:
        resp = yf.screen(q, size=page_size, offset=offset, sortField="ticker", sortAsc=True)
        total = resp.get("total", total)
        quotes = resp.get("quotes", [])
        if not quotes:
            break
        for item in quotes:
            sym = item.get("symbol", "")
            name = (item.get("shortName") or "").upper()
            if not sym or "NSETEST" in sym:
                continue
            if item.get("quoteType") != "EQUITY":
                continue
            if any(kw in name for kw in _NON_STOCK_NAME_KEYWORDS):
                continue
            rows.append(sym)
        offset += page_size
        if total is not None and offset >= total:
            break
        time.sleep(0.3)  # be polite to the endpoint

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = universe_csv_path("india")
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ticker"])
        for sym in sorted(set(rows)):
            writer.writerow([sym])
    logger.info("Wrote %d India (NSE) tickers to %s", len(rows), path)
    _refresh_names("india")
    return path


def _refresh_names(market: str) -> None:
    """Keep company names (marketdata/names.py) in step with the universe; never fails the refresh."""
    try:
        from . import names
        names.refresh(market)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Company names not refreshed (%s); run `python3 -m swing_screener.marketdata.names`", exc)


def load_sector_cache(market: str) -> dict[str, str]:
    path = sector_cache_path(market)
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    return dict(zip(df["ticker"], df["sector"]))


def save_sector_cache(market: str, sectors: dict[str, str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = sector_cache_path(market)
    pd.DataFrame(
        {"ticker": list(sectors.keys()), "sector": list(sectors.values())}
    ).to_csv(path, index=False)


def get_market_caps_cr(tickers: list[str]) -> dict[str, float | None]:
    """Market cap in crore (1 crore = 1e7) for each ticker.

    Read first from `symbol_industry` (market caps captured with the industry
    classification, refreshed monthly — ample for a market-cap floor); only
    tickers missing there are looked up via yfinance .info, and not at all in
    offline mode (they come back None, which the floor treats as unknown)."""
    from . import cache
    out: dict[str, float | None] = {}
    try:
        from . import industries
        known = industries.load("india")
        for t in tickers:
            cap = known.get(t, (None, None, None))[2]
            if cap:
                out[t] = cap / 1e7
    except Exception as e:  # noqa: BLE001 - table not built yet
        logger.info("Market caps not in symbol_industry (%s); looking them up", e)
    todo = [t for t in tickers if t not in out]
    if cache.is_offline():
        out.update({t: None for t in todo})
        return out
    import yfinance as yf

    for t in todo:
        try:
            cap = yf.Ticker(t).info.get("marketCap")
            out[t] = (cap / 1e7) if cap else None
        except Exception as e:
            logger.warning("Market cap lookup failed for %s: %s", t, e)
            out[t] = None
    return out


def get_sectors(market: str, tickers: list[str]) -> dict[str, str]:
    """Return {ticker: sector} for `tickers`, using the cache for anything
    already looked up and yfinance for the rest. Writes back to the cache
    so the lookup never repeats for a given ticker."""
    cache = load_sector_cache(market)
    missing = [t for t in tickers if t not in cache]
    from . import cache as price_cache
    if missing and price_cache.is_offline():
        # no network: take the sector from the industry classification instead
        try:
            from . import industries
            known = industries.load(market)
            return {t: cache.get(t) or (known.get(t) or ("Unknown",))[0] for t in tickers}
        except Exception:  # noqa: BLE001
            return {t: cache.get(t, "Unknown") for t in tickers}
    if missing:
        import yfinance as yf  # local import: only needed on cache miss

        for t in missing:
            try:
                info = yf.Ticker(t).info
                cache[t] = info.get("sector") or info.get("industry") or "Unknown"
            except Exception as e:
                logger.warning("Sector lookup failed for %s: %s", t, e)
                cache[t] = "Unknown"
        save_sector_cache(market, cache)
    return {t: cache.get(t, "Unknown") for t in tickers}
