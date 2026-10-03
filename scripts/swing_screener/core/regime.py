"""STEP 1 — market regime, and the per-sector regime computed in STEP 2.
Both read straight off enriched daily/weekly bars for indices and sector
ETFs/indices — no screenshots, same as everything else in this pipeline.
"""

import logging
from dataclasses import dataclass

import pandas as pd

from . import indicators as ind

logger = logging.getLogger(__name__)


@dataclass
class IndexRegime:
    symbol: str
    close: float
    above_sma50: bool
    above_sma200: bool
    sma50_rising: bool
    weekly_above_rising_30w_ema: bool


@dataclass
class MarketRegime:
    indices: dict[str, IndexRegime]
    vix_value: float | None
    high_vol: bool
    breadth_above_sma20_pct: float
    breadth_above_sma50_pct: float
    downgrade_active: bool


def index_regime(symbol: str, daily_enriched: pd.DataFrame, weekly_enriched: pd.DataFrame) -> IndexRegime | None:
    if daily_enriched is None or daily_enriched.empty or len(daily_enriched) < 60:
        return None
    last = daily_enriched.iloc[-1]
    sma50_rising = ind.is_rising(daily_enriched["sma50"], 10)
    weekly_ok = False
    if weekly_enriched is not None and len(weekly_enriched) >= 31:
        w = weekly_enriched.iloc[-1]
        weekly_ok = bool(w["close"] > w["ema30"]) and ind.is_rising(weekly_enriched["ema30"], 1)
    return IndexRegime(
        symbol=symbol,
        close=float(last["close"]),
        above_sma50=bool(pd.notna(last["sma50"]) and last["close"] > last["sma50"]),
        above_sma200=bool(pd.notna(last["sma200"]) and last["close"] > last["sma200"]),
        sma50_rising=sma50_rising,
        weekly_above_rising_30w_ema=weekly_ok,
    )


def compute_market_regime(
    index_daily: dict[str, pd.DataFrame],
    index_weekly: dict[str, pd.DataFrame],
    vix_value: float | None,
    vol_threshold: float,
    universe_daily: dict[str, pd.DataFrame],
    downgrade_index_symbols: list[str],
) -> MarketRegime:
    regimes: dict[str, IndexRegime] = {}
    for sym, df in index_daily.items():
        r = index_regime(sym, df, index_weekly.get(sym))
        if r is not None:
            regimes[sym] = r
        else:
            logger.warning("Could not compute regime for index %s", sym)

    above20 = above50 = total = 0
    for df in universe_daily.values():
        if df is None or df.empty or len(df) < 50:
            continue
        last = df.iloc[-1]
        total += 1
        if pd.notna(last.get("sma20")) and last["close"] > last["sma20"]:
            above20 += 1
        if pd.notna(last.get("sma50")) and last["close"] > last["sma50"]:
            above50 += 1

    breadth20 = (above20 / total * 100) if total else float("nan")
    breadth50 = (above50 / total * 100) if total else float("nan")

    high_vol = vix_value is not None and vix_value > vol_threshold

    downgrade = all(
        sym in regimes and not regimes[sym].above_sma50 for sym in downgrade_index_symbols
    ) if downgrade_index_symbols else False

    return MarketRegime(
        indices=regimes,
        vix_value=vix_value,
        high_vol=high_vol,
        breadth_above_sma20_pct=breadth20,
        breadth_above_sma50_pct=breadth50,
        downgrade_active=downgrade,
    )


@dataclass
class SectorRegime:
    sector: str
    index_symbol: str
    close: float
    above_sma50: bool
    above_sma200: bool
    sma50_rising: bool
    return_3m_vs_benchmark: float | None


def compute_sector_regime(
    sector: str,
    sector_index_daily: pd.DataFrame | None,
    benchmark_daily: pd.DataFrame | None,
    index_symbol: str,
) -> SectorRegime | None:
    if sector_index_daily is None or sector_index_daily.empty or len(sector_index_daily) < 64:
        logger.warning("No usable data for sector index %s (%s)", index_symbol, sector)
        return None
    d = sector_index_daily
    last = d.iloc[-1]

    rs = None
    if benchmark_daily is not None and len(benchmark_daily) >= 64:
        sector_ret_3m = d["close"].iloc[-1] / d["close"].iloc[-64] - 1
        bench_ret_3m = benchmark_daily["close"].iloc[-1] / benchmark_daily["close"].iloc[-64] - 1
        rs = (sector_ret_3m - bench_ret_3m) * 100

    return SectorRegime(
        sector=sector,
        index_symbol=index_symbol,
        close=float(last["close"]),
        above_sma50=bool(pd.notna(last.get("sma50")) and last["close"] > last["sma50"]),
        above_sma200=bool(pd.notna(last.get("sma200")) and last["close"] > last["sma200"]),
        sma50_rising=ind.is_rising(d["sma50"], 10),
        return_3m_vs_benchmark=rs,
    )
