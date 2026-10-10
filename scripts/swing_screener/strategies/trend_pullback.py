"""Trend-continuation strategy — the original system, ported behind the
Strategy interface with its logic unchanged.

Buys pullbacks (TC-01) and tight continuation bases (TC-02) inside an
already-established uptrend. Hard gates (W/T/D) decide whether the uptrend
is real; watch flags (X1-X9) cap confidence without disqualifying.

This file is a faithful move of the former gates.py / entry.py /
decision.classify / screener.passes_loose_filter — the logic was not
rewritten during the extraction, so a recorded golden baseline stays
byte-identical across the refactor. Known defects found during review are
listed in the module docstring of strategies/__init__.py rather than
silently fixed here, so the refactor and the fixes stay separable.
"""

import math

import pandas as pd

from ..core import indicators as ind
from ..core import swings as sw
from ..core import demand_supply as ds_mod
from ..config.base import MarketConfig
from ..core.context import StockContext
from .base import (
    CAP_ORDER,
    DOWNGRADE_MAP,
    LABELS,
    Decision,
    PlanChoice,
    Strategy,
    StrategyResult,
    TradePlan,
)

TC01 = "TC-01"
TC02 = "TC-02"
TC04 = "TC-04"


def round_tick(value: float, tick: float, direction: str) -> float:
    if tick <= 0:
        return value
    if direction == "up":
        return math.ceil(round(value / tick, 6)) * tick
    return math.floor(round(value / tick, 6)) * tick


