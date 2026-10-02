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

from .. import indicators as ind
from .. import swings as sw
from ..config.base import MarketConfig
from ..context import StockContext
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
    key = "breakout"
    name = "Volume-confirmed breakout"
    description = (
        "Long breakouts to new 55-day highs out of a tight consolidation, "
        "confirmed by expanding volume."
    )
    gate_codes = ("B1", "B2", "B3", "B4", "B5", "B6", "B7")
    watch_codes = ("XB1", "XB2", "XB3")
    setup_codes = (BO01, BO02)
    min_bars = 260

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
        sma50 = d["sma50"].iloc[-1]
        sma200 = d["sma200"].iloc[-1]
        high_252 = d["high_252"].iloc[-1]

        # B1: long-term structure intact
        if pd.isna(sma200) or close <= sma200:
            result.fail("B1", "close at/below SMA200")
        else:
            result.ok("B1")

        # B2: SMA200 not falling — a breakout inside a long-term downtrend
        # is a different (and worse) trade than one inside an uptrend
        sma200_state = ind.slope_state(d["sma200"], 20, 0.5)
        if sma200_state == "falling":
            result.fail("B2", "SMA200 falling")
        else:
            result.ok("B2", f"SMA200 {sma200_state}")

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
        # measured move: project the consolidation height off the pivot
        base_high = float(d["high"].iloc[-(CONSOLIDATION_BARS + 1) : -1].max())
        target = entry + max(base_high - base_low, 2.5 * risk)

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
        elif risk_pct > 8 or r_mult < 2:
            label = "WATCH_WAIT"
            if risk_pct > 8:
                reasons.append(f"stop {risk_pct:.1f}% > 8%")
            if r_mult < 2:
                reasons.append(f"target {r_mult:.2f}R < 2R")
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
        return {
            "breakout_pivot": round(pivot, 2) if pivot else None,
            "pct_from_pivot": round((ctx.close / pivot - 1) * 100, 2) if pivot else None,
        }
