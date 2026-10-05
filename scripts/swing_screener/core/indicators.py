"""Core indicator math. Every formula here is a direct transcription of the
DEFINITIONS section in the prompts — Wilder smoothing for RSI/ATR/ADX,
exact bar-offsets for 'rising'/'falling', etc. Keep it that way: if a gate
or flag definition changes in the prompt, change it here, not by swapping
in a generic TA library default (library defaults often use a plain EMA or
a different smoothing constant and will silently disagree with the rules).
"""

import numpy as np
import pandas as pd


def sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n, min_periods=n).mean()


def ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False, min_periods=n).mean()


def wilder_smooth(series: pd.Series, n: int) -> pd.Series:
    """Wilder's smoothing: equivalent to an EMA with alpha = 1/n."""
    return series.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = wilder_smooth(gain, n)
    avg_loss = wilder_smooth(loss, n)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.where(avg_loss != 0, 100.0)


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    a = df["high"] - df["low"]
    b = (df["high"] - prev_close).abs()
    c = (df["low"] - prev_close).abs()
    return pd.concat([a, b, c], axis=1).max(axis=1)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    return wilder_smooth(true_range(df), n)


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """ADX14, Wilder smoothed (see DEFINITIONS)."""
    up_move = df["high"].diff()
    down_move = -df["low"].diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr = true_range(df)
    atr_n = wilder_smooth(tr, n)
    plus_di = 100 * wilder_smooth(pd.Series(plus_dm, index=df.index), n) / atr_n
    minus_di = 100 * wilder_smooth(pd.Series(minus_dm, index=df.index), n) / atr_n
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return wilder_smooth(dx.fillna(0), n)


def enrich_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Add every indicator column the gate/flag/entry logic needs to a raw
    daily OHLCV DataFrame. Non-mutating."""
    out = df.copy()
    out["sma20"] = sma(out["close"], 20)
    out["sma50"] = sma(out["close"], 50)
    out["sma100"] = sma(out["close"], 100)
    # Minervini's Trend Template reads the 150-day as well as the 50/200, and
    # needs the 52-week LOW (for the ">=30% off the low" test) alongside the
    # 52-week high that was already here.
    out["sma150"] = sma(out["close"], 150)
    out["sma200"] = sma(out["close"], 200)
    out["ema20"] = ema(out["close"], 20)
    out["rsi14"] = rsi(out["close"], 14)
    out["rsi_ma"] = sma(out["rsi14"], 14)  # DEFINITIONS: 14-period SMA of RSI14
    out["atr14"] = atr(out, 14)
    out["atr_pct"] = out["atr14"] / out["close"] * 100
    out["adx14"] = adx(out, 14)
    out["vol_sma50"] = sma(out["volume"], 50)
    out["dollar_vol_sma20"] = sma(out["close"] * out["volume"], 20)
    out["high_252"] = out["high"].rolling(252, min_periods=20).max()  # 52-week high
    out["low_252"] = out["low"].rolling(252, min_periods=20).min()  # 52-week low
    # "the 200-day has been rising for at least a month" -- compare against
    # itself 21 sessions ago rather than fitting a slope, which is what the
    # rule actually says and is cheaper
    out["sma200_21d_ago"] = out["sma200"].shift(21)
    # 12-1 momentum: the RS proxy. Skips the most recent ~21 sessions (the
    # short-term reversal month), matching the momentum baseline's ranking.
    out["mom_12_1"] = out["close"].shift(21) / out["close"].shift(252) - 1.0
    return out


def enrich_weekly(weekly: pd.DataFrame) -> pd.DataFrame:
    out = weekly.copy()
    out["sma20"] = sma(out["close"], 20)  # W2: weekly SMA20 vs SMA50
    out["sma50"] = sma(out["close"], 50)
    out["ema30"] = ema(out["close"], 30)  # W1: weekly close vs rising 30-week EMA
    return out


def enrich_monthly(monthly: pd.DataFrame) -> pd.DataFrame:
    out = monthly.copy()
    out["sma10"] = sma(out["close"], 10)  # M1: monthly close vs 10-month SMA
    return out


def resample_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """Week ending on the last trading day of the week (see DATA PULL)."""
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    return daily.resample("W-FRI").agg(agg).dropna(subset=["close"])


def resample_monthly(daily: pd.DataFrame) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    return daily.resample("ME").agg(agg).dropna(subset=["close"])


def is_rising(series: pd.Series, lag: int) -> bool:
    """'Rising': value above its value `lag` bars ago (see DEFINITIONS)."""
    if len(series) <= lag or pd.isna(series.iloc[-1]) or pd.isna(series.iloc[-1 - lag]):
        return False
    return bool(series.iloc[-1] > series.iloc[-1 - lag])


def is_falling(series: pd.Series, lag: int, pct_threshold: float) -> bool:
    """'Falling': value more than `pct_threshold`% below its value `lag`
    bars ago (see DEFINITIONS: SMA50 >1% / SMA200 >0.5%)."""
    if len(series) <= lag or pd.isna(series.iloc[-1]) or pd.isna(series.iloc[-1 - lag]):
        return False
    past = series.iloc[-1 - lag]
    if past == 0 or pd.isna(past):
        return False
    pct_change = (series.iloc[-1] - past) / past * 100
    return bool(pct_change < -pct_threshold)


def slope_state(series: pd.Series, lag: int, falling_pct: float) -> str:
    """Returns 'rising', 'falling', or 'flat' per DEFINITIONS."""
    if is_rising(series, lag):
        return "rising"
    if is_falling(series, lag, falling_pct):
        return "falling"
    return "flat"


def pct_distance(close: float, level: float) -> float:
    """(close / level - 1) * 100 — DEFINITIONS 'percent distance from an SMA'."""
    if level in (0, None) or pd.isna(level):
        return float("nan")
    return (close / level - 1) * 100


def atr_distance(close: float, level: float, atr_value: float) -> float:
    """'N ATR from an SMA' = (close - level) / ATR14."""
    if not atr_value or pd.isna(atr_value):
        return float("nan")
    return (close - level) / atr_value