class TrendPullbackStrategy(Strategy):
    selection = "time_series"
    version = "1.0"
    changelog = (
        ("1.0", "2026-10-10",
         "v1 baseline of the trend-pullback / continuation strategy."),
    )
    key = "trend_pullback"
    name = "Trend pullback / continuation"
    description = (
        "Long pullbacks (TC-01) and tight continuation bases (TC-02) within an "
        "established uptrend, entered on a resumption signal above resistance."
    )
    style = "pullback"
    gate_codes = ("W1", "W2", "T1", "T2", "T3", "T4", "T5", "T6", "D2", "D3", "D4", "D5", "D6", "D7")
    screen_key = "uptrend"
    screen_gates = {"W1": "U1", "W2": "U2", "T1": "U3", "T2": "U4", "T3": "U5", "T4": "U6", "T5": "U7", "T6": "U8"}
    watch_codes = ("X1", "X2", "X3", "X4", "X5", "X6", "X7", "X8", "X9")
    setup_codes = (TC01, TC02, TC04)
    min_bars = 260

    thesis = (
        "A stock in a confirmed uptrend that pulls back a measured amount and "
        "then resumes should continue, so buy the resumption rather than the dip."
    )
    how_it_works = (
        "**Screen** the universe on price, liquidity, ADX and volatility, and "
        "require SMA50 above SMA200.",
        "**Hard gates (W/T/D)** confirm the uptrend is real — weekly price above "
        "a rising 30-week EMA, higher swing lows, positive 12-1 momentum, within "
        "25% of the 52-week high — and disqualify specific hazards such as "
        "earnings inside 10 days or an unheld gap.",
        "**Setups** look for the shape: TC-01 a pullback 30-60% of the prior "
        "impulse (or 1-3 ATR) from a high 3-10 bars old, holding above the prior "
        "swing low and not on rising volume; TC-02 a tight continuation base on "
        "below-average volume. TC-04 is informational only.",
        "**Watch flags (X1-X9)** cap confidence without disqualifying — e.g. X1 "
        "marks a stock extended more than 2.5 ATR above its SMA20 or with RSI14 above 75.",
        "**Entry is a resting buy-stop ABOVE the current price**, so you only buy "
        "if price actually resumes. In the backtest it expires unfilled after 10 "
        "business days (the live screener only states this in the report).",
        "**Exit** is a fixed bracket: for TC-01 the stop sits just below the "
        "pullback low and the target is a measured move; for TC-02 the stop is the "
        "10-bar low minus 0.1 ATR and the target the 10-bar high plus twice the "
        "range. Either target is cut to the nearest overhead level above entry. "
        "There is no trailing stop and no time stop.",
    )
    caveats = (
        "**No demonstrated edge.** Backtested over 13.75 years it returned "
        "-0.87% CAGR in the US and +0.57% in India, against indices doing 12.79% "
        "and 11.68%.",
        "The confidence tiers do not discriminate — TRADE - HIGH CONFIDENCE "
        "performed no better than TRADE ON TRIGGER across 484 trades.",
        "The fixed target caps the upside: on Micron's 2025 run it would have "
        "exited at +36% against a +484% move.",
        "Plan B enters at H when Plan A fails the 2R test, which manufactures the R "
        "rather than earning it (when Plan A's resistance walk-up has already moved "
        "past H, Plan B's entry is actually lower).",
    )

    # ---------- full reference documentation (Strategy details page) ----------
    # Most thresholds below are bare literals inside evaluate() /
    # _compute_watch_flags() or class attributes (max_stop_*), not module
    # constants, so they are written out as numbers here; keep in sync.
    status = (
        "No demonstrated edge: portfolio backtest from 2013 with bracket exits "
        "returned -0.87% CAGR in the US (SPY 12.79%) and +0.57% in India "
        "(index 11.68%); seven alternative exit policies did not rescue it."
        " Measured before the 2026-10 cost fix (exit slippage was charged twice); re-measured runs moved by "
        "−0.8 to +0.9 points of CAGR (the extra cash changes which later signals are taken), so re-run before relying on it."
    )
    gate_docs = {
        "W1": "Passes when the latest weekly close is above the 30-week EMA AND that "
              "EMA is higher than it was one week earlier. Fails with fewer than 31 "
              "weekly bars.",
        "W2": "Passes when the weekly SMA20 is strictly above the weekly SMA50. Fails "
              "with fewer than 50 weekly bars.",
        "T1": "Passes when daily SMA50 > SMA200 AND price has not broken down through "
              "the SMA50 — i.e. the close is not more than 2 ATR14 below the SMA50 and "
              "the last 5 closes are not all below the SMA50.",
        "T2": "Passes unless either average is falling: SMA50 more than 1% below its "
              "value 10 bars ago, or SMA200 more than 0.5% below its value 20 bars "
              "ago. A flat average passes (a flat SMA50 raises X4).",
        "T3": "Passes when the last two confirmed daily swing lows (3 bars either side) "
              "in the last 50 bars are rising; with fewer than two, the lowest low of "
              "the last 25 bars must be above the lowest low of the 25 bars before.",
        "T4": "Passes when 12-1 month momentum is positive: the close 21 bars ago is "
              "above the close 252 bars ago. Needs at least 253 daily bars.",
        "T5": "Passes when the close is at least 75% of the 52-week (252-bar) high, "
              "i.e. no more than 25% below it.",
        "T6": "Fails only when BOTH the 63-bar (about 3-month) return is negative AND "
              "the SMA50 is flat or falling (T2's definition); otherwise passes.",
        "D2": "Passes unless the next earnings date is 10 or fewer business days "
              "away. Unknown earnings dates pass, and the backtest never enforces this "
              "gate (no point-in-time earnings calendar).",
        "D3": "Fails when the pullback is on rising volume: the average volume of the "
              "bars since the swing high H is higher than the average volume of the "
              "impulse from L (lowest low in the 40 bars before H) up to H.",
        "D4": "Fails when the close is below the prior structural swing low (the last "
              "confirmed daily swing low before H); passes if there is none.",
        "D5": "Fails when any overhead resistance level (daily swing highs of the last "
              "year, weekly of ~5 years, monthly of all history, plus H) sits within 3% "
              "above the close — unless the only such level is H itself and a "
              "{TC01} or {TC02} setup is present.",
        "D6": "Fails when ATR14 is more than 8% of price (too volatile).",
        "D7": "Fails when any of the last 10 bars opened with a gap of more than 8% "
              "(up or down) versus the prior close and the current close is still "
              "below that pre-gap close.",
    }
    watch_docs = {
        "X1": "Extended: close more than 2.5 ATR14 above the SMA20, OR RSI14 above "
              "75. Caps the decision at WATCH - WAIT (wait for a pullback toward the "
              "SMA20).",
        "X2": "Close below the SMA50 while still passing T1. Caps the decision at "
              "TRADE ON TRIGGER and lifts Plan A's trigger to at least 0.1% above the "
              "SMA50.",
        "X3": "Positive flag: close within 1 ATR14 of a rising SMA50. No cap; adds 1.0 "
              "to setup quality (used for ranking).",
        "X4": "SMA50 flat (neither higher than 10 bars ago nor more than 1% lower). "
              "Labelled base (10-bar range at most 4.5 ATR and close within 10% of the "
              "52-week high) or drift; drift caps at TRADE ON TRIGGER and subtracts 1.0 "
              "from setup quality, base has no effect.",
        "X5": "Low trend strength: ADX14 from 15 up to (not including) 20. Labelled "
              "base or drift as for X4; drift subtracts 1.0 from setup quality. Never "
              "caps the decision.",
        "X6": "ADX14 lower than 5 bars ago. If price is more than 5% below H and is "
              "closer to the SMA50 than 5 bars ago it is noted as momentum fading and "
              "subtracts 1.0 from setup quality. Never caps the decision.",
        "X7": "Late move: ADX14 above 40 together with X1. Forces Plan A (no switch to "
              "Plan B); X1 already caps the decision at WATCH - WAIT.",
        "X8": "Weak momentum: RSI14 below 40 while the close is above the SMA50. Caps "
              "the decision at TRADE ON TRIGGER.",
        "X9": "Monthly structure not confirmed (the former hard gate M1): with at least "
              "24 months of history, any of — monthly close not above its 10-month SMA, "
              "last-12-month high not above the prior 12 months', or last-12-month low "
              "not above the prior 12 months'. Caps the decision at TRADE ON TRIGGER.",
    }
    setup_docs = {
        TC01: "Pullback (entry-eligible, takes priority over {TC02}). The drop from H to "
              "the pullback low P is 30-60% of the impulse H-L, or 1-3 ATR14; H was "
              "set 3-10 bars ago; P is above the prior structural swing low; and the "
              "pullback is not on rising volume (the D3 test).",
        TC02: "Tight continuation base (entry-eligible). The last 10 bars span at most "
              "4.5 ATR14, the 5-day average volume is below the 50-day average, and "
              "the 10-bar low is above the prior structural swing low.",
        TC04: "Informational only, never an entry on its own: close within 2% of the "
              "55-bar high or of the 52-week high. Adds 0.5 to setup quality.",
    }
    entry_rules = (
        "The active setup is {TC01} if valid, otherwise {TC02}; with neither there is "
        "no plan. Every hard gate must pass or the decision is AVOID.",
        "Resumption signal (needed for TRADE - HIGH CONFIDENCE and for a backtest "
        "entry): the close is above the SMA20 and above the prior bar's high ({TC01}) "
        "or the highest high of the 10 bars before today ({TC02}), and no overhead "
        "level within 3% above the close sits more than 0.5% above H (H itself does "
        "not block).",
        "Plan A trigger starts at today's high ({TC01}) or the higher of today's high "
        "and the prior 10-bar high ({TC02}); with X2 it is raised to at least 0.1% "
        "above the SMA50. It then walks up: while any overhead level lies within 3% "
        "above the trigger, the trigger moves to the highest such level.",
        "Plan B trigger is H with no resistance walk-up, so its entry can sit just "
        "under resistance (known defect 1).",
        "Entry is a resting buy-stop at trigger + 0.1%, rounded up to the tick size, so "
        "it only fills if price trades up through it on a later bar.",
        "Stop: {TC01} uses the pullback low P minus 0.1 ATR14; {TC02} the lowest low of "
        "the last 10 bars (including today) minus 0.1 ATR14; rounded down to the tick.",
        "Target: {TC01} is P + (H - L), a measured move; {TC02} is the 10-bar high plus "
        "twice the 10-bar range. Either is cut to the nearest overhead level above "
        "the entry if that is lower.",
        "Plan choice: with X7 always Plan A; otherwise if Plan A is below 2R and Plan B "
        "reaches 2R, Plan B is used; else Plan A.",
        "TRADE - HIGH CONFIDENCE needs the signal fired, no capping watch flag, a stop "
        "no wider than 3.0 ATR and 12% of entry, at least 2R, and earnings not within "
        "14 business days (note: D2 uses 10 — known defect 4).",
        "WATCH - WAIT if the position is too large for the account, the stop exceeds "
        "3.5 ATR or 15% of entry, R is below 2, demand/supply reads 'Supply in "
        "control', or X1 is set. Everything else that passes the gates is TRADE ON "
        "TRIGGER. Live, a market-regime downgrade then drops the label one tier.",
        "A plan with NaN risk is not rejected in the live path (known defect 2); the "
        "backtest discards it via TradePlan.is_valid.",
    )
    exit_rules = (
        "Fixed bracket: the stop and target set at entry never move. No trailing stop, "
        "no time stop, no exit on a trend break.",
        "Unfilled buy-stops expire after 10 business days; in the backtest an order is "
        "also cancelled if price falls to the stop before filling, or if it gaps open "
        "at or above the target.",
        "Backtest fills: a gap through the trigger fills at the open; if stop and "
        "target are both touched on one bar the stop wins; a gap through the stop "
        "exits at the open. Positions still open at the end are marked at the last "
        "close.",
        "The portfolio backtest (the default) adds a position cap, slippage and "
        "commission, and sizes off current equity; it does not apply the earnings "
        "gate, the market-regime downgrade or the per-sector cap.",
    )
    param_docs = (
        ("Minimum price", "cfg.screener.min_price",
         "Pre-screen: close must be at least this (0 disables it, as in India)."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume",
         "Pre-screen: 20-day average of close x volume must be at least this."),
        ("Minimum ADX", "cfg.screener.adx_min",
         "Pre-screen: ADX14 must be strictly above this."),
        ("Minimum ATR %", "cfg.screener.atr_pct_min",
         "Pre-screen: ATR14 as % of price must be strictly above this."),
        ("Tick size", "cfg.tick_size",
         "Entry is rounded up and the stop rounded down to this increment."),
        ("Risk per trade", "cfg.risk_pct",
         "Fraction of the account risked between entry and stop; sets share count."),
        ("Risk per trade, high volatility", "cfg.risk_pct_high_vol",
         "Used instead of risk_pct when the volatility index is above its threshold."),
        ("Max position size", "cfg.max_position_pct",
         "Notional cap per position as a fraction of the account; can shrink size."),
        ("Max open positions", "cfg.max_open_positions",
         "Portfolio backtest: signals arriving with no free slot are missed."),
        ("Per-sector limit", "cfg.sector_limit_per_sector",
         "Live: at most this many tradeable names kept per sector (ranked by setup quality); the rest become WATCH - SECTOR LIMIT."),
        ("Slippage", "cfg.slippage_bps",
         "Portfolio backtest: cost per side in basis points of notional."),
    )
    backtest_args = ""

    # ---------- pre-filter ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        if cfg.screener.min_price and last["close"] < cfg.screener.min_price:
            return False, f"price {last['close']:.2f} < {cfg.screener.min_price}"
        if pd.isna(last["sma50"]) or pd.isna(last["sma200"]) or last["sma50"] <= last["sma200"]:
            return False, "SMA50 <= SMA200"
        if pd.isna(last["adx14"]) or last["adx14"] <= cfg.screener.adx_min:
            return False, f"ADX14 <= {cfg.screener.adx_min}"
        if pd.isna(last["atr_pct"]) or last["atr_pct"] <= cfg.screener.atr_pct_min:
            return False, f"ATR% <= {cfg.screener.atr_pct_min}"
        if cfg.screener.min_dollar_volume:
            dv = last.get("dollar_vol_sma20")
            if pd.isna(dv) or dv < cfg.screener.min_dollar_volume:
                return False, f"liquidity below {cfg.screener.min_dollar_volume:,.0f}"
        return True, "passed"

    # ---------- gates / flags / setups ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        d = ctx.daily
        result = StrategyResult(entry_setup_codes=(TC01, TC02))
        close = ctx.close

        # M1 (monthly structure) was a hard gate until review showed it
        # penalises a genuine recent recovery as hard as an ongoing
        # downtrend — it is now watch flag X9 below.

        # W1-W2, T1-T6: the Established-uptrend screen's criteria U1-U8 (screens/criteria.py)
        self.apply_screen(ctx, result)

        # D1 retired — extension is now watch flag X1
        result.ok("D1", "retired, see X1")

        # D2: earnings within 10 trading days
        if ctx.earnings_days_away is not None and ctx.earnings_days_away <= 10:
            result.fail("D2", f"earnings in {ctx.earnings_days_away} trading days")
        else:
            result.ok("D2")

        # D3: pullback on rising volume
        if sw.pullback_on_rising_volume(d, ctx.h_index, ctx.l_value):
            result.fail("D3", "pullback volume higher than impulse volume")
        else:
            result.ok("D3")

        # D4: close below the prior structural swing low
        if ctx.prior_swing_low is not None and close < ctx.prior_swing_low:
            result.fail("D4", "close below prior structural swing low")
        else:
            result.ok("D4")

        # D5 needs the setup result, so compute the inputs now and decide below
        near_levels = sw.levels_within_pct_above(close, ctx.overhead, 3.0)
        only_h = near_levels == [round(ctx.h_value, 4)] or (
            len(near_levels) == 1 and abs(near_levels[0] - ctx.h_value) < 1e-6
        )

        # D6: ATR14 above 8% of price
        atr_pct = d["atr_pct"].iloc[-1]
        if pd.notna(atr_pct) and atr_pct > 8:
            result.fail("D6", f"ATR% {atr_pct:.1f} > 8%")
        else:
            result.ok("D6")

        # D7: unheld gap >8% in the last 10 bars
        if sw.gap_not_held(d, 10, 8.0):
            result.fail("D7", "unheld gap >8% in the last 10 bars")
        else:
            result.ok("D7")

        self._compute_setups(ctx, result)

        if near_levels and not (only_h and (result.setups[TC01] or result.setups[TC02])):
            result.fail("D5", f"overhead level(s) within 3%: {near_levels}")
        else:
            result.ok("D5")

        result.recompute_first_fail()
        self._compute_watch_flags(ctx, result)
        return result

    def _compute_setups(self, ctx: StockContext, result: StrategyResult) -> None:
        d = ctx.daily
        atr14 = d["atr14"].iloc[-1]
        close = ctx.close
        h, l, p = ctx.h_value, ctx.l_value, ctx.p_value
        bars_since_h = (len(d) - 1) - d.index.get_loc(ctx.h_index)

        impulse = h - l
        depth_price = h - p
        pct_depth = depth_price / impulse if impulse > 0 else float("nan")
        atr_depth = depth_price / atr14 if atr14 and not pd.isna(atr14) else float("nan")

        s01 = (0.30 <= pct_depth <= 0.60) or (1 <= atr_depth <= 3)
        s02 = 3 <= bars_since_h <= 10
        s03_tc01 = ctx.prior_swing_low is None or p > ctx.prior_swing_low
        s04 = not sw.pullback_on_rising_volume(d, ctx.h_index, ctx.l_value)
        result.setups[TC01] = bool(s01 and s02 and s03_tc01 and s04)

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
        result.setups[TC02] = bool(s03_tc02 and s05)

        high_55 = d["high"].iloc[-55:].max()
        high_252 = d["high_252"].iloc[-1]
        result.setups[TC04] = bool(
            close >= high_55 * 0.98 or (pd.notna(high_252) and close >= high_252 * 0.98)
        )

    def _compute_watch_flags(self, ctx: StockContext, result: StrategyResult) -> None:
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
            result.watch_notes["X1"] = (
                f"extended; pullback target ~{target:.2f}" if target else "extended"
            )

        # X2: below SMA50 but within T1's tolerance
        below_50 = pd.notna(sma50) and close < sma50 and result.hard_gates.get("T1", False)
        result.watch_flags["X2"] = bool(below_50)

        # X3: at a rising SMA50 (positive flag)
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
            result.watch_notes["X4"] = sw.base_or_drift(d, atr14, d["high_252"].iloc[-1])

        # X5: low ADX (15-20) -> base or drift
        low_adx = pd.notna(adx14) and 15 <= adx14 < 20
        result.watch_flags["X5"] = bool(low_adx)
        if low_adx:
            result.watch_notes["X5"] = sw.base_or_drift(d, atr14, d["high_252"].iloc[-1])

        # X6: ADX falling
        adx_falling = ind.is_falling(d["adx14"], 5, 0.0)
        result.watch_flags["X6"] = bool(adx_falling)
        if adx_falling:
            if close >= ctx.h_value * 0.95:
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
                result.watch_notes["X6"] = (
                    "momentum fading toward SMA50" if fading else "falling, no clear fade"
                )

        # X7: late move — ADX>40 together with X1
        result.watch_flags["X7"] = bool(
            pd.notna(adx14) and adx14 > 40 and result.watch_flags["X1"]
        )

        # X8: weak momentum — RSI<40 while close above SMA50
        result.watch_flags["X8"] = bool(
            pd.notna(rsi14) and rsi14 < 40 and pd.notna(sma50) and close > sma50
        )

        # X9: monthly structure not yet confirmed (former hard gate M1)
        m = ctx.monthly
        if ctx.history_months < 24 or len(m) < 24 or pd.isna(m["sma10"].iloc[-1]):
            result.watch_flags["X9"] = False
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
                result.watch_notes["X9"] = (
                    "monthly structure not yet confirmed: " + "; ".join(reasons)
                )

    def watch_cap(self, result: StrategyResult) -> str:
        caps = []
        if result.watch_flags.get("X1"):
            caps.append("WATCH_WAIT")
        if result.watch_flags.get("X2"):
            caps.append("TRADE_ON_TRIGGER")
        if result.watch_flags.get("X4") and result.watch_notes.get("X4") == "drift":
            caps.append("TRADE_ON_TRIGGER")
        if result.watch_flags.get("X8"):
            caps.append("TRADE_ON_TRIGGER")
        if result.watch_flags.get("X9"):
            caps.append("TRADE_ON_TRIGGER")
        if not caps:
            return "TRADE_HIGH_CONFIDENCE"
        return min(caps, key=CAP_ORDER.index)

    def setup_quality(self, result: StrategyResult) -> float:
        score = 2.0 if result.setups.get(TC01) else (1.0 if result.setups.get(TC02) else 0.0)
        if result.setups.get(TC04):
            score += 0.5
        if result.watch_flags.get("X3"):
            score += 1.0
        if result.watch_flags.get("X4") and result.watch_notes.get("X4") == "drift":
            score -= 1.0
        if result.watch_flags.get("X5") and result.watch_notes.get("X5") == "drift":
            score -= 1.0
        if (
            result.watch_flags.get("X6")
            and result.watch_notes.get("X6") == "momentum fading toward SMA50"
        ):
            score -= 1.0
        return score

    # ---------- entry geometry ----------

    def active_setup(self, result: StrategyResult) -> str | None:
        """If both TC-01 and TC-02 are valid, TC-01 sets the stop and target."""
        if result.setups.get(TC01):
            return TC01
        if result.setups.get(TC02):
            return TC02
        return None

    def _resumption_signal(self, ctx: StockContext, setup: str) -> bool:
        d = ctx.daily
        sma20 = d["sma20"].iloc[-1]
        if sma20 != sma20:  # NaN
            return False
        ref_high = d["high"].iloc[-11:-1].max() if setup == TC02 else d["high"].iloc[-2]
        return bool(ctx.close > ref_high and ctx.close > sma20)

    # H -- the high the pullback started from -- is itself in ctx.overhead,
    # but H is the level this setup exists to break THROUGH. Counting it as
    # resistance is a catch-22: the closer price gets to triggering, the more
    # certainly the signal is suppressed. Measured over 2025-26, 31 of 31
    # otherwise-valid momentum entries were blocked, and in all 31 the
    # blocking level WAS H. Only genuine structure above H should block.
    own_level_tol_pct: float = 0.5

    # Stop distance is capped in ATRs, not in percent of price.
    #
    # The old caps (<=7% for TRADE, >8% -> WATCH_WAIT) were a volatility
    # filter wearing a risk label: because stop = P - 0.1*ATR and entry sits
    # near H, risk% is essentially the pullback depth, so a high-ATR stock
    # mechanically fails them no matter how well-placed the stop is. Measured
    # over 2025-26, 10 of 11 surviving momentum signals died on risk%>7 --
    # yet in ATR terms (0.84-2.91 ATR for trades actually taken) the rejects
    # sat in the SAME range: MU 2.53, TSM 2.36, AMD 1.93 ATR, tighter than
    # accepted trades like SAP 2.91 or CMI 2.80.
    #
    # Dollar risk per trade is already controlled by position sizing, which
    # buys fewer shares as the stop widens -- so admitting a wider percentage
    # stop does not increase risk taken; it only stops discarding volatile
    # leaders. Thresholds come from that measured range: 3.0 just above the
    # widest stop the system actually traded, 3.5 as the hard ceiling.
    max_stop_atr_trade: float = 3.0
    max_stop_atr_wait: float = 3.5

    # The ATR cap alone is NOT sufficient. It asks "is the stop sane for this
    # stock's volatility" -- a different question from "is the 2R target
    # reachable in a swing-trade timeframe". Measured cases where they
    # diverge: SWVL sat at 2.05 ATR but 27.5% of price, so with R>=2 enforced
    # the target needs a 55% move; ITGR was 4.5% of price but 13.5 ATR, a
    # stop absurdly wide for its own volatility. Both caps are therefore
    # kept, each guarding its own failure mode.
    #
    # 12% follows from the timeframe: a stop of X% needs a >=2X% move to pay
    # 2R, and ~24% is the top of what a multi-week swing plausibly delivers.
    # It admits the volatile leaders this strategy was wrongly excluding
    # (AMD 7.2%, TSM 7.6-9.1%, AVGO 8.5%, MU 10.9%) while still rejecting
    # SNDK 20.9%, MRVL 18.4% and SWVL 27.5%.
    max_stop_pct_trade: float = 12.0
    max_stop_pct_wait: float = 15.0

    def stop_atr_multiple(self, ctx: StockContext, plan: TradePlan) -> float:
        """Stop distance expressed in current ATRs (NaN if ATR unavailable)."""
        atr14 = float(ctx.daily["atr14"].iloc[-1])
        if not atr14 or atr14 != atr14:
            return float("nan")
        return plan.risk_per_share / atr14

    def blocking_overhead(self, ctx: StockContext) -> list[float]:
        """Overhead levels close enough above price to veto an entry,
        excluding the setup's own origin high."""
        near = sw.levels_within_pct_above(ctx.close, ctx.overhead, 3.0)
        ceiling = ctx.h_value * (1 + self.own_level_tol_pct / 100)
        return [lv for lv in near if lv > ceiling]

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        setup = self.active_setup(result)
        if setup is None:
            return False
        blocked = self.blocking_overhead(ctx)
        return bool(self._resumption_signal(ctx, setup) and not blocked)

    def _compute_trigger(self, ctx: StockContext, result: StrategyResult, setup: str) -> float:
        d = ctx.daily
        last_high = float(d["high"].iloc[-1])
        ref = max(last_high, float(d["high"].iloc[-11:-1].max())) if setup == TC02 else last_high

        trigger = ref
        if result.watch_flags.get("X2"):
            sma50 = d["sma50"].iloc[-1]
            if sma50 == sma50:
                trigger = max(trigger, float(sma50) * 1.001)

        for _ in range(50):  # hard cap; overhead list is finite
            near = sw.levels_within_pct_above(trigger * 1.001, ctx.overhead, 3.0)
            if not near:
                break
            highest = max(near)
            if highest <= trigger:
                break
            trigger = highest
        return trigger

    def _stop_target(self, ctx: StockContext, setup: str) -> tuple[float, float]:
        d = ctx.daily
        atr14 = float(d["atr14"].iloc[-1])
        if setup == TC01:
            return ctx.p_value - 0.1 * atr14, ctx.p_value + (ctx.h_value - ctx.l_value)
        low_10 = float(d["low"].iloc[-10:].min())
        high_10 = float(d["high"].iloc[-10:].max())
        return low_10 - 0.1 * atr14, high_10 + 2 * (high_10 - low_10)

    def _build_plan(
        self, ctx: StockContext, result: StrategyResult, tick_size: float, which: str
    ) -> TradePlan | None:
        setup = self.active_setup(result)
        if setup is None:
            return None

        raw_stop, raw_target = self._stop_target(ctx, setup)
        trigger = (
            self._compute_trigger(ctx, result, setup) if which == "A" else ctx.h_value
        )

        entry = round_tick(trigger * 1.001, tick_size, "up")
        stop = round_tick(raw_stop, tick_size, "down")

        nearest_above = sw.nearest_overhead_above(entry, ctx.overhead)
        target = raw_target
        if nearest_above is not None and nearest_above < target:
            target = nearest_above

        risk_per_share = entry - stop
        reward_per_share = target - entry
        r_multiple = reward_per_share / risk_per_share if risk_per_share > 0 else float("nan")

        return TradePlan(
            plan=which, setup=setup, entry=entry, stop=stop, target=target,
            risk_per_share=risk_per_share, reward_per_share=reward_per_share,
            r_multiple=r_multiple, nearest_overhead_above_entry=nearest_above,
        )

    def build_plans(
        self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig
    ) -> PlanChoice:
        plan_a = self._build_plan(ctx, result, cfg.tick_size, "A")
        if plan_a is None:
            return PlanChoice(None, None, "no active setup")
        plan_b = self._build_plan(ctx, result, cfg.tick_size, "B")

        if result.watch_flags.get("X7"):
            return PlanChoice(plan_a, plan_b, "X7 late move: Plan A (pullback) preferred")
        if plan_a.r_multiple < 2 and plan_b is not None and plan_b.r_multiple >= 2:
            return PlanChoice(plan_b, plan_a, "Plan A capped below 2R, Plan B (breakout) used instead")
        return PlanChoice(plan_a, plan_b, "Plan A (pullback)")

    # ---------- decision ----------

    def classify(
        self,
        ctx: StockContext,
        result: StrategyResult,
        plan: TradePlan,
        sizing_result,
        earnings_days_away: int | None,
        regime_downgrade_active: bool,
    ) -> Decision:
        if not result.hard_gates_passed:
            code = result.first_hard_fail
            reason = f"fails hard gate {code}: {result.hard_notes.get(code, '')}"
            return Decision("AVOID", "AVOID", reason, float("nan"), float("nan"), 0.0)

        ds = ds_mod.compute(ctx)
        risk_pct = plan.risk_per_share / plan.entry * 100 if plan.entry else float("nan")
        stop_atr = self.stop_atr_multiple(ctx, plan)
        r_mult = plan.r_multiple
        sig = self.entry_signal_fired(ctx, result)
        cap = self.watch_cap(result)
        supply_blocks = ds.verdict == "Supply in control"
        earnings_block_15 = earnings_days_away is not None and earnings_days_away < 15

        reasons: list[str] = []

        if sizing_result.too_large:
            label = "WATCH_WAIT"
            reasons.append("too large for account")
        elif (
            stop_atr > self.max_stop_atr_wait
            or risk_pct > self.max_stop_pct_wait
            or r_mult < 2
        ):
            label = "WATCH_WAIT"
            if stop_atr > self.max_stop_atr_wait:
                reasons.append(
                    f"stop {stop_atr:.2f} ATR > {self.max_stop_atr_wait} ATR "
                    f"({risk_pct:.1f}% of price)"
                )
            if risk_pct > self.max_stop_pct_wait:
                reasons.append(f"stop {risk_pct:.1f}% > {self.max_stop_pct_wait}% of price")
            if r_mult < 2:
                reasons.append(f"target {r_mult:.2f}R < 2R")
        elif supply_blocks:
            label = "WATCH_WAIT"
            reasons.append(f"demand/supply: {ds.verdict} ({ds.supports_demand_text})")
        elif cap == "WATCH_WAIT":
            label = "WATCH_WAIT"
            reasons.append(result.watch_notes.get("X1", "extended (X1)"))
        elif (
            sig
            and cap == "TRADE_HIGH_CONFIDENCE"
            and stop_atr <= self.max_stop_atr_trade
            and risk_pct <= self.max_stop_pct_trade
            and r_mult >= 2
            and not earnings_block_15
        ):
            label = "TRADE_HIGH_CONFIDENCE"
            reasons.append(f"{plan.setup} signal fired, {r_mult:.2f}R")
        else:
            label = "TRADE_ON_TRIGGER"
            if not sig:
                reasons.append("entry trigger not yet fired")
            if cap == "TRADE_ON_TRIGGER":
                capping = [
                    code for code in ("X2", "X4", "X8", "X9")
                    if result.watch_flags.get(code)
                    and (code != "X4" or result.watch_notes.get("X4") == "drift")
                ]
                reasons.append(f"capped by watch flag ({'/'.join(capping)})")
            if earnings_block_15:
                reasons.append(f"earnings in {earnings_days_away}d (blocks HIGH CONFIDENCE)")

        label_after = DOWNGRADE_MAP[label] if regime_downgrade_active else label
        if regime_downgrade_active:
            reasons.append("market-regime downgrade applied")

        return Decision(
            label_before=LABELS[label],
            label_after=LABELS[label_after],
            reason="; ".join(reasons) if reasons else "",
            risk_pct=risk_pct,
            r_multiple=r_mult,
            setup_quality=self.setup_quality(result),
        )

    def report_extras(
        self, ctx: StockContext, result: StrategyResult, plan: TradePlan | None
    ) -> dict:
        ds = ds_mod.compute(ctx)
        return {
            "demand_supply": f"{ds.verdict} ({ds.supports_demand_text})",
            "h_pct_above_close": round(ind.pct_distance(ctx.h_value, ctx.close), 1),
            "monthly": "recovering" if result.watch_flags.get("X9") else "up",
            "weekly": (
                "up"
                if result.hard_gates.get("W1") and result.hard_gates.get("W2")
                else "down"
            ),
        }
