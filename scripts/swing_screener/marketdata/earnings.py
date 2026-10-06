"""Earnings-date lookup for the D2 gate.

Turns out yfinance DOES carry next-earnings-date via `Ticker.calendar`
for both US and NSE tickers (verified directly — see chat) — it's just a
per-ticker call, not a bulk one, same shape as the sector lookup. So:
auto-fetch it for whatever small set of tickers reaches this point (after
the loose screener filter), cache it locally with a refresh window (the
date moves every quarter, unlike sector), and let
data/earnings_<market>.csv be a manual override for anything auto-fetch
gets wrong or misses — overrides always win.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

from ..paths import DATA_DIR  # noqa: F401
CACHE_REFRESH_DAYS = 7  # re-check each ticker's earnings date at most weekly


def earnings_override_path(market: str) -> Path:
    return DATA_DIR / f"earnings_{market}.csv"


def earnings_cache_path(market: str) -> Path:
    return DATA_DIR / f"earnings_cache_{market}.csv"


def _load_overrides(market: str) -> dict[str, pd.Timestamp]:
    path = earnings_override_path(market)
    if not path.exists():
        return {}
    df = pd.read_csv(path, parse_dates=["next_earnings_date"])
    return {
        str(r["symbol"]).strip(): r["next_earnings_date"]
        for _, r in df.iterrows()
        if pd.notna(r["next_earnings_date"])
    }


def _load_cache(market: str) -> pd.DataFrame:
    path = earnings_cache_path(market)
    if not path.exists():
        return pd.DataFrame(columns=["symbol", "next_earnings_date", "fetched_at"])
    return pd.read_csv(path, parse_dates=["next_earnings_date", "fetched_at"])


def _save_cache(market: str, df: pd.DataFrame) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(earnings_cache_path(market), index=False)


def _fetch_next_earnings_date(symbol: str) -> pd.Timestamp | None:
    import yfinance as yf

    try:
        cal = yf.Ticker(symbol).calendar
        dates = (cal or {}).get("Earnings Date")
        if not dates:
            return None
        return pd.Timestamp(min(dates))  # nearest upcoming
    except Exception as e:
        logger.warning("Earnings date fetch failed for %s: %s", symbol, e)
        return None


def days_away(today: pd.Timestamp, edate: pd.Timestamp) -> int:
    return int(np.busday_count(today.date(), edate.date()))


def load_earnings_days_away(
    market: str, tickers: list[str], today: pd.Timestamp | None = None
) -> dict[str, int]:
    """Auto-fetch (cached, weekly refresh) + manual override, for `tickers`
    only — call this AFTER the loose screener filter, not against the full
    universe, since it's one request per ticker."""
    from .cache import is_offline
    offline = is_offline()  # stored dates only (the `earnings` job refreshes them)
    today = today or pd.Timestamp.today().normalize()
    overrides = _load_overrides(market)
    cache_df = _load_cache(market)
    cache = {
        row["symbol"]: (row["next_earnings_date"], row["fetched_at"])
        for _, row in cache_df.iterrows()
    }

    out: dict[str, int] = {}
    updated = False
    for sym in tickers:
        if sym in overrides:
            out[sym] = days_away(today, overrides[sym])
            continue

        cached = cache.get(sym)
        stale = (
            cached is None
            or pd.isna(cached[0])
            or cached[0].normalize() < today  # date already passed, need the next one
            or (today - cached[1]).days > CACHE_REFRESH_DAYS
        )
        if stale and offline:
            edate = cached[0] if cached is not None and pd.notna(cached[0]) and cached[0].normalize() >= today else None
        elif stale:
            edate = _fetch_next_earnings_date(sym)
            cache[sym] = (edate, today)
            updated = True
        else:
            edate = cached[0]

        if edate is not None and pd.notna(edate):
            out[sym] = days_away(today, edate)

    if updated:
        rows = [
            {"symbol": s, "next_earnings_date": d, "fetched_at": f}
            for s, (d, f) in cache.items()
        ]
        _save_cache(market, pd.DataFrame(rows))

    return out
