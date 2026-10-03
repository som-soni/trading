"""Postgres-backed price cache so a daily run only pulls NEW bars, not the
full lookback window every time (see DATA PULL in the prompts: 'pull with
at most 4 requests in parallel... keep all pulled data for the rest of the
run'). Indicators are precomputed and stored alongside raw OHLCV on every
save — they're purely backward-looking (no lookahead), so computing them
once here instead of re-deriving them from scratch in every caller (and
every backtest day) is free correctness-wise and saves real time.
"""

import logging

import pandas as pd

from . import db

from ..core import indicators as ind
from ..providers.base import DataProvider

logger = logging.getLogger(__name__)

_RAW_COLUMNS = ["open", "high", "low", "close", "volume"]
_INDICATOR_COLUMNS = [
    "sma20", "sma50", "sma100", "sma200", "ema20", "rsi14", "rsi_ma",
    "atr14", "atr_pct", "adx14", "vol_sma50", "dollar_vol_sma20", "high_252",
]


def load_cached(market: str, symbol: str) -> pd.DataFrame | None:
    """Raw OHLCV only (same contract as before) — callers run their own
    ind.enrich_daily() on top; the precomputed indicator columns in
    Postgres are there for the backtest fast-path, not this function."""
    conn = db.get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT date, open, high, low, close, volume FROM prices "
            "WHERE market=%s AND symbol=%s ORDER BY date",
            (market, symbol),
        )
        rows = cur.fetchall()
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["Date", "open", "high", "low", "close", "volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date")


def load_cached_with_indicators(market: str, symbol: str, as_of: pd.Timestamp, tail: int = 70) -> pd.DataFrame | None:
    """The trailing `tail` rows up to and including `as_of`, WITH the
    precomputed indicator columns — used by the backtest's cache-hit path
    so it doesn't need to re-run ind.enrich_daily() on an expanding slice
    every simulated day."""
    conn = db.get_connection()
    cols = ", ".join(["date"] + _RAW_COLUMNS + _INDICATOR_COLUMNS)
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {cols} FROM prices WHERE market=%s AND symbol=%s AND date<=%s "
            f"ORDER BY date DESC LIMIT %s",
            (market, symbol, as_of.date(), tail),
        )
        rows = cur.fetchall()
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["Date"] + _RAW_COLUMNS + _INDICATOR_COLUMNS)
    df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date").sort_index()


def save_cached(market: str, symbol: str, df: pd.DataFrame) -> None:
    if df is None or df.empty:
        return
    enriched = ind.enrich_daily(df)
    rows = [
        (
            market, symbol, idx.date(),
            *[db.py_value(row.get(c)) for c in _RAW_COLUMNS],
            *[db.py_value(row.get(c)) for c in _INDICATOR_COLUMNS],
        )
        for idx, row in enriched.iterrows()
    ]
    all_cols = ["market", "symbol", "date"] + _RAW_COLUMNS + _INDICATOR_COLUMNS
    update_cols = _RAW_COLUMNS + _INDICATOR_COLUMNS
    query = (
        f"INSERT INTO prices ({', '.join(all_cols)}) VALUES %s "
        f"ON CONFLICT (market, symbol, date) DO UPDATE SET "
        + ", ".join(f"{c}=EXCLUDED.{c}" for c in update_cols)
    )
    db.execute_values(query, rows)


def get_bars(
    provider: DataProvider,
    market: str,
    symbol: str,
    lookback_days: int,
) -> pd.DataFrame | None:
    """Return at least `lookback_days` of daily bars for `symbol`, pulling
    only the incremental tail from `provider` if a cache already covers
    most of the history. Returns None if the symbol could not be loaded at
    all (caller should list it under 'Not reviewed')."""
    cached = load_cached(market, symbol)

    if cached is None or cached.empty:
        try:
            fresh = provider.get_daily_bars(symbol, lookback_days)
        except Exception as e:
            logger.warning("Failed to fetch %s: %s", symbol, e)
            return None
        if fresh is None or fresh.empty:
            return None
        save_cached(market, symbol, fresh)
        return fresh

    last_cached_date = cached.index[-1]
    try:
        new_rows = provider.get_daily_bars(
            symbol, lookback_days, start_after=last_cached_date
        )
    except Exception as e:
        logger.warning(
            "Incremental fetch failed for %s, using stale cache: %s", symbol, e
        )
        new_rows = pd.DataFrame(columns=cached.columns)

    if new_rows is not None and not new_rows.empty:
        combined = pd.concat([cached, new_rows])
        combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    else:
        combined = cached

    if len(combined) < lookback_days:
        # cache doesn't have enough history yet (e.g. lookback_days grew) —
        # backfill with a full pull
        try:
            fresh = provider.get_daily_bars(symbol, lookback_days)
            if fresh is not None and not fresh.empty:
                combined = pd.concat([fresh, combined])
                combined = combined[~combined.index.duplicated(keep="last")].sort_index()
        except Exception as e:
            logger.warning("Backfill failed for %s, using what we have: %s", symbol, e)

    save_cached(market, symbol, combined)
    return combined


def get_many_bars(
    provider: DataProvider,
    market: str,
    symbols: list[str],
    lookback_days: int,
    batch_size: int = 50,
) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Bulk version: uses the provider's batch call for symbols with no
    cache yet, and per-symbol incremental pulls for symbols already cached.
    Returns (bars_by_symbol, failed_symbols).

    Saves after each `batch_size` chunk (not after the whole uncached list
    finishes) specifically so Ctrl+C / a crash / a network drop mid-run
    only costs you the in-flight chunk, not the entire run — on restart,
    everything already written to Postgres is picked up as 'already
    cached' and skipped.
    """
    uncached = [s for s in symbols if load_cached(market, s) is None]
    cached_syms = [s for s in symbols if s not in uncached]

    out: dict[str, pd.DataFrame] = {}
    failed: list[str] = []

    for i in range(0, len(uncached), batch_size):
        chunk = uncached[i : i + batch_size]
        try:
            fresh_batch = provider.get_many_daily_bars(chunk, lookback_days)
        except Exception as e:
            logger.warning("Batch pull failed for chunk starting at %s: %s", chunk[0], e)
            fresh_batch = {}
        for sym in chunk:
            df = fresh_batch.get(sym)
            if df is not None and not df.empty:
                save_cached(market, sym, df)  # persisted immediately
                out[sym] = df
            else:
                failed.append(sym)
        if uncached:
            logger.info(
                "Pulled %d/%d new symbols so far (checkpointed to Postgres)",
                min(i + batch_size, len(uncached)), len(uncached),
            )

    for sym in cached_syms:
        df = get_bars(provider, market, sym, lookback_days)
        if df is not None and not df.empty:
            out[sym] = df
        else:
            failed.append(sym)

    return out, failed
