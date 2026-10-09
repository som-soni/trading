"""Qualification criteria shared by the screens and the strategies that draw from them.

Each criterion takes a `StockContext` (core/context.py) and returns (passed, note). The code here was
moved verbatim out of the strategies' gate code, so a strategy that qualifies stocks through a screen
evaluates exactly as it did before (tests/golden_strategies.py proves it).
"""

import pandas as pd

from ..core import indicators as ind
from ..core import swings as sw

# ---- Stage 2 (Minervini's Trend Template) — thresholds
SMA200_RISING_BARS = 21          # the 200-day must be higher than this many sessions ago
MIN_PCT_ABOVE_52W_LOW = 30.0
MAX_PCT_BELOW_52W_HIGH = 25.0
RS_MIN_MOM = 0.10                # per-stock stand-in for an RS rank of 70+: 12-1 month momentum
RS_MIN_RANK = 70                 # when a whole market is screened at once: the true 1-99 RS rank

# ---- near highs
NEAR_HIGH_MIN_FRAC = 0.85        # close at least this fraction of the 52-week high (within 15%)
SMA200_FALLING_PCT = 0.5         # "falling": more than this % below its value SMA200_SLOPE_BARS ago
SMA200_SLOPE_BARS = 20


# ------------------------------------------------------------------ long-term trend (200-day)

def above_sma200(ctx) -> tuple[bool, str]:
    sma200 = ctx.daily["sma200"].iloc[-1]
    if pd.isna(sma200) or ctx.close <= sma200:
        return False, "close at/below SMA200"
    return True, ""


def sma200_not_falling(ctx) -> tuple[bool, str]:
    state = ind.slope_state(ctx.daily["sma200"], SMA200_SLOPE_BARS, SMA200_FALLING_PCT)
    if state == "falling":
        return False, "SMA200 falling"
    return True, f"SMA200 {state}"


def near_52w_high(ctx, min_frac: float = NEAR_HIGH_MIN_FRAC) -> tuple[bool, str]:
    high_252 = ctx.daily["high_252"].iloc[-1]
    if pd.isna(high_252):
        return False, "insufficient history for the 52-week high"
    if ctx.close >= high_252 * min_frac:
        return True, ""
    return False, f"more than {(1 - min_frac) * 100:.0f}% below the 52-week high"


# ------------------------------------------------------------------ Stage 2 / Trend Template

def _tt(ctx) -> dict:
    last = ctx.last
    return {"close": ctx.close, "s50": float(last["sma50"]), "s150": float(last["sma150"]), "s200": float(last["sma200"]),
            "s200_prev": float(last["sma200_21d_ago"]), "lo52": float(last["low_252"]), "hi52": float(last["high_252"]),
            "mom": float(last["mom_12_1"]) if pd.notna(last.get("mom_12_1")) else float("nan")}


def tt_above_sma50(ctx):
    v = _tt(ctx)
    return v["close"] > v["s50"], f"close {v['close']:.2f} vs SMA50 {v['s50']:.2f}"


def tt_above_sma150(ctx):
    v = _tt(ctx)
    return v["close"] > v["s150"], f"close {v['close']:.2f} vs SMA150 {v['s150']:.2f}"


def tt_above_sma200(ctx):
    v = _tt(ctx)
    return v["close"] > v["s200"], f"close {v['close']:.2f} vs SMA200 {v['s200']:.2f}"


def tt_stacked(ctx):
    v = _tt(ctx)
    return v["s50"] > v["s150"] > v["s200"], f"SMA50 {v['s50']:.2f} / SMA150 {v['s150']:.2f} / SMA200 {v['s200']:.2f}"


def tt_sma200_rising(ctx):
    v = _tt(ctx)
    return v["s200"] > v["s200_prev"], f"SMA200 {v['s200']:.2f} vs {v['s200_prev']:.2f} {SMA200_RISING_BARS} bars ago"


def tt_off_low(ctx):
    v = _tt(ctx)
    pct = (v["close"] / v["lo52"] - 1) * 100 if v["lo52"] > 0 else float("nan")
    ctx.extras["pct_above_52w_low"] = pct
    return pct >= MIN_PCT_ABOVE_52W_LOW, f"{pct:.1f}% above the 52-week low"


