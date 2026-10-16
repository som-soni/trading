"""Qualification criteria shared by the screens and the strategies that draw from them.

Each criterion takes a `StockContext` (core/context.py) and returns (passed, note). The code here was
moved verbatim out of the strategies' gate code, so a strategy that qualifies stocks through a screen
evaluates exactly as it did before (tests/golden_strategies.py proves it).

Naming
------
A criterion is named for the rule it tests, not for the screen that uses it, because screens
share rules: `above_sma200` serves both H1 and A1. A screen that keeps its *own variant* of a
shared rule prefixes it with its screen key — `stage2_above_sma200` beside `above_sma200`,
`uptrend_near_52w_high` beside `near_52w_high` — so the prefix always answers "whose version
is this?" and never decorates a rule that only one screen has.

Thresholds follow the same idea: one name per quantity (`MAX_PCT_BELOW_52W_HIGH`), prefixed with
the screen key where a screen sets its own (`UPTREND_MAX_PCT_BELOW_52W_HIGH`). The Trend
Template's are the unprefixed ones and have to stay that way: MAX_PCT_BELOW_52W_HIGH,
MIN_PCT_ABOVE_52W_LOW, RS_MIN_MOM, RS_MIN_RANK and SMA200_RISING_BARS are keys in the minervini
strategy's fingerprint (`strategies/base.py` spec_params), so renaming one fails the version gate
and invalidates the stored signals for a change that alters no behaviour.
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

# ---- near highs. Its own, tighter ceiling; the _FRAC form is the same number as a
# fraction of the high, which is how the snapshot conditions express it.
NEAR_HIGHS_MAX_PCT_BELOW_52W_HIGH = 15.0
NEAR_HIGHS_MIN_FRAC_OF_52W_HIGH = 1 - NEAR_HIGHS_MAX_PCT_BELOW_52W_HIGH / 100

# ---- established uptrend. Its own ceiling, deliberately not MAX_PCT_BELOW_52W_HIGH even
# though the two currently agree: the screens serve different strategies, so tuning the
# Trend Template must not silently move the uptrend screen.
UPTREND_MAX_PCT_BELOW_52W_HIGH = 25.0
UPTREND_MIN_FRAC_OF_52W_HIGH = 1 - UPTREND_MAX_PCT_BELOW_52W_HIGH / 100

# ---- moving-average slope. "falling" means more than FALLING_PCT% below its value SLOPE_BARS ago.
SMA200_FALLING_PCT = 0.5
SMA200_SLOPE_BARS = 20
SMA50_FALLING_PCT = 1.0
SMA50_SLOPE_BARS = 10


# ------------------------------------------------------------------ shared predicates
# Several screens ask the same question at different thresholds: three ask whether the
# close is above the 200-day (C3, H1, A1), three how far it is below the 52-week high
# (C7, H3, U7), two whether the 200-day is falling (H2, U4). Each question is answered
# in exactly one place below and each criterion only supplies its own ceiling, so two
# screens cannot drift apart on what the question means.
# tests/test_screen_criteria.py pins these against the per-screen criteria.

def _above_sma(ctx, col: str) -> bool:
    """Close strictly above a moving average; False when the average has no value yet."""
    v = ctx.daily[col].iloc[-1]
    return bool(pd.notna(v) and ctx.close > v)


def _pct_below_52w_high(ctx) -> float:
    """How far the close sits below the 52-week high, in percent. NaN — which fails every
    comparison, so a stock without a usable high never qualifies — when the high is
    missing or non-positive."""
    high_252 = ctx.daily["high_252"].iloc[-1]
    if pd.isna(high_252) or high_252 <= 0:
        return float("nan")
    return float((1 - ctx.close / high_252) * 100)


def sma50_state(ctx) -> str:
    return ind.slope_state(ctx.daily["sma50"], SMA50_SLOPE_BARS, SMA50_FALLING_PCT)


def sma200_state(ctx) -> str:
    return ind.slope_state(ctx.daily["sma200"], SMA200_SLOPE_BARS, SMA200_FALLING_PCT)


# ------------------------------------------------------------------ long-term trend (200-day)

def above_sma200(ctx) -> tuple[bool, str]:
    if _above_sma(ctx, "sma200"):
        return True, ""
    return False, "close at/below SMA200"


def sma200_not_falling(ctx) -> tuple[bool, str]:
    state = sma200_state(ctx)
    if state == "falling":
        return False, "SMA200 falling"
    return True, f"SMA200 {state}"


def near_52w_high(ctx) -> tuple[bool, str]:
    pct = _pct_below_52w_high(ctx)
    if pd.isna(pct):
        return False, "insufficient history for the 52-week high"
    if pct <= NEAR_HIGHS_MAX_PCT_BELOW_52W_HIGH:
        return True, ""
    return False, f"more than {NEAR_HIGHS_MAX_PCT_BELOW_52W_HIGH:g}% below the 52-week high"


# ------------------------------------------------------------------ Stage 2 / Trend Template

def _stage2_vals(ctx) -> dict:
    last = ctx.last
    return {"close": ctx.close, "s50": float(last["sma50"]), "s150": float(last["sma150"]), "s200": float(last["sma200"]),
            "s200_prev": float(last["sma200_21d_ago"]), "lo52": float(last["low_252"]), "hi52": float(last["high_252"]),
            "mom": float(last["mom_12_1"]) if pd.notna(last.get("mom_12_1")) else float("nan")}


def stage2_above_sma50(ctx):
    v = _stage2_vals(ctx)
    return _above_sma(ctx, "sma50"), f"close {v['close']:.2f} vs SMA50 {v['s50']:.2f}"


def stage2_above_sma150(ctx):
    v = _stage2_vals(ctx)
    return _above_sma(ctx, "sma150"), f"close {v['close']:.2f} vs SMA150 {v['s150']:.2f}"


def stage2_above_sma200(ctx):
    """C3 asks exactly what H1 and A1 ask; only the note differs."""
    v = _stage2_vals(ctx)
    return _above_sma(ctx, "sma200"), f"close {v['close']:.2f} vs SMA200 {v['s200']:.2f}"


def stage2_stacked(ctx):
    v = _stage2_vals(ctx)
    return v["s50"] > v["s150"] > v["s200"], f"SMA50 {v['s50']:.2f} / SMA150 {v['s150']:.2f} / SMA200 {v['s200']:.2f}"


def stage2_sma200_rising(ctx):
    v = _stage2_vals(ctx)
    return v["s200"] > v["s200_prev"], f"SMA200 {v['s200']:.2f} vs {v['s200_prev']:.2f} {SMA200_RISING_BARS} bars ago"


def stage2_off_low(ctx):
    v = _stage2_vals(ctx)
    pct = (v["close"] / v["lo52"] - 1) * 100 if v["lo52"] > 0 else float("nan")
    ctx.extras["pct_above_52w_low"] = pct
    return pct >= MIN_PCT_ABOVE_52W_LOW, f"{pct:.1f}% above the 52-week low"


def stage2_near_high(ctx):
    pct = _pct_below_52w_high(ctx)
    ctx.extras["pct_below_52w_high"] = pct
    return pct <= MAX_PCT_BELOW_52W_HIGH, f"{pct:.1f}% below the 52-week high"


def stage2_rs(ctx):
    """TT-08. The TRUE cross-sectional rank when the caller has rated the whole market, and the
    per-stock 12-1 momentum stand-in only when it has not.

    A rank is cross-sectional, so a one-symbol evaluation cannot compute one -- which is why the
    stand-in exists at all. A caller that holds the whole market seeds `rs_ranked` and `rs_rank`
    (backtesting/spec.rs_rank_asof, the same ratings `filter_min_rs` gates on), and then this
    answers with the rating a backtested trade had to clear instead of a looser proxy for it.

    A BACKTEST leaves it unseeded on purpose: it applies the real rating after collecting signals
    (filter_min_rs), so ranking inside the per-bar scan would only cost time for the same answer.
    The market-wide screen likewise replaces it via `Screen.rank_rs` (screens/definitions.py)."""
    v = _stage2_vals(ctx)
    ctx.extras["rs_mom"] = v["mom"]
    if ctx.extras.get("rs_ranked"):
        rank = ctx.extras.get("rs_rank")
        if rank is None or pd.isna(rank):
            # filter_min_rs drops these as "outside the rated universe"; say the same thing here
            # rather than quietly falling back to a test the backtest would not have applied
            return False, "outside the rated universe (too cheap, too thin or too new)"
        return float(rank) >= RS_MIN_RANK, f"RS rank {int(rank)}"
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


def averages_not_falling(ctx):
    s50, s200 = sma50_state(ctx), sma200_state(ctx)
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


def uptrend_near_52w_high(ctx):
    """The uptrend screen's own 52-week-high ceiling — looser than the Trend Template's."""
    pct = _pct_below_52w_high(ctx)
    if pd.isna(pct):
        return False, "insufficient history for the 52-week high"
    if pct <= UPTREND_MAX_PCT_BELOW_52W_HIGH:
        return True, ""
    return False, f"close more than {UPTREND_MAX_PCT_BELOW_52W_HIGH:g}% below the 52-week high"


def trend_not_fading(ctx):
    d = ctx.daily
    if len(d) < 64:
        return False, "insufficient history for 3mo return"
    ret_3m = d["close"].iloc[-1] / d["close"].iloc[-64] - 1
    if ret_3m < 0 and sma50_state(ctx) in ("flat", "falling"):
        return False, "3mo return negative and SMA50 flat/falling"
    return True, ""
