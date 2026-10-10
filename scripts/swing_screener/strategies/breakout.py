"""Breakout strategy — a second, deliberately different implementation.

Its purpose is twofold: it's a usable strategy, and it proves the Strategy
seam is real. It shares none of trend_pullback's gate vocabulary, setup
codes, entry geometry or watch flags — it only consumes the same shared
StockContext and emits the same StrategyResult/TradePlan/Decision types.
If adding this had required editing pipeline.py, backtest.py, output.py or
the storage layer, the abstraction would have been fake.

Thesis: buy a decisive, volume-confirmed break to new highs out of a tight
consolidation, rather than buying weakness inside a trend.

NOT yet validated against market data — the gate thresholds here are
reasonable defaults, not tuned or backtested numbers. Run it through
backtest.py before trusting it.
"""

import pandas as pd

from ..core import swings as sw
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
from .trend_pullback import round_tick

BO01 = "BO-01"  # new-high breakout from consolidation
BO02 = "BO-02"  # pre-breakout coil, sitting just under the pivot

CONSOLIDATION_BARS = 20
BREAKOUT_LOOKBACK = 55


class BreakoutStrategy(Strategy):
    selection = "time_series"
    version = "1.0"
    changelog = (
        ("1.0", "2026-10-10",
         "v1 baseline of the volume-confirmed breakout strategy."),
    )
    key = "breakout"
    name = "Volume-confirmed breakout"
    description = (
        "Long breakouts to new 55-day highs out of a tight consolidation, "
        "confirmed by expanding volume."
    )
    style = "breakout"
    gate_codes = ("B1", "B2", "B3", "B4", "B5", "B6", "B7")
    screen_key = "near_highs"
    screen_gates = {"B1": "H1", "B2": "H2"}
    watch_codes = ("XB1", "XB2", "XB3")
    setup_codes = (BO01, BO02)
    min_bars = 260

    needs_ctx_extras = True
    extra_columns = ("breakout_pivot", "pct_from_pivot", "structural_r")
    extra_numeric_columns = ("breakout_pivot", "pct_from_pivot", "structural_r")

    # Minimum reward the consolidation must actually project, measured off the
    # base height. Nothing pads a setup up to this — it is a rejection
    # threshold, not a target floor.
    min_structural_r: float = 2.0

    thesis = (
        "A decisive, volume-confirmed break to new highs out of a tight "
        "consolidation continues, so buy strength rather than weakness."
    )
    how_it_works = (
        "**Screen** for stocks above their SMA200 and within 20% of the 52-week high.",
        "**Gates B1-B7** require an SMA200 that is not falling (no more than 0.5% "
        "below its level 20 bars ago), price within 5% of the 52-week high, a "
        "tight {CONSOLIDATION_BARS}-bar base (range under 6 ATR), not already "
        "extended beyond 4 ATR above SMA20, ATR no more than 8% of price, and "
        "no earnings inside 10 days.",
        "**Setups**: BO-01 is a close above the {BREAKOUT_LOOKBACK}-day pivot on "
        "confirming volume; BO-02 is a coil sitting within 3% below that pivot. "
        "Only BO-01 is the entry signal, so only BO-01 can reach TRADE - HIGH CONFIDENCE.",
        "**Entry** is 0.1% above the higher of today's high and the pivot, rounded "
        "up to the tick; for BO-01 the signal *is* the setup, because the close "
        "has already cleared the pivot.",
        "**Exit**: stop below the consolidation (never wider than 2 ATR), target "
        "the entry plus the base height, lowered to the nearest overhead level "
        "if one is in the way. Plans projecting under 2R are not traded.",
    )
    caveats = (
        "**NOT VALIDATED.** The thresholds are reasonable defaults, not tuned. "
        "Backtested once (US, 500-symbol sample, bracket exits): -1.74% CAGR, "
        "about 14.6 points a year behind SPY — see research/momentum-trend-research.md.",
        "Treat anything it produces as a hypothesis to test, not a signal to act on.",
        "The target is the measured move off the base, with no floor; setups "
        "projecting under 2R are rejected rather than padded. When an overhead "
        "level lowers the target, the R column is smaller than `structural_r`, "
        "and the 2R test uses the lowered R.",
        "Watch flag XB2 (breakout on below-average volume) can never fire: it needs "
        "BO-01, which already requires volume above 1.5x average.",
    )

    # --- full reference documentation (generated Strategy page) ---
    status = (
        "Not validated, no demonstrated edge: thresholds are untuned defaults, and the one "
        "recorded run (US, 500-symbol sample, bracket exits) returned -1.74% CAGR, "
        "about 14.6 points a year behind SPY."
        " Measured before the 2026-10 cost fix (exit slippage was charged twice); re-measured runs moved by "
        "−0.8 to +0.9 points of CAGR (the extra cash changes which later signals are taken), so re-run before relying on it."
    )
    gate_docs = {
        "B1": "The latest close must be strictly above the 200-day SMA. A missing SMA200 fails.",
        "B2": "The 200-day SMA must not be falling. It fails only if SMA200 is more than 0.5% "
              "below its value 20 bars ago, so a flat SMA200 passes as well as a rising one.",
        "B3": "The close must be at least 95% of the 52-week high (high_252, which includes "
              "today's bar), i.e. no more than 5% below it. Fails if the 52-week high is unavailable.",
        "B4": "The {CONSOLIDATION_BARS} bars before today must form a tight base: their highest "
              "high minus lowest low must be at most 6 x ATR14. Fails if there are fewer than "
              "{CONSOLIDATION_BARS} prior bars or ATR is missing or zero.",
        "B5": "The close must not be more than 4 x ATR14 above the 20-day SMA (exactly 4 ATR "
              "passes). If SMA20 or ATR is missing the gate passes.",
        "B6": "ATR14 as a percent of the close must be 8% or less. If ATR% is missing the gate passes.",
        "B7": "Earnings must not be 10 or fewer days away. Passes when no earnings date is "
              "known; the backtest has no historical earnings calendar, so it always passes there.",
    }
    watch_docs = {
        "XB1": "Raised when the close is more than 2.5 x ATR14 above the 20-day SMA (extended; the "
               "note suggests SMA20 as a pullback level). Caps the decision at TRADE ON TRIGGER and "
               "lowers setup quality by 0.5.",
        "XB2": "Meant to flag a breakout on below-average volume: raised only when BO-01 is active "
               "AND today's volume is below its 50-day average. Would cap the decision at WATCH - "
               "WAIT and cut setup quality by 1. In practice it can never fire, because BO-01 "
               "itself requires volume above 1.5x the 50-day average.",
        "XB3": "Raised when RSI14 is above 80 (overbought). Caps the decision at TRADE ON TRIGGER; "
               "no effect on setup quality.",
    }
    setup_docs = {
        "BO-01": "Breakout: today's close is strictly above the pivot (the highest high of the "
                 "{BREAKOUT_LOOKBACK} bars before today) AND today's volume is more than 1.5x its "
                 "50-day average. Entry-eligible, and it is also the entry signal, so only BO-01 can "
                 "reach TRADE - HIGH CONFIDENCE (setup quality 2).",
        "BO-02": "Coil: the close is within 3% below the pivot (between 97% and 100% of it), not "
                 "through it yet. Entry-eligible but the signal has not fired, so the best it gets is "
                 "TRADE ON TRIGGER (setup quality 1). If BO-01 is also true, BO-01 is used.",
    }
    entry_rules = (
        "Entry is a buy-stop at 0.1% above the higher of today's high and the "
        "{BREAKOUT_LOOKBACK}-bar pivot, rounded up to the market's tick size.",
        "Stop is the lowest low of the {CONSOLIDATION_BARS} bars before today minus 0.1 ATR, but "
        "never more than 2 ATR below entry (whichever is higher), rounded down to the tick.",
        "Target is entry plus the base height (highest high minus lowest low of the "
        "{CONSOLIDATION_BARS} prior bars), with no minimum R. If an overhead supply level sits "
        "between entry and that target, the target is lowered to the nearest one.",
        "A plan is WATCH - WAIT if the position is too large for the account, the stop is more than "
        "8% below entry, or the plan offers less than 2R. TRADE - HIGH CONFIDENCE additionally "
        "needs BO-01, no watch-flag cap, a stop of 7% or less, at least 2R and no earnings within "
        "15 days; otherwise TRADE ON TRIGGER. A market-regime downgrade lowers the label one tier.",
    )
    exit_rules = (
        "Live: a fixed bracket. The stop and target set at entry do not move; there is no trailing "
        "stop or time exit in the strategy itself.",
        "Backtest (default bracket mode): only TRADE - HIGH CONFIDENCE signals (so only BO-01) are "
        "placed, as resting buy-stops that fill on a later bar trading through the entry (at the "
        "open if it gaps above) and expire unfilled after 10 business days, or are cancelled if "
        "price hits the stop first or gaps past the target.",
        "Backtest exits: the first later bar whose low touches the stop or whose high touches the "
        "target closes the trade; if both on one bar the stop is assumed first, and gaps fill at "
        "the open. Positions still open at the end are marked at the last close.",
    )
    param_docs = (
        ("Consolidation length", "CONSOLIDATION_BARS",
         "Bars before today that must form the tight base (B4) and that define stop and target."),
        ("Pivot lookback", "BREAKOUT_LOOKBACK",
         "Bars before today whose highest high is the breakout pivot for BO-01/BO-02 and entry."),
        ("Minimum price", "cfg.screener.min_price",
         "Pre-filter: symbols closing below this price are not screened."),
        ("Minimum ATR%", "cfg.screener.atr_pct_min",
         "Pre-filter: ATR14 as % of close must exceed this, so very quiet stocks are skipped."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume",
         "Pre-filter: 20-day average dollar volume must be at least this."),
        ("Tick size", "cfg.tick_size",
         "Entry is rounded up and the stop rounded down to this increment."),
        ("Max open positions", "cfg.max_open_positions",
         "Portfolio backtest: position slots; signals arriving with no free slot are missed."),
    )
    backtest_args = ""

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        if cfg.screener.min_price and last["close"] < cfg.screener.min_price:
            return False, f"price {last['close']:.2f} < {cfg.screener.min_price}"
        if pd.isna(last["sma200"]) or last["close"] <= last["sma200"]:
            return False, "close <= SMA200"
        if pd.isna(last["atr_pct"]) or last["atr_pct"] <= cfg.screener.atr_pct_min:
            return False, f"ATR% <= {cfg.screener.atr_pct_min}"
        if cfg.screener.min_dollar_volume:
            dv = last.get("dollar_vol_sma20")
            if pd.isna(dv) or dv < cfg.screener.min_dollar_volume:
                return False, f"liquidity below {cfg.screener.min_dollar_volume:,.0f}"
        if pd.isna(last["high_252"]) or last["close"] < last["high_252"] * 0.80:
            return False, "more than 20% below the 52-week high"
        return True, "passed"

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        d = ctx.daily
        result = StrategyResult(entry_setup_codes=(BO01, BO02))
        close, atr14 = ctx.close, ctx.atr
        high_252 = d["high_252"].iloc[-1]

        # B1-B2: the Near-highs screen's H1 (above the 200-day) and H2 (200-day not falling);
        # B3 below is this strategy's own, tighter, near-the-high rule
        self.apply_screen(ctx, result)

        # B3: at or near the highs — breakouts are bought at highs, not mid-range
        if pd.isna(high_252):
            result.fail("B3", "insufficient history for 52-week high")
        elif close >= high_252 * 0.95:
            result.ok("B3")
        else:
            result.fail("B3", "more than 5% below the 52-week high")

        # B4: a real consolidation preceded this — the prior N bars were tight
        prior = d.iloc[-(CONSOLIDATION_BARS + 1) : -1]
        if len(prior) < CONSOLIDATION_BARS or pd.isna(atr14) or not atr14:
            result.fail("B4", "insufficient bars to measure the consolidation")
        else:
            rng = float(prior["high"].max() - prior["low"].min())
            if rng <= 6 * atr14:
                result.ok("B4", f"{CONSOLIDATION_BARS}-bar range {rng / atr14:.1f} ATR")
            else:
                result.fail("B4", f"pre-breakout range {rng / atr14:.1f} ATR > 6 ATR (no tight base)")

        # B5: not already extended beyond a sane entry
        sma20 = d["sma20"].iloc[-1]
        if pd.notna(sma20) and pd.notna(atr14) and atr14 and (close - sma20) > 4 * atr14:
            result.fail("B5", "more than 4 ATR above SMA20")
        else:
            result.ok("B5")

        # B6: volatility sane
        atr_pct = d["atr_pct"].iloc[-1]
        if pd.notna(atr_pct) and atr_pct > 8:
            result.fail("B6", f"ATR% {atr_pct:.1f} > 8%")
        else:
            result.ok("B6")

        # B7: earnings not imminent
        if ctx.earnings_days_away is not None and ctx.earnings_days_away <= 10:
            result.fail("B7", f"earnings in {ctx.earnings_days_away} trading days")
        else:
            result.ok("B7")

        self._compute_setups(ctx, result)
        result.recompute_first_fail()
        self._compute_watch_flags(ctx, result)
        return result

    def _compute_setups(self, ctx: StockContext, result: StrategyResult) -> None:
        d = ctx.daily
        close = ctx.close
        pivot = float(d["high"].iloc[-(BREAKOUT_LOOKBACK + 1) : -1].max())
        vol = float(d["volume"].iloc[-1])
        vol_sma50 = d["vol_sma50"].iloc[-1]
        vol_ok = pd.notna(vol_sma50) and vol_sma50 and vol > 1.5 * vol_sma50

        # BO-01: closed above the pivot today, on expanding volume
        result.setups[BO01] = bool(close > pivot and vol_ok)
        # BO-02: coiled just under the pivot, not through it yet
        result.setups[BO02] = bool(pivot * 0.97 <= close <= pivot)
        ctx.extras["breakout_pivot"] = pivot

    def _compute_watch_flags(self, ctx: StockContext, result: StrategyResult) -> None:
        d = ctx.daily
        close, atr14 = ctx.close, ctx.atr
        sma20 = d["sma20"].iloc[-1]
        rsi14 = d["rsi14"].iloc[-1]
        vol_sma50 = d["vol_sma50"].iloc[-1]

        # XB1: extended from the mean — breakout already ran
        result.watch_flags["XB1"] = bool(
            pd.notna(sma20) and pd.notna(atr14) and atr14 and (close - sma20) > 2.5 * atr14
        )
        if result.watch_flags["XB1"]:
            result.watch_notes["XB1"] = f"extended; pullback target ~{sma20:.2f}"

        # XB2: breakout without volume confirmation — the classic failure mode
        vol = float(d["volume"].iloc[-1])
        thin = pd.notna(vol_sma50) and vol_sma50 and vol < vol_sma50
        result.watch_flags["XB2"] = bool(thin and result.setups.get(BO01))
        if result.watch_flags["XB2"]:
            result.watch_notes["XB2"] = "breakout on below-average volume"

        # XB3: overbought
        result.watch_flags["XB3"] = bool(pd.notna(rsi14) and rsi14 > 80)

    def watch_cap(self, result: StrategyResult) -> str:
        caps = []
        if result.watch_flags.get("XB1"):
            caps.append("TRADE_ON_TRIGGER")
        if result.watch_flags.get("XB2"):
            caps.append("WATCH_WAIT")
        if result.watch_flags.get("XB3"):
            caps.append("TRADE_ON_TRIGGER")
        return min(caps, key=CAP_ORDER.index) if caps else "TRADE_HIGH_CONFIDENCE"

    def setup_quality(self, result: StrategyResult) -> float:
        score = 2.0 if result.setups.get(BO01) else (1.0 if result.setups.get(BO02) else 0.0)
        if result.watch_flags.get("XB2"):
            score -= 1.0
        if result.watch_flags.get("XB1"):
            score -= 0.5
        return score

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        """For a breakout the signal IS the setup: BO-01 means today's close
        already cleared the pivot on volume."""
        return bool(result.setups.get(BO01))

    def build_plans(
        self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig
    ) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no active setup")

        d = ctx.daily
        atr14 = ctx.atr
        pivot = ctx.extras.get("breakout_pivot")
        if pivot is None or pd.isna(atr14) or not atr14:
            return PlanChoice(None, None, "missing pivot/ATR")

        setup = BO01 if result.setups.get(BO01) else BO02
        trigger = max(float(d["high"].iloc[-1]), pivot)
        entry = round_tick(trigger * 1.001, cfg.tick_size, "up")

        # stop below the consolidation, but never wider than 2 ATR
        base_low = float(d["low"].iloc[-(CONSOLIDATION_BARS + 1) : -1].min())
        stop = round_tick(max(base_low - 0.1 * atr14, entry - 2 * atr14), cfg.tick_size, "down")

        risk = entry - stop
        # Measured move: project the consolidation height off the pivot.
        #
        # The 2.5R floor below is an ASSUMPTION, not a measurement. Whenever the
        # base is shorter than 2.5R the floor binds and every candidate reports
        # "2.50R" — which looks like an assessment of opportunity but is the
        # formula restating itself. Both numbers are kept so a reader can tell
        # which one is real: `structural_r` is what the chart actually offers.
        base_high = float(d["high"].iloc[-(CONSOLIDATION_BARS + 1) : -1].max())
        measured_move = base_high - base_low
        structural_r = measured_move / risk if risk > 0 else float("nan")
        # The target is the measured move, full stop. A floor (this previously
        # used max(measured_move, 2.5 * risk)) reports reward the chart does
        # not offer: 12 of 14 live candidates showed "2.50R" while projecting
        # 1.40-2.38R. Setups that project less than `min_structural_r` are
        # rejected in classify() rather than padded up to look acceptable.
        target = entry + measured_move
        ctx.extras["structural_r"] = structural_r

        nearest_above = sw.nearest_overhead_above(entry, ctx.overhead)
        if nearest_above is not None and nearest_above < target:
            target = nearest_above

        r_multiple = (target - entry) / risk if risk > 0 else float("nan")
        plan = TradePlan(
            plan="BO", setup=setup, entry=entry, stop=stop, target=target,
            risk_per_share=risk, reward_per_share=target - entry,
            r_multiple=r_multiple, nearest_overhead_above_entry=nearest_above,
        )
        return PlanChoice(plan, None, f"{setup} breakout above {pivot:.2f}")

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
            return Decision(
                "AVOID", "AVOID",
                f"fails hard gate {code}: {result.hard_notes.get(code, '')}",
                float("nan"), float("nan"), 0.0,
            )

        if not plan.is_valid:
            return Decision(
                "AVOID", "AVOID", "degenerate plan (non-positive or undefined risk)",
                float("nan"), float("nan"), 0.0,
            )

        risk_pct = plan.risk_per_share / plan.entry * 100
        r_mult = plan.r_multiple
        cap = self.watch_cap(result)
        fired = self.entry_signal_fired(ctx, result)
        earnings_block = earnings_days_away is not None and earnings_days_away <= 15
        reasons: list[str] = []

        if sizing_result.too_large:
            label = "WATCH_WAIT"
            reasons.append("too large for account")
        elif risk_pct > 8 or r_mult < self.min_structural_r:
            label = "WATCH_WAIT"
            if risk_pct > 8:
                reasons.append(f"stop {risk_pct:.1f}% > 8%")
            if r_mult < self.min_structural_r:
                reasons.append(
                    f"base projects {r_mult:.2f}R < {self.min_structural_r:g}R "
                    "— not enough reward for the risk"
                )
        elif cap == "WATCH_WAIT":
            label = "WATCH_WAIT"
            reasons.append(result.watch_notes.get("XB2", "capped by watch flag"))
        elif fired and cap == "TRADE_HIGH_CONFIDENCE" and risk_pct <= 7 and r_mult >= 2 and not earnings_block:
            label = "TRADE_HIGH_CONFIDENCE"
            reasons.append(f"{plan.setup} fired on volume, {r_mult:.2f}R")
        else:
            label = "TRADE_ON_TRIGGER"
            if not fired:
                reasons.append("coiled under the pivot, breakout not yet confirmed")
            if cap == "TRADE_ON_TRIGGER":
                active = [c for c in ("XB1", "XB3") if result.watch_flags.get(c)]
                reasons.append(f"capped by watch flag ({'/'.join(active)})")
            if earnings_block:
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
        pivot = ctx.extras.get("breakout_pivot")
        sr = ctx.extras.get("structural_r")
        return {
            "breakout_pivot": round(pivot, 2) if pivot else None,
            "pct_from_pivot": round((ctx.close / pivot - 1) * 100, 2) if pivot else None,
            # what the base projects — now identical to target_r, kept because
            # it names the thing explicitly
            "structural_r": round(sr, 2) if isinstance(sr, float) and sr == sr else None,
        }

    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The 55-day-high pivot the breakout had to clear, plus the shared default (resistance,
        swing low, setup note). The consolidation itself has no stored geometry, so the pivot and
        the note carry the story."""
        e = sig.get("extras") or {}
        d = str(sig["date"])
        out = super().chart_anatomy(sig)
        if e.get("breakout_pivot"):
            out.append({"shape": "level", "bars": 55, "to": d, "price": float(e["breakout_pivot"]),
                        "role": "pivot", "label": f"pivot {e['breakout_pivot']:g} — highest high of the last 55 days"})
            out.append({"shape": "note", "at": d, "price": float(e["breakout_pivot"]),
                        "text": f"BO setup {d}: new 55-day high out of a tight consolidation; the trigger needs "
                                f"expanding volume. Structural R {e.get('structural_r', '?')} (what the base projects)."})
        return out
