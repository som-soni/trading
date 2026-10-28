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
MIN_PCT_ABOVE_52W_LOW, RS_MIN_SCORE, RS_MIN_RANK and SMA200_RISING_BARS are keys in the minervini
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
RS_MIN_SCORE = 0.50              # per-stock floor when no market is there to rank against:
                                 # the weighted RS score (core.indicators.rs_score), the same
                                 # quantity the 1-99 rating ranks -- see `rs_strong`
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

# ---- big movers (Kullamägi's universe): fast stocks that have just made a large move. ADR is the
# average daily range, the mean of each session's high / low - 1; the prior move compares the
# highest high of the last MOVERS_HIGH_BARS sessions with the lowest low of the last MOVERS_LOW_BARS.
MOVERS_ADR_BARS = 20
MOVERS_MIN_ADR_PCT = 4.0
MOVERS_HIGH_BARS = 20
MOVERS_LOW_BARS = 63
MOVERS_MIN_MOVE_PCT = 30.0

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
            "rs": float(last["rs_score"]) if pd.notna(last.get("rs_score")) else float("nan")}


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
    per-stock floor on the same weighted RS score only when it has not.

    A rank is cross-sectional, so a one-symbol evaluation cannot compute one -- which is why the
    stand-in exists at all. A caller that holds the whole market seeds `rs_ranked` and `rs_rank`
    (backtesting/spec.rs_rank_asof, the same ratings `filter_min_rs` gates on), and then this
    answers with the rating a backtested trade had to clear instead of a looser proxy for it.

    A BACKTEST leaves it unseeded on purpose: it applies the real rating after collecting signals
    (filter_min_rs), so ranking inside the per-bar scan would only cost time for the same answer.
    The market-wide screen likewise replaces it via `Screen.rank_rs` (screens/definitions.py)."""
    v = _stage2_vals(ctx)
    ctx.extras["rs_score"] = v["rs"]
    if ctx.extras.get("rs_ranked"):
        rank = ctx.extras.get("rs_rank")
        if rank is None or pd.isna(rank):
            # filter_min_rs drops these as "outside the rated universe"; say the same thing here
            # rather than quietly falling back to a test the backtest would not have applied
            return False, "outside the rated universe (too cheap, too thin or too new)"
        return float(rank) >= RS_MIN_RANK, f"RS rank {int(rank)}"
    # The floor is on the SAME quantity the rating ranks, so the two stages agree. It used to be
    # 12-1 momentum, which skips the most recent month and so discounts exactly the quarter the
    # rating counts twice: measured over 2012-2026 that cut 8.1% of US and 6.6% of Indian names
    # that passed the whole Trend Template AND rated RS {RS_MIN_RANK}+ -- RELINFRA at RS 88 with
    # 12-1 momentum of -0.14, AGO at RS 90 with +0.02. The floor below cuts 0.8% and 0.5% of them.
    return pd.notna(v["rs"]) and v["rs"] >= RS_MIN_SCORE, f"RS score {v['rs']:.2f}"


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


# ------------------------------------------------------------------ trend aligned on three timeframes
# The "convergence, not conflict" rule: an uptrend on the daily, the weekly and the monthly chart at once.
# Daily: the 50-day above the 200-day, both higher than TF_DAILY_RISE_BARS sessions ago. Weekly: the close
# above a TF_WEEKS-week average that is higher than TF_WEEKLY_RISE_WEEKS weeks ago. Monthly: the close above
# a TF_MONTHS-month average that is higher than TF_MONTHLY_RISE_MONTHS months ago. The current week and month
# count as they stand that day (today's close closes them), so the flag is point in time and identical
# whether the history ends that day or runs on.
TF_DAILY_FAST = 50
TF_DAILY_SLOW = 200
TF_DAILY_RISE_BARS = 20
TF_WEEKS = 30
TF_WEEKLY_RISE_WEEKS = 4
TF_MONTHS = 10
TF_MONTHLY_RISE_MONTHS = 3


def trend_alignment(close: pd.Series) -> pd.DataFrame:
    """Per session: `daily`, `weekly`, `monthly` uptrend flags and `aligned` (all three), from closes on a
    DatetimeIndex. Vectorised for backtests; `trend_aligned_dwm` reads its last row."""
    c = close.astype(float)
    f, sl = c.rolling(TF_DAILY_FAST).mean(), c.rolling(TF_DAILY_SLOW).mean()
    daily = (f > sl) & (f > f.shift(TF_DAILY_RISE_BARS)) & (sl > sl.shift(TF_DAILY_RISE_BARS))

    def to_date(freq: str, n: int, rise: int) -> pd.Series:
        # On each session the week (month) is the period SO FAR: today's close stands in for the period's
        # close, the earlier periods are complete. Its n-period average is (the n-1 completed closes before
        # it + today's close) / n, and "rising" compares it with the completed average `rise` periods back.
        # Every input is known on that session, so the flag is the same whether the history ends today or
        # runs on for years -- the screen and a backtest read one definition.
        per = c.index.to_period(freq)
        last = c.groupby(per).last()                         # each period's close (only earlier ones are used)
        prev_sum = last.shift(1).rolling(n - 1).sum()        # the n-1 completed closes before the period
        ref = last.rolling(n).mean().shift(rise)             # the completed average `rise` periods back
        ma = (prev_sum.reindex(per).to_numpy() + c.to_numpy()) / n
        ref_d = ref.reindex(per).to_numpy()
        ok = (c.to_numpy() > ma) & (ma > ref_d)
        return pd.Series(ok, index=c.index).fillna(False).astype(bool)

    weekly = to_date("W-FRI", TF_WEEKS, TF_WEEKLY_RISE_WEEKS)
    monthly = to_date("M", TF_MONTHS, TF_MONTHLY_RISE_MONTHS)
    return pd.DataFrame({"daily": daily.fillna(False), "weekly": weekly, "monthly": monthly,
                         "aligned": daily.fillna(False) & weekly & monthly}, index=c.index)


def trend_aligned_dwm(ctx):
    d = ctx.daily
    if len(d) < TF_DAILY_SLOW + TF_DAILY_RISE_BARS:
        return False, "insufficient history for three timeframes"
    r = trend_alignment(d["close"]).iloc[-1]
    if r["aligned"]:
        return True, ""
    missing = [k for k in ("daily", "weekly", "monthly") if not r[k]]
    return False, f"no uptrend on the {', '.join(missing)} chart"


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


# ------------------------------------------------------------------ big movers (Kullamägi)
# adr_pct and prior_move_pct are the quantities themselves, shared with the snapshot fields of the
# same names (screens/snapshot.py) and the kullamagi strategy, so a condition on them is exact.

def adr_pct(daily: pd.DataFrame) -> float:
    """Average daily range over the last MOVERS_ADR_BARS sessions, in percent: the mean of
    high / low - 1. NaN with fewer bars or a non-positive low."""
    d = daily.iloc[-MOVERS_ADR_BARS:]
    if len(d) < MOVERS_ADR_BARS:
        return float("nan")
    hi, lo = d["high"].to_numpy(float), d["low"].to_numpy(float)
    if not (lo > 0).all():
        return float("nan")
    return float((hi / lo - 1).mean() * 100)


def prior_move_pct(daily: pd.DataFrame) -> float:
    """How far the highest high of the last MOVERS_HIGH_BARS sessions sits above the lowest low of
    the last MOVERS_LOW_BARS, in percent. NaN with fewer bars or a non-positive low."""
    if len(daily) < MOVERS_LOW_BARS:
        return float("nan")
    hi = float(daily["high"].iloc[-MOVERS_HIGH_BARS:].max())
    lo = float(daily["low"].iloc[-MOVERS_LOW_BARS:].min())
    if not lo > 0:
        return float("nan")
    return (hi / lo - 1) * 100


def fast_mover(ctx):
    v = adr_pct(ctx.daily)
    if pd.isna(v):
        return False, "insufficient history for the average daily range"
    if v >= MOVERS_MIN_ADR_PCT:
        return True, f"ADR {v:.1f}%"
    return False, f"ADR {v:.1f}% under {MOVERS_MIN_ADR_PCT:g}%"


def big_prior_move(ctx):
    v = prior_move_pct(ctx.daily)
    if pd.isna(v):
        return False, "insufficient history for the prior move"
    if v >= MOVERS_MIN_MOVE_PCT:
        return True, f"prior move {v:.0f}%"
    return False, f"prior move {v:.0f}% under {MOVERS_MIN_MOVE_PCT:g}%"
