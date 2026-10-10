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


@dataclass
class SymbolFrames:
    """Everything build_context would otherwise re-derive on every bar.

    A backtest calls build_context once per qualifying bar on a GROWING slice of
    the same history, so the daily/weekly/monthly enrichment is recomputed from
    scratch each time -- quadratic in bars, and ~89% of a scan's runtime.

    Indicators are causal (indicators.py has no centered window, no negative
    shift, no backfill), so enriching the full history once and slicing it at a
    date gives the same row as enriching the truncated frame. Swing structure is
    NOT sliceable the same way -- swings.py uses center=True, so a precomputed
    swing mask would confirm a swing using bars that had not happened yet -- and
    stays per bar.

    The resampled frames are not simply sliceable either. `resample` labels each
    period by its END (W-FRI, ME), so slicing at a mid-week date silently drops
    the current partial week, while a truncated frame would include it. Complete
    periods therefore come from the precomputed resample and the final partial
    period is rebuilt from the daily bars inside it.
    """

    raw: pd.DataFrame
    daily: pd.DataFrame           # enriched, full history
    weekly_raw: pd.DataFrame      # resampled OHLCV, full history, unenriched
    monthly_raw: pd.DataFrame
    month_count: pd.Series        # distinct months up to each daily bar -> history_months


_AGG_COLS = ("open", "high", "low", "close", "volume")


def prepare_frames(daily_raw: pd.DataFrame) -> SymbolFrames:
    """Do once per symbol what build_context would otherwise do per bar."""
    months = pd.Series(daily_raw.index.to_period("M"), index=daily_raw.index)
    return SymbolFrames(
        raw=daily_raw,
        daily=ind.enrich_daily(daily_raw),
        weekly_raw=ind.resample_weekly(daily_raw),
        monthly_raw=ind.resample_monthly(daily_raw),
        month_count=(~months.duplicated()).cumsum(),
    )


def _periods_as_of(raw: pd.DataFrame, period_raw: pd.DataFrame, as_of) -> pd.DataFrame:
    """Complete periods before `as_of`'s period, plus that period rebuilt from
    the daily bars up to `as_of` -- what resampling the truncated frame gives."""
    idx = period_raw.index
    pos = int(idx.searchsorted(as_of, side="left"))   # first label >= as_of is as_of's own period
    if pos >= len(idx):
        return period_raw
    complete = period_raw.iloc[:pos]
    lo = int(raw.index.searchsorted(idx[pos - 1], side="right")) if pos else 0
    hi = int(raw.index.searchsorted(as_of, side="right"))
    tail = raw.iloc[lo:hi]
    if tail.empty:
        return complete
    part = pd.DataFrame(
        {"open": [tail["open"].iloc[0]], "high": [tail["high"].max()],
         "low": [tail["low"].min()], "close": [tail["close"].iloc[-1]],
         "volume": [tail["volume"].sum()]},
        index=[idx[pos]],
    )[list(_AGG_COLS)]
    return complete if part["close"].isna().all() else pd.concat([complete, part])


def build_context(
    symbol: str,
    daily_raw: pd.DataFrame,
    earnings_days_away: int | None = None,
    frames: "SymbolFrames | None" = None,
    as_of=None,
) -> StockContext | None:
    """Build a StockContext from raw daily OHLCV. Returns None if there
    isn't enough history to compute the core structure (see DATA RULE).

    `frames` + `as_of` take the same context from a per-symbol SymbolFrames
    instead of re-deriving it; the result is identical (tests/test_context_frames.py)."""
    if frames is not None and as_of is not None:
        hi = int(frames.raw.index.searchsorted(as_of, side="right"))
        if hi < MIN_CONTEXT_BARS:
            return None
        daily = frames.daily.iloc[:hi]
        weekly = ind.enrich_weekly(_periods_as_of(frames.raw, frames.weekly_raw, as_of))
        monthly = ind.enrich_monthly(_periods_as_of(frames.raw, frames.monthly_raw, as_of))
        return _assemble(symbol, daily, weekly, monthly,
                         int(frames.month_count.iloc[hi - 1]), earnings_days_away)

    if daily_raw is None or len(daily_raw) < MIN_CONTEXT_BARS:
        return None

    daily = ind.enrich_daily(daily_raw)
    weekly = ind.enrich_weekly(ind.resample_weekly(daily_raw))
    monthly = ind.enrich_monthly(ind.resample_monthly(daily_raw))

    return _assemble(symbol, daily, weekly, monthly, len(monthly), earnings_days_away)


def _assemble(symbol, daily, weekly, monthly, history_months, earnings_days_away):
    """The swing structure and overhead supply, shared by both paths above."""
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
        history_months=history_months,
        earnings_days_away=earnings_days_away,
    )
