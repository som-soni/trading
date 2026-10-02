"""STEP 3 — hard gates (M/W/T/D), watch flags (X1-X8), and setup gates
(TC-01/TC-02/TC-04). Direct transcription of the prompts; gate/flag codes
in comments match the prompt text so the two can be diffed against each
other when the prompt changes.
"""

from dataclasses import dataclass, field

import pandas as pd

from . import indicators as ind
from . import swings as sw

CAP_ORDER = ["AVOID", "WATCH_WAIT", "TRADE_ON_TRIGGER", "TRADE_HIGH_CONFIDENCE"]


@dataclass
class StockContext:
    """Everything the gate/flag/entry/pattern logic needs for one stock,
    computed once and passed around (avoids recomputing swing structure in
    five different places)."""

    symbol: str
    daily: pd.DataFrame  # enriched (indicators.enrich_daily)
    weekly: pd.DataFrame  # enriched (indicators.enrich_weekly)
    monthly: pd.DataFrame  # enriched (indicators.enrich_monthly)
    h_value: float
    h_index: pd.Timestamp
    l_value: float
    p_value: float
    prior_swing_low: float | None
    overhead: list[float]
    history_months: float
    earnings_days_away: int | None = None

    @property
    def last(self) -> pd.Series:
        return self.daily.iloc[-1]

    @property
    def close(self) -> float:
        return float(self.last["close"])


def build_context(
    symbol: str,
    daily_raw: pd.DataFrame,
    earnings_days_away: int | None = None,
) -> StockContext | None:
    """Build a StockContext from raw daily OHLCV. Returns None if there
    isn't enough history to compute the core structure (see DATA RULE)."""
    if daily_raw is None or len(daily_raw) < 60:
        return None

    daily = ind.enrich_daily(daily_raw)
    weekly = ind.enrich_weekly(ind.resample_weekly(daily_raw))
    monthly = ind.enrich_monthly(ind.resample_monthly(daily_raw))

    h_value, h_index = sw.current_swing_high(daily)
    l_value = sw.impulse_low(daily, h_index)
    p_value = sw.pullback_low(daily, h_index)
    prior_low = sw.prior_structural_swing_low(daily, h_index)
    overhead = sw.overhead_levels(daily, weekly, monthly, h_value)
    history_months = len(monthly)

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


@dataclass
class GateResult:
    hard_gates: dict[str, bool] = field(default_factory=dict)
    hard_notes: dict[str, str] = field(default_factory=dict)
    first_hard_fail: str | None = None
    watch_flags: dict[str, bool] = field(default_factory=dict)
    watch_notes: dict[str, str] = field(default_factory=dict)
    setup_tc01: bool = False
    setup_tc02: bool = False
    setup_tc04: bool = False

    @property
    def hard_gates_passed(self) -> bool:
        return self.first_hard_fail is None

    @property
    def has_setup(self) -> bool:
        return self.setup_tc01 or self.setup_tc02

    @property
    def watch_cap(self) -> str:
        """'If several caps apply, use the lowest' (most restrictive)."""
        caps = []
        if self.watch_flags.get("X1"):
            caps.append("WATCH_WAIT")
        if self.watch_flags.get("X2"):
            caps.append("TRADE_ON_TRIGGER")
        if self.watch_flags.get("X4") and self.watch_notes.get("X4") == "drift":
            caps.append("TRADE_ON_TRIGGER")
        if self.watch_flags.get("X8"):
            caps.append("TRADE_ON_TRIGGER")
        if self.watch_flags.get("X9"):
            caps.append("TRADE_ON_TRIGGER")
        if not caps:
            return "TRADE_HIGH_CONFIDENCE"
        return min(caps, key=CAP_ORDER.index)


def _fail(result: GateResult, code: str, note: str = "") -> None:
    result.hard_gates[code] = False
    if note:
        result.hard_notes[code] = note
    if result.first_hard_fail is None:
        result.first_hard_fail = code


def _pass(result: GateResult, code: str, note: str = "") -> None:
    result.hard_gates[code] = True
    if note:
        result.hard_notes[code] = note


