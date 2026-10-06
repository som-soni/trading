"""Current-snapshot fundamentals, for the LIVE SCREENER ONLY.

SEPA part 2 wants strong and ideally accelerating growth in earnings and
sales, improving margins, and earnings that beat expectations. This module
supplies what is actually obtainable, and it is important to be precise about
why that is less than the method asks for.

What yfinance gives (measured, not assumed)
-------------------------------------------
- `quarterly_income_stmt`: **5 quarters**, on both AAPL and RELIANCE.NS.
- `income_stmt`: 4-5 annual periods.
- `earnings_dates` (EPS estimate vs actual, i.e. the "beat"): raises
  ImportError without `lxml` installed, and carries only a few quarters even
  with it.

Five quarters is exactly enough for ONE year-over-year comparison (Q0 vs Q4)
and not enough for acceleration, which needs this year's quarterly growth set
against last year's -- 8+ quarters. So:

    growth              YES (one YoY reading)
    margin direction    YES (one YoY reading)
    acceleration        NO
    earnings surprise   NO

Why this is screener-only
-------------------------
Every figure here is the CURRENT restatement with no as-of history. For a live
screen that is correct by construction: today's fundamentals are what is known
today. For a backtest it is severe lookahead -- ranking a 2015 stock by a 2026
margin. **Nothing in `backtesting/` may import this module.** The Minervini
backtest therefore measures the technical four-fifths of SEPA and says so.

To backtest part 2 properly you need point-in-time fundamentals: Sharadar via
Nasdaq Data Link, Compustat PIT or S&P Capital IQ for the US; Trendlyne or
Screener.in carry some India history.
"""

import logging
from datetime import datetime, timezone

import pandas as pd

from ..paths import DATA_DIR

logger = logging.getLogger(__name__)

CACHE_REFRESH_DAYS = 7
COLUMNS = [
    "symbol", "revenue_yoy_pct", "earnings_yoy_pct", "gross_margin_pct",
    "gross_margin_change_pp", "quarters_available", "fetched_at",
]


def cache_path(market: str):
    return DATA_DIR / f"fundamentals_cache_{market}.csv"


def _load_cache(market: str) -> pd.DataFrame:
    path = cache_path(market)
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    return pd.read_csv(path, parse_dates=["fetched_at"])


def _save_cache(market: str, df: pd.DataFrame) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_path(market), index=False)


def _row(series: pd.DataFrame, *names: str) -> pd.Series | None:
    """Income-statement line lookup. yfinance's row labels vary by filer, so
    try several spellings rather than assuming one."""
    for n in names:
        if n in series.index:
            return series.loc[n]
    return None


def fetch_one(symbol: str) -> dict:
    """One symbol's current fundamental snapshot. Never raises: a missing
    filing must degrade to None, not abort a 5,000-symbol screen."""
    out = {
        "symbol": symbol, "revenue_yoy_pct": None, "earnings_yoy_pct": None,
        "gross_margin_pct": None, "gross_margin_change_pp": None,
        "quarters_available": 0,
    }
    try:
        import yfinance as yf

        q = yf.Ticker(symbol).quarterly_income_stmt
        if q is None or q.empty:
            return out
        # columns are periods, newest first
        q = q.reindex(sorted(q.columns, reverse=True), axis=1)
        out["quarters_available"] = int(q.shape[1])

        rev = _row(q, "Total Revenue", "Operating Revenue")
        ni = _row(q, "Net Income", "Net Income Common Stockholders")
        gp = _row(q, "Gross Profit")

        def yoy(s):
            """Q0 against Q4 -- the same fiscal quarter a year earlier, which
            is the only comparison 5 quarters supports. Comparing Q0 to Q1
            would measure seasonality, not growth."""
            if s is None or len(s) < 5:
                return None
            now, ago = s.iloc[0], s.iloc[4]
            if pd.isna(now) or pd.isna(ago) or ago == 0:
                return None
            # a negative base makes the percentage meaningless (-10 -> +5 is
            # not "+150% growth"), so refuse it rather than print a number
            if ago < 0:
                return None
            return float((now - ago) / abs(ago) * 100)

        out["revenue_yoy_pct"] = yoy(rev)
        out["earnings_yoy_pct"] = yoy(ni)

        if gp is not None and rev is not None and len(gp) >= 5 and len(rev) >= 5:
            if pd.notna(gp.iloc[0]) and pd.notna(rev.iloc[0]) and rev.iloc[0]:
                gm_now = float(gp.iloc[0] / rev.iloc[0] * 100)
                out["gross_margin_pct"] = gm_now
                if pd.notna(gp.iloc[4]) and pd.notna(rev.iloc[4]) and rev.iloc[4]:
                    gm_ago = float(gp.iloc[4] / rev.iloc[4] * 100)
                    out["gross_margin_change_pp"] = gm_now - gm_ago
    except Exception as e:  # noqa: BLE001 - a screen must not die on one filer
        logger.debug("fundamentals fetch failed for %s: %s", symbol, e)
    return out


