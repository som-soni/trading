"""CANDLESTICK COMMENTARY. Thresholds for doji/hammer/shooting-star/NR7
come straight from the prompt. A few things the prompt names but doesn't
pin to an exact number — 'any gap', '3-bar reversal' — are implemented
here as reasonable, clearly-commented heuristics; tighten them if your
own read of the charts disagrees.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass
class BarStats:
    date: pd.Timestamp
    body_pct: float
    close_loc: str  # "top" / "middle" / "bottom"
    upper_wick_ratio: float
    lower_wick_ratio: float
    gap_pct: float
    vol_ratio: float  # vs 50-day average
    patterns: list[str]


def _bar_stats(daily: pd.DataFrame, pos: int) -> BarStats:
    row = daily.iloc[pos]
    o, h, l, c = row["open"], row["high"], row["low"], row["close"]
    rng = h - l
    body = abs(c - o)
    body_pct = (body / rng * 100) if rng > 0 else 0.0

    if rng > 0:
        close_frac = (c - l) / rng
    else:
        close_frac = 0.5
    close_loc = "top" if close_frac >= 0.66 else ("bottom" if close_frac <= 0.34 else "middle")

    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    upper_wick_ratio = (upper_wick / body) if body > 0 else float("inf") if upper_wick > 0 else 0.0
    lower_wick_ratio = (lower_wick / body) if body > 0 else float("inf") if lower_wick > 0 else 0.0

    prev_close = daily["close"].iloc[pos - 1] if pos > 0 else float("nan")
    gap_pct = (o - prev_close) / prev_close * 100 if pos > 0 and prev_close else 0.0

    vol_sma50 = daily["vol_sma50"].iloc[pos] if "vol_sma50" in daily.columns else float("nan")
    vol_ratio = row["volume"] / vol_sma50 if pd.notna(vol_sma50) and vol_sma50 else float("nan")

    patterns: list[str] = []
    if body_pct <= 10:
        patterns.append("doji")
    if lower_wick_ratio >= 2 and close_loc == "top":
        patterns.append("hammer")
    if upper_wick_ratio >= 2 and close_loc == "bottom":
        patterns.append("shooting star")

    if pos > 0:
        prev = daily.iloc[pos - 1]
        po, ph, pl, pc = prev["open"], prev["high"], prev["low"], prev["close"]
        bullish_cur = c > o
        bearish_prev = pc < po
        if bullish_cur and bearish_prev and o <= pc and c >= po:
            patterns.append("bullish engulfing")
        bearish_cur = c < o
        bullish_prev = pc > po
        if bearish_cur and bullish_prev and o >= pc and c <= po:
            patterns.append("bearish engulfing")
        if h <= ph and l >= pl:
            patterns.append("inside bar")
        if h >= ph and l <= pl:
            patterns.append("outside bar")

    if pos >= 6:
        last7_ranges = (daily["high"] - daily["low"]).iloc[pos - 6 : pos + 1]
        if rng > 0 and rng == last7_ranges.min():
            patterns.append("NR7")

    if pos >= 2:
        c0, c1, c2 = daily["close"].iloc[pos - 2], daily["close"].iloc[pos - 1], c
        o0 = daily["open"].iloc[pos - 2]
        if c1 < c0 and c2 > c1 and c2 > o0:
            patterns.append("3-bar reversal (bullish)")
        if c1 > c0 and c2 < c1 and c2 < o0:
            patterns.append("3-bar reversal (bearish)")

    if gap_pct > 0.3:
        patterns.append("gap up")
    elif gap_pct < -0.3:
        patterns.append("gap down")

    return BarStats(
        date=daily.index[pos],
        body_pct=round(body_pct, 1),
        close_loc=close_loc,
        upper_wick_ratio=round(upper_wick_ratio, 2) if upper_wick_ratio != float("inf") else float("inf"),
        lower_wick_ratio=round(lower_wick_ratio, 2) if lower_wick_ratio != float("inf") else float("inf"),
        gap_pct=round(gap_pct, 2),
        vol_ratio=round(vol_ratio, 2) if pd.notna(vol_ratio) else float("nan"),
        patterns=patterns,
    )


def last_n_bar_stats(daily: pd.DataFrame, n: int = 5) -> list[BarStats]:
    start = max(0, len(daily) - n)
    return [_bar_stats(daily, pos) for pos in range(start, len(daily))]


def weekly_candle_note(weekly: pd.DataFrame) -> str:
    if len(weekly) < 2:
        return "weekly: insufficient history"
    stats = _bar_stats(weekly, len(weekly) - 1)
    bits = []
    if stats.patterns:
        bits.append("/".join(stats.patterns))
    bits.append(f"close {stats.close_loc} of range")
    return "weekly: " + ", ".join(bits)


def summarize(
    daily: pd.DataFrame,
    sma20: float,
    sma50: float,
    h_value: float,
    n: int = 5,
) -> str:
    """<=25-word summary of the last n bars, in context of support/SMA/H."""
    bars = last_n_bar_stats(daily, n)
    last = bars[-1]
    close = daily["close"].iloc[-1]

    context = []
    if sma20 == sma20 and abs(close - sma20) / sma20 < 0.02:
        context.append("at SMA20")
    if sma50 == sma50 and abs(close - sma50) / sma50 < 0.02:
        context.append("at SMA50")
    if h_value and abs(close - h_value) / h_value < 0.02:
        context.append("under H")

    vol_note = ""
    if last.vol_ratio == last.vol_ratio:  # not NaN
        vol_note = "above avg volume" if last.vol_ratio > 1.2 else (
            "below avg volume" if last.vol_ratio < 0.8 else ""
        )

    parts = []
    if last.patterns:
        parts.append("/".join(last.patterns))
    else:
        parts.append(f"plain {last.close_loc}-range close")
    if context:
        parts.append(", ".join(context))
    if vol_note:
        parts.append(vol_note)

    return "; ".join(parts)