def compute_gates(ctx: StockContext) -> GateResult:
    d = ctx.daily
    w = ctx.weekly
    result = GateResult()
    close = ctx.close

    # ---- Multi-timeframe (M / W) — hard gates ----
    # M1 (monthly close vs 10-month SMA, 12mo-vs-prior-12mo high/low
    # structure) used to live here as a hard gate, but it penalizes a
    # genuine recent recovery just as hard as a stock that's still falling
    # — a stock can be up 30%+ off its own low, confirmed on every other
    # timeframe, and still fail M1 purely because its 24-month low happens
    # to fall inside the trailing 12-month window rather than the prior
    # one (see HMC, discussed and verified against real cached data: W1,
    # W2, T1-T6 all passed, only M1 and D5 failed). Moved to watch flag X9
    # below — still computed and surfaced, just no longer disqualifying.

    # W1: weekly close above a rising 30-week EMA
    if len(w) < 31 or pd.isna(w["ema30"].iloc[-1]):
        _fail(result, "W1", "insufficient weekly history")
    else:
        rising = ind.is_rising(w["ema30"], 1)
        above = w["close"].iloc[-1] > w["ema30"].iloc[-1]
        if above and rising:
            _pass(result, "W1")
        else:
            _fail(result, "W1", "weekly close not above a rising 30-week EMA")

    # W2: weekly SMA20 above weekly SMA50
    if len(w) < 50 or pd.isna(w["sma50"].iloc[-1]):
        _fail(result, "W2", "insufficient weekly history")
    elif w["sma20"].iloc[-1] > w["sma50"].iloc[-1]:
        _pass(result, "W2")
    else:
        _fail(result, "W2", "weekly SMA20 below weekly SMA50")

    # ---- Trend (T) — hard gates ----
    sma50 = d["sma50"].iloc[-1]
    sma200 = d["sma200"].iloc[-1]
    atr14 = d["atr14"].iloc[-1]

    # T1: structure SMA50>SMA200 AND close hasn't broken down through SMA50
    if pd.isna(sma50) or pd.isna(sma200) or pd.isna(atr14):
        _fail(result, "T1", "insufficient history for SMA50/SMA200/ATR")
    else:
        structure_ok = sma50 > sma200
        broke_down = (close < sma50 - 2 * atr14) or bool(
            (d["close"].iloc[-5:] < d["sma50"].iloc[-5:]).all()
        )
        if structure_ok and not broke_down:
            _pass(result, "T1")
        else:
            _fail(result, "T1", "SMA50<=SMA200 or close broke down through SMA50")

    # T2: slope — fail if SMA50 or SMA200 falling; flat passes (flagged X4)
    sma50_state = ind.slope_state(d["sma50"], 10, 1.0)
    sma200_state = ind.slope_state(d["sma200"], 20, 0.5)
    if sma50_state == "falling" or sma200_state == "falling":
        _fail(result, "T2", f"SMA50 {sma50_state}, SMA200 {sma200_state}")
    else:
        _pass(result, "T2", f"SMA50 {sma50_state}, SMA200 {sma200_state}")

    # T3: higher swing lows over the last ~50 bars
    if sw.higher_swing_lows(d, 50):
        _pass(result, "T3")
    else:
        _fail(result, "T3", "no higher swing lows over the last ~50 bars")

    # T4: 12-1 month momentum positive (close 21 bars ago vs 252 bars ago)
    if len(d) < 253:
        _fail(result, "T4", "insufficient history for 12-1mo momentum")
    else:
        close_21_ago = d["close"].iloc[-22]
        close_252_ago = d["close"].iloc[-253]
        if close_21_ago > close_252_ago:
            _pass(result, "T4")
        else:
            _fail(result, "T4", "12-1 month momentum negative")

    # T5: leadership — close no more than 25% below the 52-week high
    high_252 = d["high_252"].iloc[-1]
    if pd.isna(high_252):
        _fail(result, "T5", "insufficient history for 52-week high")
    elif close >= high_252 * 0.75:
        _pass(result, "T5")
    else:
        _fail(result, "T5", "close more than 25% below the 52-week high")

    # T6: trend not fading — fail if 3mo return negative AND SMA50 flat/falling
    if len(d) < 64:
        _fail(result, "T6", "insufficient history for 3mo return")
    else:
        ret_3m = d["close"].iloc[-1] / d["close"].iloc[-64] - 1
        if ret_3m < 0 and sma50_state in ("flat", "falling"):
            _fail(result, "T6", "3mo return negative and SMA50 flat/falling")
        else:
            _pass(result, "T6")

    # ---- Disqualifiers (D) — hard gates ----
    # D1 retired — extension is now watch flag X1
    _pass(result, "D1", "retired, see X1")

    # D2: earnings/results within 10 trading days
    if ctx.earnings_days_away is not None and ctx.earnings_days_away <= 10:
        _fail(result, "D2", f"earnings in {ctx.earnings_days_away} trading days")
    else:
        _pass(result, "D2")

    # D3: pullback on rising volume
    if sw.pullback_on_rising_volume(d, ctx.h_index, ctx.l_value):
        _fail(result, "D3", "pullback volume higher than impulse volume")
    else:
        _pass(result, "D3")

    # D4: close below the prior structural swing low
    if ctx.prior_swing_low is not None and close < ctx.prior_swing_low:
        _fail(result, "D4", "close below prior structural swing low")
    else:
        _pass(result, "D4")

    # D5: overhead level within 3% above close (TC-01/TC-02 + H-only exception
    # handled after setup gates are computed, below)
    near_levels = sw.levels_within_pct_above(close, ctx.overhead, 3.0)
    only_h = near_levels == [round(ctx.h_value, 4)] or (
        len(near_levels) == 1 and abs(near_levels[0] - ctx.h_value) < 1e-6
    )

    # D6: ATR14 above 8% of price
    atr_pct = d["atr_pct"].iloc[-1]
    if pd.notna(atr_pct) and atr_pct > 8:
        _fail(result, "D6", f"ATR% {atr_pct:.1f} > 8%")
    else:
        _pass(result, "D6")

    # D7: gap >8% in the last 10 bars that has not held
    if sw.gap_not_held(d, 10, 8.0):
        _fail(result, "D7", "unheld gap >8% in the last 10 bars")
    else:
        _pass(result, "D7")

    # ---- Setup gates (computed before finalizing D5) ----
    _compute_setup_gates(ctx, result)

    if near_levels and not (only_h and (result.setup_tc01 or result.setup_tc02)):
        _fail(result, "D5", f"overhead level(s) within 3%: {near_levels}")
    else:
        _pass(result, "D5")

    # re-evaluate first_hard_fail now that D5 may have been added late
    result.first_hard_fail = next(
        (code for code, ok in result.hard_gates.items() if not ok), None
    )

    # ---- Watch flags (X) — never AVOID on their own ----
    _compute_watch_flags(ctx, result)

    return result