def load_fundamentals(
    market: str, symbols: list[str], refresh: bool = True,
    max_fetch: int | None = None,
) -> dict[str, dict]:
    """Cached fundamentals for `symbols`, refetching entries older than
    `CACHE_REFRESH_DAYS`.

    One HTTP round trip per symbol, so `max_fetch` bounds a cold run: the
    screener passes only the symbols that already cleared the Trend Template
    (23 of 400 in a US sample), which is what keeps this affordable.
    """
    cache = _load_cache(market)
    now = pd.Timestamp(datetime.now(timezone.utc)).tz_localize(None)
    have: dict[str, dict] = {}
    stale: list[str] = []

    indexed = cache.set_index("symbol") if not cache.empty else None
    for sym in symbols:
        if indexed is not None and sym in indexed.index:
            row = indexed.loc[sym]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            age = (now - pd.Timestamp(row["fetched_at"])).days
            have[sym] = {c: row.get(c) for c in COLUMNS if c != "fetched_at"}
            if age < CACHE_REFRESH_DAYS:
                continue
        stale.append(sym)

    from .cache import is_offline
    if refresh and stale and not is_offline():  # offline: cached values only (the `fundamentals` job refreshes)
        todo = stale[:max_fetch] if max_fetch else stale
        logger.info("fundamentals: fetching %d of %d symbols (%d cached fresh)",
                    len(todo), len(symbols), len(symbols) - len(stale))
        fetched = []
        for i, sym in enumerate(todo, 1):
            rec = fetch_one(sym)
            rec["fetched_at"] = now
            fetched.append(rec)
            have[sym] = {k: v for k, v in rec.items() if k != "fetched_at"}
            if i % 25 == 0:
                logger.info("  fundamentals %d/%d", i, len(todo))
        if fetched:
            merged = pd.concat(
                [cache[~cache["symbol"].isin([f["symbol"] for f in fetched])]
                 if not cache.empty else pd.DataFrame(columns=COLUMNS),
                 pd.DataFrame(fetched)],
                ignore_index=True,
            )
            _save_cache(market, merged)
    return have


# --- interpretation, kept next to the data it reads ---

STRONG_REVENUE_YOY = 20.0   # Minervini looks for strong sales growth
STRONG_EARNINGS_YOY = 25.0  # and stronger earnings growth than sales


def fundamental_flags(rec: dict | None) -> dict[str, bool | None]:
    """SEPA part 2 as flags. `None` means UNKNOWN, which is not the same as
    False and must not be rendered as a failure -- most of the universe has no
    usable filing here."""
    if not rec:
        return {"F_growth": None, "F_margin": None, "F_data": False}
    rev, earn = rec.get("revenue_yoy_pct"), rec.get("earnings_yoy_pct")
    margin = rec.get("gross_margin_change_pp")

    def num(v):
        return None if v is None or pd.isna(v) else float(v)

    rev, earn, margin = num(rev), num(earn), num(margin)
    growth = None
    if rev is not None or earn is not None:
        growth = bool(
            (rev is not None and rev >= STRONG_REVENUE_YOY)
            or (earn is not None and earn >= STRONG_EARNINGS_YOY)
        )
    return {
        "F_growth": growth,
        "F_margin": None if margin is None else bool(margin > 0),
        "F_data": bool(rec.get("quarters_available", 0) >= 5),
    }
