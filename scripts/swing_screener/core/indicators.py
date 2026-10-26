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


RS_SCORE_WINDOWS = (63, 126, 189, 252)   # trailing 3 / 6 / 9 / 12 months, in sessions
RS_SCORE_RECENT_WEIGHT = 2               # the most recent quarter counts twice


def rs_score(close):
    """The IBD-style weighted relative-strength score: trailing 3/6/9/12-month returns with the
    most recent quarter counted twice.

    THE one definition of this quantity. `backtesting/spec.rs_ratings` ranks it across a market
    to produce the 1-99 RS rating, `screens/snapshot` stores it per stock, and `enrich_daily`
    exposes it as `rs_score` so a single symbol can be screened on the same number without a
    market to rank against.

    Note the four windows OVERLAP -- each contains the most recent quarter -- so in terms of
    non-overlapping quarterly returns the weights are 5/3/2/1, i.e. 45% on the most recent
    quarter and 9% on the oldest, not the 40/20/20/20 the arithmetic looks like.

    `close` may be a Series (one symbol) or a DataFrame of closes by symbol; the result has the
    same shape.
    """
    r = lambda k: close / close.shift(k) - 1.0
    w = RS_SCORE_RECENT_WEIGHT
    q1, q2, q3, q4 = (r(k) for k in RS_SCORE_WINDOWS)
    return w * q1 + q2 + q3 + q4


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
    # 12-1 momentum: skips the most recent ~21 sessions (the short-term
    # reversal month), matching the momentum baseline's ranking. It is the
    # ranking factor for the momentum strategies -- NOT the Trend Template's
    # RS stand-in, which wants the opposite emphasis; see `rs_score`.
    out["mom_12_1"] = out["close"].shift(21) / out["close"].shift(252) - 1.0
    out["rs_score"] = rs_score(out["close"])
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


class SupertrendState:
    """Supertrend(ATR period, multiplier), one bar at a time.

    THE Python definition, transcribed from the chart's Supertrend study (web/static/studies.js,
    `st`) so the two draw the same line: the ATR is an RMA of the true range seeded with the
    simple average of its first `period` values (not `wilder_smooth`, which seeds from the first
    value); the basic bands are (high + low) / 2 ± multiplier × ATR; the final upper band only
    falls and the final lower band only rises, unless the previous close crossed them; the trend
    starts up, turns up on a close above the previous final upper band and down on a close below
    the previous final lower band. The line is the final lower band in an up-trend and the final
    upper band in a down-trend.

    Stepping (rather than a function of a whole frame) is what lets a backtest that sees a growing
    slice of one history extend it bar by bar instead of recomputing it -- every value depends
    only on bars up to its own, so the extension equals a recomputation."""

    __slots__ = ("period", "mult", "_seed", "_atr", "_prev_close", "upper", "lower", "dir")

    def __init__(self, period: int, mult: float):
        self.period, self.mult = int(period), float(mult)
        self._seed: list[float] = []
        self._atr = None
        self._prev_close = None
        self.upper = self.lower = None
        self.dir = 1

    def step(self, high: float, low: float, close: float) -> tuple[float, int, float, float]:
        """Feed one bar; return (line, direction, final upper, final lower), NaN/0 until the ATR exists."""
        pc = self._prev_close
        tr = high - low if pc is None else max(high - low, abs(high - pc), abs(low - pc))
        if self._atr is None:
            self._seed.append(tr)
            if len(self._seed) == self.period:
                self._atr = sum(self._seed) / self.period
        else:
            self._atr += (tr - self._atr) / self.period
        if self._atr is None:
            self._prev_close = close
            return float("nan"), 0, float("nan"), float("nan")
        hl2 = (high + low) / 2
        bu, bl = hl2 + self.mult * self._atr, hl2 - self.mult * self._atr
        pu, pl = self.upper, self.lower
        self.upper = bu if pu is None or bu < pu or pc > pu else pu
        self.lower = bl if pl is None or bl > pl or pc < pl else pl
        if pu is not None:
            self.dir = (1 if close > pu else -1) if self.dir == -1 else (-1 if close < pl else 1)
        self._prev_close = close
        return (self.lower if self.dir == 1 else self.upper), self.dir, self.upper, self.lower


def supertrend(df: pd.DataFrame, period: int, mult: float) -> pd.DataFrame:
    """`SupertrendState` over a whole daily frame: columns line, dir (1 up, -1 down, 0 before the
    ATR exists), upper, lower."""
    st = SupertrendState(period, mult)
    rows = [st.step(h, l, c) for h, l, c in zip(df["high"].to_numpy(float), df["low"].to_numpy(float),
                                                 df["close"].to_numpy(float))]
    return pd.DataFrame(rows, index=df.index, columns=["line", "dir", "upper", "lower"])
