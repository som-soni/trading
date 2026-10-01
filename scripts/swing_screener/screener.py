"""The loosened screener filter, replicated directly against pulled bars —
this is what replaces Chartink/TradingView's screener UI. Applied AFTER
indicators are computed (cheap vectorized pandas) and BEFORE the heavier
swing-structure + gate/flag computation, so the expensive work only runs
on the much smaller filtered set (mirrors the funnel in the prompts).
"""

import pandas as pd

from .config.base import MarketConfig


def passes_loose_filter(cfg: MarketConfig, enriched_daily: pd.DataFrame) -> tuple[bool, str]:
    if enriched_daily is None or len(enriched_daily) < 210:
        return False, "insufficient history (<210 daily bars)"
    last = enriched_daily.iloc[-1]

    if cfg.screener.min_price and last["close"] < cfg.screener.min_price:
        return False, f"price {last['close']:.2f} < {cfg.screener.min_price}"

    if pd.isna(last["sma50"]) or pd.isna(last["sma200"]) or last["sma50"] <= last["sma200"]:
        return False, "SMA50 <= SMA200"

    if pd.isna(last["adx14"]) or last["adx14"] <= cfg.screener.adx_min:
        return False, f"ADX14 <= {cfg.screener.adx_min}"

    if pd.isna(last["atr_pct"]) or last["atr_pct"] <= cfg.screener.atr_pct_min:
        return False, f"ATR% <= {cfg.screener.atr_pct_min}"

    if cfg.screener.min_dollar_volume:
        dv = last.get("dollar_vol_sma20")
        if pd.isna(dv) or dv < cfg.screener.min_dollar_volume:
            return False, f"liquidity below {cfg.screener.min_dollar_volume:,.0f}"

    return True, "passed"


def passes_market_cap(min_cap_cr: float, market_cap_cr: float | None) -> bool:
    if market_cap_cr is None:
        return True  # unknown — don't silently exclude, flag upstream instead
    return market_cap_cr >= min_cap_cr