def tt_near_high(ctx):
    v = _tt(ctx)
    pct = (1 - v["close"] / v["hi52"]) * 100 if v["hi52"] > 0 else float("nan")
    ctx.extras["pct_below_52w_high"] = pct
    return pct <= MAX_PCT_BELOW_52W_HIGH, f"{pct:.1f}% below the 52-week high"


def tt_rs(ctx):
    """Per-stock RS stand-in (12-1 month momentum). The Stage 2 screen replaces it with the true
    cross-sectional rank when it screens a whole market (screens/stage2.py)."""
    v = _tt(ctx)
    ctx.extras["rs_mom"] = v["mom"]
    return pd.notna(v["mom"]) and v["mom"] >= RS_MIN_MOM, f"12-1 momentum {v['mom']:.3f}"


# ------------------------------------------------------------------ established uptrend (weekly + daily)

def weekly_above_rising_ema30(ctx):
    w = ctx.weekly
    if len(w) < 31 or pd.isna(w["ema30"].iloc[-1]):
        return False, "insufficient weekly history"
    rising = ind.is_rising(w["ema30"], 1)
    above = w["close"].iloc[-1] > w["ema30"].iloc[-1]
    if above and rising:
        return True, ""
    return False, "weekly close not above a rising 30-week EMA"


def weekly_sma20_above_sma50(ctx):
    w = ctx.weekly
    if len(w) < 50 or pd.isna(w["sma50"].iloc[-1]):
        return False, "insufficient weekly history"
    if w["sma20"].iloc[-1] > w["sma50"].iloc[-1]:
        return True, ""
    return False, "weekly SMA20 below weekly SMA50"


def daily_structure(ctx):
    d, close = ctx.daily, ctx.close
    sma50, sma200, atr14 = d["sma50"].iloc[-1], d["sma200"].iloc[-1], d["atr14"].iloc[-1]
    if pd.isna(sma50) or pd.isna(sma200) or pd.isna(atr14):
        return False, "insufficient history for SMA50/SMA200/ATR"
    structure_ok = sma50 > sma200
    broke_down = (close < sma50 - 2 * atr14) or bool((d["close"].iloc[-5:] < d["sma50"].iloc[-5:]).all())
    if structure_ok and not broke_down:
        return True, ""
    return False, "SMA50<=SMA200 or close broke down through SMA50"


def sma50_state(ctx) -> str:
    return ind.slope_state(ctx.daily["sma50"], 10, 1.0)


def averages_not_falling(ctx):
    s50, s200 = sma50_state(ctx), ind.slope_state(ctx.daily["sma200"], 20, 0.5)
    if s50 == "falling" or s200 == "falling":
        return False, f"SMA50 {s50}, SMA200 {s200}"
    return True, f"SMA50 {s50}, SMA200 {s200}"


def higher_swing_lows(ctx):
    if sw.higher_swing_lows(ctx.daily, 50):
        return True, ""
    return False, "no higher swing lows over the last ~50 bars"


def momentum_12_1_positive(ctx):
    d = ctx.daily
    if len(d) < 253:
        return False, "insufficient history for 12-1mo momentum"
    if d["close"].iloc[-22] > d["close"].iloc[-253]:
        return True, ""
    return False, "12-1 month momentum negative"


def within_25pct_of_high(ctx):
    high_252 = ctx.daily["high_252"].iloc[-1]
    if pd.isna(high_252):
        return False, "insufficient history for 52-week high"
    if ctx.close >= high_252 * 0.75:
        return True, ""
    return False, "close more than 25% below the 52-week high"


def trend_not_fading(ctx):
    d = ctx.daily
    if len(d) < 64:
        return False, "insufficient history for 3mo return"
    ret_3m = d["close"].iloc[-1] / d["close"].iloc[-64] - 1
    if ret_3m < 0 and sma50_state(ctx) in ("flat", "falling"):
        return False, "3mo return negative and SMA50 flat/falling"
    return True, ""
