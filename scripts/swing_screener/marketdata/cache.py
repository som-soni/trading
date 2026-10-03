"""Postgres-backed price cache so a daily run only pulls NEW bars, not the
full lookback window every time (see DATA PULL in the prompts: 'pull with
at most 4 requests in parallel... keep all pulled data for the rest of the
run'). Indicators are precomputed and stored alongside raw OHLCV on every
save — they're purely backward-looking (no lookahead), so computing them
once here instead of re-deriving them from scratch in every caller (and
every backtest day) is free correctness-wise and saves real time.
"""

import logging
import time

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

    changed = new_rows is not None and not new_rows.empty
    if changed:
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
                changed = True
        except Exception as e:
            logger.warning("Backfill failed for %s, using what we have: %s", symbol, e)

    # Only write when something actually arrived. Re-saving an unchanged frame
    # upserts the symbol's whole history back into Postgres — across a 5,400
    # name universe that is ~14.6M redundant row writes on every daily run,
    # and it was the bulk of the runtime.
    if changed:
        save_cached(market, symbol, combined)
    return combined


def cached_symbols(market: str) -> set[str]:
    """Which symbols have ANY cached history, as one query.

    Testing existence with `load_cached(...) is None` pulls every symbol's
    full price history out of Postgres into a DataFrame just to throw it
    away — ~14.6M rows for the US universe, and then `get_bars` loads each
    one again. This asks the question directly."""
    conn = db.get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT symbol FROM prices WHERE market=%s", (market,))
        return {r[0] for r in cur.fetchall()}


def last_cached_dates(market: str) -> dict[str, pd.Timestamp]:
    """symbol -> most recent cached bar date, as ONE query.

    Asking this per symbol (by loading the frame and taking `index[-1]`)
    costs a full-history read per symbol; the whole universe answers in one
    grouped query instead."""
    conn = db.get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT symbol, MAX(date) FROM prices WHERE market=%s GROUP BY symbol",
            (market,),
        )
        return {sym: pd.Timestamp(d) for sym, d in cur.fetchall()}


def load_many_cached(
    market: str, symbols: list[str], since: "pd.Timestamp | None" = None
) -> dict[str, pd.DataFrame]:
    """Raw OHLCV for many symbols in ONE query instead of one per symbol.

    5,400 individual round trips dominated the daily run; this issues a
    single statement and splits the result locally. `since` bounds the read
    to the history the caller actually needs."""
    if not symbols:
        return {}
    conn = db.get_connection()
    sql = (
        "SELECT symbol, date, open, high, low, close, volume FROM prices "
        "WHERE market=%s AND symbol = ANY(%s)"
    )
    params: list = [market, list(symbols)]
    if since is not None:
        sql += " AND date >= %s"
        params.append(since.date())
    sql += " ORDER BY symbol, date"
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    if not rows:
        return {}
    df = pd.DataFrame(
        rows, columns=["symbol", "Date", "open", "high", "low", "close", "volume"]
    )
    df["Date"] = pd.to_datetime(df["Date"])
    out: dict[str, pd.DataFrame] = {}
    for sym, g in df.groupby("symbol", sort=False):
        out[sym] = g.drop(columns="symbol").set_index("Date")
    return out


def get_many_bars(
    provider: DataProvider,
    market: str,
    symbols: list[str],
    lookback_days: int,
    batch_size: int = 50,
    chunk_size: int = 400,
) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Bring `symbols` up to date and return their bars.

    Three things made the naive version slow enough to look hung on a
    5,400-name universe, all fixed here:

      * existence was tested by loading every symbol's full history and
        discarding it -> one grouped query instead;
      * the incremental tail was fetched with one HTTP request PER SYMBOL
        -> batched through the provider's bulk call, ~50 symbols a request;
      * every symbol was re-saved even when nothing new arrived, upserting
        its whole history back into Postgres -> only changed frames write.

    Stale symbols are processed in chunks: each chunk does one bulk read of
    full history, one batched network fetch, then merges and saves. Full
    history is needed (not just the tail) because `save_cached` recomputes
    indicators, and SMA200 on a 400-bar tail would be wrong.
    """
    t_start = time.time()
    out: dict[str, pd.DataFrame] = {}
    failed: list[str] = []

    last_dates = last_cached_dates(market)
    uncached = [s for s in symbols if s not in last_dates]
    cached_syms = [s for s in symbols if s in last_dates]
    market_latest = max(last_dates.values()) if last_dates else None
    stale = [s for s in cached_syms if market_latest and last_dates[s] < market_latest]
    fresh = [s for s in cached_syms if s not in set(stale)]
    logger.info(
        "%s: %d symbols — %d up to date, %d need a tail fetch, %d not cached at all",
        market, len(symbols), len(fresh), len(stale), len(uncached),
    )

    # ---- symbols with no cache at all: batched full pull ----
    for i in range(0, len(uncached), batch_size):
        chunk = uncached[i : i + batch_size]
        try:
            got = provider.get_many_daily_bars(chunk, lookback_days)
        except Exception as e:
            logger.warning("Batch pull failed at %s: %s", chunk[0], e)
            got = {}
        for sym in chunk:
            df = got.get(sym)
            if df is not None and not df.empty:
                save_cached(market, sym, df)
                out[sym] = df
            else:
                failed.append(sym)
        logger.info(
            "  new symbols: %d/%d fetched", min(i + batch_size, len(uncached)), len(uncached)
        )

    # ---- stale symbols: bulk read + batched fetch, chunk by chunk ----
    updated = 0
    for ci in range(0, len(stale), chunk_size):
        chunk = stale[ci : ci + chunk_size]
        existing = load_many_cached(market, chunk)          # one query
        fetched: dict[str, pd.DataFrame] = {}
        for i in range(0, len(chunk), batch_size):
            sub = chunk[i : i + batch_size]
            try:
                fetched.update(provider.get_many_daily_bars(sub, lookback_days))
            except Exception as e:
                logger.warning("  tail fetch failed at %s: %s", sub[0], e)
        for sym in chunk:
            cached = existing.get(sym)
            new_rows = fetched.get(sym)
            if cached is None or cached.empty:
                if new_rows is not None and not new_rows.empty:
                    save_cached(market, sym, new_rows)
                    out[sym] = new_rows
                    updated += 1
                else:
                    failed.append(sym)
                continue
            if new_rows is None or new_rows.empty:
                out[sym] = cached           # nothing new; do NOT rewrite it
                continue
            combined = pd.concat([cached, new_rows])
            combined = combined[~combined.index.duplicated(keep="last")].sort_index()
            if len(combined) > len(cached):
                save_cached(market, sym, combined)
                updated += 1
            out[sym] = combined
        done = min(ci + chunk_size, len(stale))
        rate = done / max(time.time() - t_start, 1e-9)
        logger.info(
            "  refreshed %d/%d stale symbols (%d written, %.0f/s, ETA %.0f min)",
            done, len(stale), updated, rate, (len(stale) - done) / max(rate, 1e-9) / 60,
        )

    # ---- already up to date: one bulk read, no network at all ----
    if fresh:
        logger.info("  bulk-loading %d up-to-date symbols...", len(fresh))
        loaded = load_many_cached(market, fresh)
        out.update(loaded)
        failed.extend([s for s in fresh if s not in loaded])
        logger.info("  loaded %d/%d", len(loaded), len(fresh))

    logger.info(
        "%s: %d symbols ready, %d failed, in %.1f min",
        market, len(out), len(failed), (time.time() - t_start) / 60,
    )
    return out, failed

