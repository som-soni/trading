"""Shared, strategy-agnostic market structure for one symbol.

Everything here is a plain fact about the chart — enriched OHLCV across
timeframes, swing structure, overhead supply — not an opinion about
whether it's tradeable. Strategies read this; they don't each rebuild it.
Keeping it shared is what makes running several strategies over the same
universe cheap: the context is built once per symbol per day.
"""

from dataclasses import dataclass, field

import pandas as pd

from . import indicators as ind
from . import swings as sw

MIN_CONTEXT_BARS = 60


@dataclass
class StockContext:
    symbol: str
    daily: pd.DataFrame  # enriched (indicators.enrich_daily)
    weekly: pd.DataFrame  # enriched (indicators.enrich_weekly)
    monthly: pd.DataFrame  # enriched (indicators.enrich_monthly)
    h_value: float  # highest high of the last 20 daily bars
    h_index: pd.Timestamp
    l_value: float  # lowest low in the 40 bars before H
    p_value: float  # lowest low after H
    prior_swing_low: float | None
    overhead: list[float]
    history_months: float
    earnings_days_away: int | None = None
    # strategies may stash their own derived values here rather than
    # widening this dataclass for every new strategy
    extras: dict = field(default_factory=dict)

    @property
    def last(self) -> pd.Series:
        return self.daily.iloc[-1]

    @property
    def close(self) -> float:
        return float(self.last["close"])

    @property
    def atr(self) -> float:
        return float(self.daily["atr14"].iloc[-1])


def build_context(
    symbol: str,
    daily_raw: pd.DataFrame,
    earnings_days_away: int | None = None,
) -> StockContext | None:
    """Build a StockContext from raw daily OHLCV. Returns None if there
    isn't enough history to compute the core structure (see DATA RULE)."""
    if daily_raw is None or len(daily_raw) < MIN_CONTEXT_BARS:
        return None

    daily = ind.enrich_daily(daily_raw)
    weekly = ind.enrich_weekly(ind.resample_weekly(daily_raw))
    monthly = ind.enrich_monthly(ind.resample_monthly(daily_raw))

    h_value, h_index = sw.current_swing_high(daily)
    l_value = sw.impulse_low(daily, h_index)
    p_value = sw.pullback_low(daily, h_index)
    prior_low = sw.prior_structural_swing_low(daily, h_index)
    overhead = sw.overhead_levels(daily, weekly, monthly, h_value)

    return StockContext(
        symbol=symbol,
        daily=daily,
        weekly=weekly,
        monthly=monthly,
        h_value=h_value,
        h_index=h_index,
        l_value=l_value,
        p_value=p_value,
        prior_swing_low=prior_low,
        overhead=overhead,
        history_months=len(monthly),
        earnings_days_away=earnings_days_away,
    )