def _compute_setup_gates(ctx: StockContext, result: GateResult) -> None:
    d = ctx.daily
    atr14 = d["atr14"].iloc[-1]
    close = ctx.close
    h, l, p = ctx.h_value, ctx.l_value, ctx.p_value
    pos_now = len(d) - 1
    pos_h = d.index.get_loc(ctx.h_index)
    bars_since_h = pos_now - pos_h

    impulse = h - l
    depth_price = h - p
    pct_depth = depth_price / impulse if impulse > 0 else float("nan")
    atr_depth = depth_price / atr14 if atr14 and not pd.isna(atr14) else float("nan")

    s01 = (0.30 <= pct_depth <= 0.60) or (1 <= atr_depth <= 3)
    s02 = 3 <= bars_since_h <= 10
    s03_tc01 = ctx.prior_swing_low is None or p > ctx.prior_swing_low
    s04 = not sw.pullback_on_rising_volume(d, ctx.h_index, ctx.l_value)
    result.setup_tc01 = bool(s01 and s02 and s03_tc01 and s04)

    low_10 = d["low"].iloc[-10:].min()
    high_10 = d["high"].iloc[-10:].max()
    s03_tc02 = ctx.prior_swing_low is None or low_10 > ctx.prior_swing_low
    range_10 = high_10 - low_10
    vol_5d = d["volume"].iloc[-5:].mean()
    vol_sma50 = d["vol_sma50"].iloc[-1]
    s05 = (
        atr14
        and not pd.isna(atr14)
        and range_10 <= 4.5 * atr14
        and pd.notna(vol_sma50)
        and vol_5d < vol_sma50
    )
    result.setup_tc02 = bool(s03_tc02 and s05)

    high_55 = d["high"].iloc[-55:].max()
    high_252 = d["high_252"].iloc[-1]
    result.setup_tc04 = bool(
        close >= high_55 * 0.98 or (pd.notna(high_252) and close >= high_252 * 0.98)
    )


