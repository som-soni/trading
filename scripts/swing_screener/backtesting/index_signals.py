"""Timing signals for index strategies — every one lagged to be actionable.

The single rule in this file: a signal's value on date *t* may only use
information from *t-1* or earlier, because it is acted on at *t*'s close.
Every function therefore ends in `.shift(1)`. It is the difference between
"the 200-day rule returns 9%" and a backtest that quietly sells on the
morning of a crash it has not seen yet.

For the monthly rules this is stricter than it sounds. Faber's 10-month
rule is evaluated on *month-end closes*, so the decision taken during
February can only use January's close — reindexing a month-end signal
forward without shifting lets February trade on its own month-end price.
"""

import numpy as np
import pandas as pd


def _lag(s: pd.Series) -> pd.Series:
    return s.shift(1)


def sma_overlay(px: pd.Series, months: int = 10) -> pd.Series:
    """Faber: invested while the month-end close is above its N-month SMA.

    Monthly rather than daily on purpose — the original rule trades roughly
    once a year, and `dma_cross` exists to measure what daily evaluation
    does to that.
    """
    m = px.resample("ME").last()
    sig = m > m.rolling(months, min_periods=months).mean()
    # shift on the MONTHLY series: a decision inside month k uses month k-1
    sig = sig.shift(1)
    return sig.reindex(px.index, method="ffill").fillna(False).astype(bool)


def dma_cross(px: pd.Series, window: int = 200) -> pd.Series:
    """Invested while price is above its own N-day moving average."""
    sig = px > px.rolling(window, min_periods=window).mean()
    return _lag(sig).fillna(False).astype(bool)


def golden_cross(px: pd.Series, fast: int = 50, slow: int = 200) -> pd.Series:
    f = px.rolling(fast, min_periods=fast).mean()
    s = px.rolling(slow, min_periods=slow).mean()
    return _lag(f > s).fillna(False).astype(bool)


def abs_momentum(px: pd.Series, lookback: int = 252, skip: int = 0) -> pd.Series:
    """Time-series momentum: invested while the trailing return is positive."""
    r = px.shift(skip) / px.shift(skip + lookback) - 1
    return _lag(r > 0).fillna(False).astype(bool)


def excess_momentum(px: pd.Series, cash_rate: pd.Series, lookback: int = 252) -> pd.Series:
    """Dual-momentum's absolute leg: equity return over the cash return.

    Beating zero is the wrong bar when T-bills pay 5%; this is the bar that
    an investor actually faces.
    """
    eq_r = px / px.shift(lookback) - 1
    # compound the realised daily cash rate over the same window
    cash_leg = (1 + cash_rate.fillna(0) / 252).rolling(lookback, min_periods=lookback).apply(
        np.prod, raw=True
    ) - 1
    return _lag(eq_r > cash_leg).fillna(False).astype(bool)


def rank_momentum(prices: dict[str, pd.Series], lookback: int = 252) -> pd.DataFrame:
    """Trailing total return per asset per date, lagged. For rotation."""
    frame = pd.DataFrame(prices)
    return (frame / frame.shift(lookback) - 1).shift(1)


def vol_target_weight(
    px: pd.Series, target: float, window: int = 63, cap: float = 1.0
) -> pd.Series:
    """Exposure that scales to a volatility target, never levering past `cap`.

    Capped deliberately: an uncapped vol target quietly becomes a leveraged
    strategy in calm markets, which is a different (and borrowing-cost
    dependent) question from the one being asked.
    """
    rv = px.pct_change().rolling(window, min_periods=window // 2).std() * np.sqrt(252)
    w = (target / rv).clip(upper=cap)
    return _lag(w).fillna(0.0).clip(0.0, cap)


def seasonal(index: pd.DatetimeIndex, months: tuple[int, ...]) -> pd.Series:
    """Invested only during the given calendar months ('sell in May')."""
    return pd.Series([d.month in months for d in index], index=index, dtype=bool)


def drawdown_from_peak(px: pd.Series) -> pd.Series:
    """Lagged drawdown from the running all-time high, as a positive fraction.

    Uses the running peak of the series available at the time — not the
    whole-sample maximum, which would be lookahead of the worst kind.
    """
    dd = 1.0 - px / px.cummax()
    return _lag(dd).fillna(0.0)
