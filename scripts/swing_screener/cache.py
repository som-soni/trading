"""Local parquet cache so a daily run only pulls NEW bars, not the full
lookback window every time (see DATA PULL in the prompts: 'pull with at
most 4 requests in parallel... keep all pulled data for the rest of the
run' — the cache is what makes that cheap across runs, not just within one)."""

import logging
from pathlib import Path

import pandas as pd

from .providers.base import DataProvider

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"


def _cache_path(cache_dir: Path, market: str, symbol: str) -> Path:
    safe = symbol.replace("/", "_").replace("^", "idx_")
    return cache_dir / market / f"{safe}.parquet"


def load_cached(cache_dir: Path, market: str, symbol: str) -> pd.DataFrame | None:
    path = _cache_path(cache_dir, market, symbol)
    if not path.exists():
        return None
    try:
        return pd.read_parquet(path)
    except Exception:
        logger.warning("Corrupt cache for %s, discarding: %s", symbol, path)
        return None


def save_cached(cache_dir: Path, market: str, symbol: str, df: pd.DataFrame) -> None:
    path = _cache_path(cache_dir, market, symbol)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)


def get_bars(
    provider: DataProvider,
    cache_dir: Path,
    market: str,
    symbol: str,
    lookback_days: int,
) -> pd.DataFrame | None:
    """Return at least `lookback_days` of daily bars for `symbol`, pulling
    only the incremental tail from `provider` if a cache already covers
    most of the history. Returns None if the symbol could not be loaded at
    all (caller should list it under 'Not reviewed')."""
    cached = load_cached(cache_dir, market, symbol)

    if cached is None or cached.empty:
        try:
            fresh = provider.get_daily_bars(symbol, lookback_days)
        except Exception as e:
            logger.warning("Failed to fetch %s: %s", symbol, e)
            return None
        if fresh is None or fresh.empty:
            return None
        save_cached(cache_dir, market, symbol, fresh)
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

    save_cached(cache_dir, market, symbol, combined)
    return combined


def get_many_bars(
    provider: DataProvider,
    cache_dir: Path,
    market: str,
    symbols: list[str],
    lookback_days: int,
    batch_size: int = 50,
) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Bulk version: uses the provider's batch call for symbols with no
    cache yet, and per-symbol incremental pulls for symbols already cached.
    Returns (bars_by_symbol, failed_symbols).

    Saves to disk after each `batch_size` chunk (not after the whole
    uncached list finishes) specifically so Ctrl+C / a crash / a network
    drop mid-run only costs you the in-flight chunk, not the entire run —
    on restart, everything already written to cache/ is picked up as
    'already cached' and skipped.
    """
    uncached = [
        s for s in symbols if load_cached(cache_dir, market, s) is None
    ]
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
                save_cached(cache_dir, market, sym, df)  # persisted immediately
                out[sym] = df
            else:
                failed.append(sym)
        if uncached:
            logger.info(
                "Pulled %d/%d new symbols so far (checkpointed to cache)",
                min(i + batch_size, len(uncached)), len(uncached),
            )

    for sym in cached_syms:
        df = get_bars(provider, cache_dir, market, sym, lookback_days)
        if df is not None and not df.empty:
            out[sym] = df
        else:
            failed.append(sym)

    return out, failed
