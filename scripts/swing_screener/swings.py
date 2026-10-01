"""Swing-structure detection: swing highs/lows, H/L/P, overhead levels,
base-vs-drift. Direct transcription of DEFINITIONS in the prompts.
"""

import pandas as pd


def _swing_mask(series: pd.Series, left: int, right: int, how: str) -> pd.Series:
    window = left + right + 1
    roll = series.rolling(window, center=True, min_periods=window)
    extreme = roll.max() if how == "max" else roll.min()
    return series == extreme


def swing_high_mask(high: pd.Series, left: int = 3, right: int = 3) -> pd.Series:
    return _swing_mask(high, left, right, "max")


def swing_low_mask(low: pd.Series, left: int = 3, right: int = 3) -> pd.Series:
    return _swing_mask(low, left, right, "min")


def current_swing_high(daily: pd.DataFrame, window: int = 20) -> tuple[float, pd.Timestamp]:
    """H: highest high of the last `window` daily bars."""
    tail = daily["high"].iloc[-window:]
    idx = tail.idxmax()
    return float(tail.loc[idx]), idx


def impulse_low(daily: pd.DataFrame, h_index: pd.Timestamp, window: int = 40) -> float:
    """L: lowest low in the `window` bars before H."""
    pos = daily.index.get_loc(h_index)
    start = max(0, pos - window)
    segment = daily["low"].iloc[start:pos]
    return float(segment.min()) if len(segment) else float("nan")


def pullback_low(daily: pd.DataFrame, h_index: pd.Timestamp) -> float:
    """P: lowest low after H."""
    pos = daily.index.get_loc(h_index)
    segment = daily["low"].iloc[pos + 1 :]
    if segment.empty:
        return float(daily["low"].iloc[pos])
    return float(segment.min())

def prior_structural_swing_low(
    daily: pd.DataFrame, h_index: pd.Timestamp, left: int = 3, right: int = 3
) -> float | None:
    """The last confirmed daily swing low before H."""
    mask = swing_low_mask(daily["low"], left, right)
    pos = daily.index.get_loc(h_index)
    prior = mask.iloc[:pos]
    confirmed = prior[prior]
    if confirmed.empty:
        return None
    last_idx = confirmed.index[-1]
    return float(daily.loc[last_idx, "low"])


def overhead_levels(
    daily: pd.DataFrame,
    weekly: pd.DataFrame | None,
    monthly: pd.DataFrame | None,
    h_value: float,
) -> list[float]:
    """Every daily swing high in the last 252 bars, weekly swing high in the
    last 5 years, monthly swing high in all history, AND the current swing
    high H (see DEFINITIONS)."""
    levels: set[float] = {round(h_value, 4)}

    d_tail = daily.iloc[-252:]
    d_mask = swing_high_mask(d_tail["high"], 3, 3)
    levels.update(round(v, 4) for v in d_tail.loc[d_mask, "high"].tolist())

    if weekly is not None and not weekly.empty:
        w_tail = weekly.iloc[-260:]  # ~5 years
        w_mask = swing_high_mask(w_tail["high"], 3, 3)
        levels.update(round(v, 4) for v in w_tail.loc[w_mask, "high"].tolist())

    if monthly is not None and not monthly.empty:
        m_mask = swing_high_mask(monthly["high"], 2, 2)
        levels.update(round(v, 4) for v in monthly.loc[m_mask, "high"].tolist())

    return sorted(levels)


def levels_within_pct_above(close: float, levels: list[float], pct: float = 3.0) -> list[float]:
    """Overhead levels within `pct`% above close, excluding levels already
    broken (close already above them) — see D5."""
    lo, hi = close, close * (1 + pct / 100)
    return sorted(lvl for lvl in levels if lo < lvl <= hi)


def nearest_overhead_above(close: float, levels: list[float]) -> float | None:
    above = [lvl for lvl in levels if lvl > close]
    return min(above) if above else None


def base_or_drift(
    daily: pd.DataFrame, atr14: float, high_252: float, lookback: int = 10
) -> str:
    """Base = 10-bar range <= 4.5 ATR AND close within 10% of the 52-week
    high. Drift = anything else (see DEFINITIONS)."""
    tail = daily.iloc[-lookback:]
    bar_range = float(tail["high"].max() - tail["low"].min())
    close = float(daily["close"].iloc[-1])
    if atr14 in (0, None) or pd.isna(atr14) or high_252 in (0, None) or pd.isna(high_252):
        return "drift"
    range_ok = bar_range <= 4.5 * atr14
    near_high = close >= high_252 * 0.90
    return "base" if (range_ok and near_high) else "drift"


def higher_swing_lows(daily: pd.DataFrame, lookback: int = 50) -> bool:
    """T3: the last two confirmed daily swing lows within `lookback` bars
    are rising. Fewer than two: lowest low of the last 25 bars must be
    above the lowest low of the 25 bars before that."""
    tail = daily.iloc[-lookback:]
    mask = swing_low_mask(tail["low"], 3, 3)
    confirmed = tail.loc[mask, "low"]
    if len(confirmed) >= 2:
        last_two = confirmed.iloc[-2:]
        return bool(last_two.iloc[1] > last_two.iloc[0])
    recent_25 = daily["low"].iloc[-25:]
    prior_25 = daily["low"].iloc[-50:-25]
    if recent_25.empty or prior_25.empty:
        return False
    return bool(recent_25.min() > prior_25.min())


def pullback_on_rising_volume(daily: pd.DataFrame, h_index: pd.Timestamp, l_value: float) -> bool:
    """D3: average volume of the bars after H is higher than the average
    volume of the impulse bars from L to H."""
    pos = daily.index.get_loc(h_index)
    after_h = daily["volume"].iloc[pos + 1 :]
    if after_h.empty:
        return False
    # find L's index: lowest low in the 40 bars before H
    start = max(0, pos - 40)
    segment = daily.iloc[start:pos]
    if segment.empty:
        return False
    l_pos_label = segment["low"].idxmin()
    l_pos = daily.index.get_loc(l_pos_label)
    impulse = daily["volume"].iloc[l_pos : pos + 1]
    if impulse.empty:
        return False
    return bool(after_h.mean() > impulse.mean())


def gap_not_held(daily: pd.DataFrame, lookback: int = 10, gap_pct: float = 8.0) -> bool:
    """D7: a gap of more than `gap_pct`% in the last `lookback` bars that
    has not held (see DEFINITIONS)."""
    tail = daily.iloc[-(lookback + 1) :]
    if len(tail) < 2:
        return False
    current_close = float(daily["close"].iloc[-1])
    opens = tail["open"].values
    prev_closes = tail["close"].shift(1).values
    for i in range(1, len(tail)):
        prev_close = prev_closes[i]
        if prev_close == 0 or pd.isna(prev_close):
            continue
        gap = (opens[i] - prev_close) / prev_close * 100
        if gap > gap_pct and current_close < prev_close:
            return True
        if gap < -gap_pct and current_close < prev_close:
            return True
    return False