def _compute_watch_flags(ctx: StockContext, result: GateResult) -> None:
    d = ctx.daily
    close = ctx.close
    sma20 = d["sma20"].iloc[-1]
    sma50 = d["sma50"].iloc[-1]
    atr14 = d["atr14"].iloc[-1]
    rsi14 = d["rsi14"].iloc[-1]
    adx14 = d["adx14"].iloc[-1]

    # X1: extended
    extended = False
    if pd.notna(sma20) and pd.notna(atr14) and atr14:
        extended = (close - sma20) > 2.5 * atr14
    if pd.notna(rsi14) and rsi14 > 75:
        extended = True
    result.watch_flags["X1"] = bool(extended)
    if extended:
        target = sma20 if pd.notna(sma20) else None
        result.watch_notes["X1"] = f"extended; pullback target ~{target:.2f}" if target else "extended"

    # X2: below SMA50 but within T1 limits (T1 passed)
    below_50 = pd.notna(sma50) and close < sma50 and result.hard_gates.get("T1", False)
    result.watch_flags["X2"] = bool(below_50)

    # X3: at a rising SMA50 (positive flag, ranks setup up one step)
    sma50_state = ind.slope_state(d["sma50"], 10, 1.0)
    at_rising_50 = (
        pd.notna(sma50)
        and pd.notna(atr14)
        and atr14
        and abs(close - sma50) <= atr14
        and sma50_state == "rising"
    )
    result.watch_flags["X3"] = bool(at_rising_50)

    # X4: flat SMA50 -> base or drift
    flat_50 = sma50_state == "flat"
    result.watch_flags["X4"] = bool(flat_50)
    if flat_50:
        high_252 = d["high_252"].iloc[-1]
        result.watch_notes["X4"] = sw.base_or_drift(d, atr14, high_252)

    # X5: low ADX (15-20) -> base or drift
    low_adx = pd.notna(adx14) and 15 <= adx14 < 20
    result.watch_flags["X5"] = bool(low_adx)
    if low_adx:
        high_252 = d["high_252"].iloc[-1]
        result.watch_notes["X5"] = sw.base_or_drift(d, atr14, high_252)

    # X6: ADX falling
    adx_falling = ind.is_falling(d["adx14"], 5, 0.0)
    result.watch_flags["X6"] = bool(adx_falling)
    if adx_falling:
        near_h = close >= ctx.h_value * 0.95
        if near_h:
            result.watch_notes["X6"] = "healthy pause near H"
        else:
            dist_now = abs(close - sma50) if pd.notna(sma50) else float("nan")
            sma50_5ago = d["sma50"].iloc[-6] if len(d) > 5 else float("nan")
            close_5ago = d["close"].iloc[-6] if len(d) > 5 else float("nan")
            dist_5ago = (
                abs(close_5ago - sma50_5ago)
                if pd.notna(sma50_5ago) and pd.notna(close_5ago)
                else float("nan")
            )
            fading = pd.notna(dist_now) and pd.notna(dist_5ago) and dist_now < dist_5ago
            result.watch_notes["X6"] = "momentum fading toward SMA50" if fading else "falling, no clear fade"

    # X7: late move — ADX>40 together with X1
    late_move = pd.notna(adx14) and adx14 > 40 and result.watch_flags["X1"]
    result.watch_flags["X7"] = bool(late_move)

    # X8: weak momentum — RSI<40 while close above SMA50
    weak_momentum = pd.notna(rsi14) and rsi14 < 40 and pd.notna(sma50) and close > sma50
    result.watch_flags["X8"] = bool(weak_momentum)

    # X9: monthly structure not yet confirmed — formerly the hard gate M1
    # (monthly close vs 10-month SMA, 12mo-vs-prior-12mo high/low
    # structure). Demoted to a watch flag: a stock recovering from a
    # recent multi-year low fails this by construction even when every
    # other timeframe already confirms the trend, so it caps the decision
    # at TRADE ON TRIGGER instead of removing the stock outright — still
    # visible, still a discretionary call, not an automatic exclusion.
    m = ctx.monthly
    if ctx.history_months < 24 or len(m) < 24 or pd.isna(m["sma10"].iloc[-1]):
        result.watch_flags["X9"] = False  # not enough monthly history to judge either way
    else:
        above_sma10 = m["close"].iloc[-1] > m["sma10"].iloc[-1]
        last12_high = m["high"].iloc[-12:].max()
        prior12_high = m["high"].iloc[-24:-12].max()
        last12_low = m["low"].iloc[-12:].min()
        prior12_low = m["low"].iloc[-24:-12].min()
        reasons = []
        if not above_sma10:
            reasons.append("monthly close below 10mo SMA")
        if last12_high <= prior12_high:
            reasons.append(f"high not above prior year ({last12_high:.2f} vs {prior12_high:.2f})")
        if last12_low <= prior12_low:
            reasons.append(f"low not above prior year ({last12_low:.2f} vs {prior12_low:.2f})")
        result.watch_flags["X9"] = bool(reasons)
        if reasons:
            result.watch_notes["X9"] = "monthly structure not yet confirmed: " + "; ".join(reasons)
