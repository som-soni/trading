"""Shared by the review scripts: the run's own benchmark and its equity table's date column.

A strategy may declare its own benchmark (`benchmark_key`, e.g. momentum_vol_scaled measures itself against the
Smallcap 250 in India), and the runner reports against that. The scripts must judge against the same series,
or they test a different claim. Portfolio runners name the equity table's date column `Date`, the per-symbol
simulator `date`.
"""
import pandas as pd

from swing_screener.config import MARKETS


def date_index(df: pd.DataFrame) -> pd.DatetimeIndex:
    col = next((c for c in df.columns if str(c).lower() == "date"), df.columns[0])
    return pd.DatetimeIndex(pd.to_datetime(df[col]))


def bench_ticker(strategy: str | None, market: str, override: str | None = None) -> tuple[str, str]:
    """(ticker, name) of the benchmark the run itself reports against, as the runner resolves it
    (backtesting/baseline.py: a portfolio strategy's `benchmark_key`, else the market's benchmark)."""
    cfg = MARKETS[market]
    if override:
        return override, override
    try:
        from swing_screener.strategies import portfolio_strategies
        key = (getattr(portfolio_strategies().get(strategy or ""), "benchmark_key", None) or {}).get(market)
    except Exception:  # noqa: BLE001
        key = None
    tk = cfg.broad_index_symbols.get(key) if key else None
    if tk:
        from swing_screener.marketdata import cache
        if cache.load_cached(market, tk) is not None:
            return tk, key
    return cfg.benchmark_ticker, cfg.benchmark_symbol
