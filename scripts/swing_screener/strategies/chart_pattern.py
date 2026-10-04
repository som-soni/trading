"""Classical chart patterns — the bases that precede a breakout.

Where `breakout` buys any 55-day high out of a tight 20-bar range, this
strategy insists the consolidation have a RECOGNISED SHAPE: a cup-and-handle,
a double bottom, a flat base, a bull flag, an ascending triangle, or a
volatility-contraction pattern. The geometry lives in
`core/chart_patterns.py`; this file only decides what is tradeable.

Thesis
------
A base's shape carries information its range does not. O'Neil's claim is that
a rounded 12-33% correction that recovers to its rim and then drifts on dry
volume has shaken out supply, so the subsequent break of the rim meets little
resistance — whereas an equally tight range that formed through choppy,
high-volume churn has not. Minervini's VCP makes the same argument about a
sequence of successively shallower pullbacks.

The honest counter-argument is that pattern recognition is the most
over-claimed idea in technical analysis, that published tests of it are
mostly weak or unreplicated, and that any detector is one particular reading
of an informally-defined shape. Which is exactly why the geometry is
separable and the thresholds are the conventional published ones rather than
numbers fitted here: you can backtest this against `breakout` and find out
whether shape adds anything over "tight range near highs".

What it shares with the other strategies
----------------------------------------
Entry geometry is uniform across all six patterns — buy a tick through the
pivot, stop under the structural low the pattern names, target the measured
move, reject anything projecting under 2R. Only the pivot/stop/measured-move
differ by pattern, and those come from the detector.
"""

import pandas as pd

from ..config.base import MarketConfig
from ..core import chart_patterns as cp
from ..core import indicators as ind
from ..core import swings as sw
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

# How close to the pivot price must already be for a detected pattern to
# count as a SETUP. A perfect cup whose pivot is 20% overhead is a fact about
# the chart, not a trade — it is reported, but it is not actionable.
NEAR_PIVOT_PCT = 0.08
# How far above the pivot price may be and still be entered. Past this the
# breakout has happened without you; chasing it is a different (worse) trade.
MAX_CHASE_PCT = 0.04
# Volume multiple that counts as confirmation of a breakout.
VOL_CONFIRM = 1.4


class ChartPatternStrategy(Strategy):
    key = "chart_pattern"
    name = "Classical chart-pattern breakout"
    description = (
        "Breakouts from a named base — cup-and-handle, double bottom, flat "
        "base, bull flag, ascending triangle, or VCP."
    )
    gate_codes = ("P1", "P2", "P3", "P4", "P5", "P6", "P7")
    watch_codes = ("XP1", "XP2", "XP3", "XP4")
    setup_codes = cp.ALL_CODES
    min_bars = cp.MIN_BARS

    needs_ctx_extras = True
    extra_columns = (
        "pattern", "patterns_seen", "pattern_pivot", "pct_from_pivot",
        "pattern_depth_pct", "pattern_length", "pattern_quality",
        "structural_r", "pattern_note",
    )
    extra_numeric_columns = (
        "pattern_pivot", "pct_from_pivot", "pattern_depth_pct",
        "pattern_length", "pattern_quality", "structural_r",
    )

    # A pattern scoring below this is a loose resemblance, not an example.
    min_quality: float = 0.45
    # Minimum reward the pattern's own measured move must project. Nothing is
    # padded up to it — setups projecting less are rejected.
    min_structural_r: float = 2.0
    max_depth_pct: float = 35.0  # deeper than this is noted, not rejected
    # How far above the entry still counts as the base's OWN resistance zone
    # rather than new overhead supply. A base's ceiling is not a line: a
    # cup's two rims, a triangle's three touches and a box top all print at
    # slightly different prices, spread over roughly an ATR.
    overhead_cluster_atr: float = 1.0

    thesis = (
        "A base with a recognised shape — rounded cup, matched double bottom, "
        "tightening contractions — has absorbed supply in a way a merely "
        "narrow range has not, so its breakout meets less resistance."
    )
    how_it_works = (
        "**Screen** for liquid stocks above their SMA200 and within 20% of the "
        "52-week high, with enough history for a long base.",
        "**Detect** all six patterns geometrically (see `core/chart_patterns.py`); "
        "each returns a pivot, the structural low a stop belongs under, and the "
        "measured move it projects. Pivots are computed from bars BEFORE the "
        "current one, so a breakout bar can never define the level it breaks.",
        f"**Setups** fire per pattern once price is within {NEAR_PIVOT_PCT * 100:.0f}% "
        "below the pivot; several patterns may match one chart and all are reported.",
        "**Gates P1-P7** require the SMA200 intact and not falling, price within "
        "15% of the 52-week high, sane volatility, no earnings inside 10 days, a "
        f"pattern scoring at least {min_quality:g}, and price no more than "
        f"{MAX_CHASE_PCT * 100:.0f}% above the pivot.",
        "**Entry** a tick through the pivot, or the market price if price has "
        "already cleared it. **Stop** under the pattern's own structural low "
        "(handle low, second bottom, box low, flag low), never wider than 2 "
        "ATR. **Target** the measured move, capped at overhead supply more "
        "than 1 ATR above the entry — nearer levels are the base's own "
        "resistance zone, not new supply.",
        "**Confirmation**: the trigger is a close through the pivot on "
        f"{VOL_CONFIRM:g}x average volume; without the volume it is still a "
        "setup, capped at WATCH.",
    )
    caveats = (
        "**NOT BACKTESTED.** No pattern here has been run through the "
        "backtester, and the thresholds are the conventional published ones "
        "(O'Neil, Darvas, Minervini), not numbers fitted to this data.",
        "Pattern recognition is the most over-claimed idea in technical "
        "analysis. The first thing to test is whether this beats `breakout`, "
        "which needs no shape at all — if it does not, the shape is decoration.",
        "Any detector is one reading of an informally-defined shape. A chart a "
        "human would call a cup may score 0.3 here, and vice versa. Read "
        "`pattern_note` before trusting `pattern_quality`.",
        "Flat bases and flags project their PRIOR ADVANCE as the measured move, "
        "not the base height (a 10% box cannot project 2R off a stop under its "
        "own low). That is the most aggressive assumption in the file.",
        "Several patterns usually match one chart (a VCP is often also a cup "
        "or a flat base). The traded one is whichever scores highest among "
        "those near their pivot; `patterns_seen` lists the rest. Do not read "
        "a long `patterns_seen` as corroboration — the detectors are not "
        "independent.",
    )

    # ---------- screen ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        if cfg.screener.min_price and last["close"] < cfg.screener.min_price:
            return False, f"price {last['close']:.2f} < {cfg.screener.min_price}"
        if pd.isna(last["sma200"]) or last["close"] <= last["sma200"]:
            return False, "close <= SMA200"
        if cfg.screener.min_dollar_volume:
            dv = last.get("dollar_vol_sma20")
            if pd.isna(dv) or dv < cfg.screener.min_dollar_volume:
                return False, f"liquidity below {cfg.screener.min_dollar_volume:,.0f}"
        if pd.isna(last["atr14"]) or not last["atr14"]:
            return False, "no ATR"
        if pd.isna(last["high_252"]) or last["close"] < last["high_252"] * 0.80:
            return False, "more than 20% below the 52-week high"
        return True, "passed"

    # ---------- gates + detection ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        d = ctx.daily
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        close, atr14 = ctx.close, ctx.atr

        matches = cp.detect_patterns(d)
        # The traded pattern is the best-scoring one that is also actionable
        # (price already near its pivot); a higher-scoring pattern whose pivot
        # is far overhead is reported but not traded.
        actionable = [
            m for m in matches
            if close >= m.pivot * (1 - NEAR_PIVOT_PCT) and m.quality >= self.min_quality
        ]
        best = actionable[0] if actionable else (matches[0] if matches else None)

        for code in self.setup_codes:
            result.setups[code] = any(m.code == code for m in actionable)

        # Always written, even with nothing found: the backtest's signal cache
        # treats an empty `extras` as a miss for a strategy that reads them
        # (see backtest._load_cached_signal), so a symbol-day with no pattern
        # would otherwise be recomputed from scratch on every run forever.
        ctx.extras["patterns_seen"] = ",".join(m.code for m in matches)
        if best is not None:
            ctx.extras.update({
                "pattern": best.code,
                "pattern_pivot": float(best.pivot),
                "pattern_stop": float(best.stop_ref),
                "pattern_move": float(best.measured_move),
                "pattern_depth_pct": float(best.depth_pct),
                "pattern_length": int(best.length_bars),
                "pattern_quality": round(float(best.quality), 3),
                "pattern_note": best.note,
                "pattern_actionable": bool(actionable),
            })

        sma200 = d["sma200"].iloc[-1]
        high_252 = d["high_252"].iloc[-1]

        # P1: long-term structure intact. Every pattern here is a
        # CONTINUATION setup; the same shapes below a falling SMA200 are
        # bear-market rallies.
        if pd.isna(sma200) or close <= sma200:
            result.fail("P1", "close at/below SMA200")
        else:
            result.ok("P1")

        # P2: SMA200 not falling
        state = ind.slope_state(d["sma200"], 20, 0.5)
        if state == "falling":
            result.fail("P2", "SMA200 falling")
        else:
            result.ok("P2", f"SMA200 {state}")

        # P3: near the highs. A base that completes 30% below the 52-week
        # high is a recovery attempt, not a breakout.
        if pd.isna(high_252):
            result.fail("P3", "insufficient history for the 52-week high")
        elif close >= high_252 * 0.85:
            result.ok("P3")
        else:
            result.fail("P3", "more than 15% below the 52-week high")

        # P4: volatility sane
        atr_pct = d["atr_pct"].iloc[-1]
        if pd.notna(atr_pct) and atr_pct > 10:
            result.fail("P4", f"ATR% {atr_pct:.1f} > 10%")
        else:
            result.ok("P4")

        # P5: earnings not imminent — a base breaking out two days before a
        # print is a bet on the print, not on the base.
        if ctx.earnings_days_away is not None and ctx.earnings_days_away <= 10:
            result.fail("P5", f"earnings in {ctx.earnings_days_away} trading days")
        else:
            result.ok("P5")

        # P6: a recognisable, actionable pattern exists
        if not actionable:
            if best is None:
                result.fail("P6", "no pattern detected")
            elif best.quality < self.min_quality:
                result.fail(
                    "P6",
                    f"best pattern {best.code} scores {best.quality:.2f} "
                    f"< {self.min_quality:g}",
                )
            else:
                result.fail(
                    "P6",
                    f"{best.code} pivot {best.pivot:.2f} is "
                    f"{(best.pivot / close - 1) * 100:.1f}% overhead",
                )
        else:
            result.ok("P6", f"{best.code}: {best.note}")

        # P7: not already extended beyond a sane entry
        if actionable and close > best.pivot * (1 + MAX_CHASE_PCT):
            result.fail(
                "P7",
                f"{(close / best.pivot - 1) * 100:.1f}% above the pivot "
                f"(> {MAX_CHASE_PCT * 100:.0f}%)",
            )
        else:
            result.ok("P7")

        result.recompute_first_fail()
        self._watch_flags(ctx, result, best, atr14)
        return result

    def _watch_flags(self, ctx, result, best, atr14) -> None:
        d = ctx.daily
        close = ctx.close
        sma20 = d["sma20"].iloc[-1]
        rsi14 = d["rsi14"].iloc[-1]
        vol = float(d["volume"].iloc[-1])
        vol_sma50 = d["vol_sma50"].iloc[-1]
        through = best is not None and close > best.pivot

        # XP1: through the pivot without volume — the classic failed breakout.
        # Only meaningful once price is actually through: a coiling base is
        # SUPPOSED to be quiet.
        thin = pd.notna(vol_sma50) and vol_sma50 and vol < VOL_CONFIRM * vol_sma50
        result.watch_flags["XP1"] = bool(through and thin)
        if result.watch_flags["XP1"]:
            result.watch_notes["XP1"] = (
                f"through the pivot on {vol / vol_sma50:.2f}x volume "
                f"(want {VOL_CONFIRM:g}x)"
            )

        # XP2: extended from the mean
        result.watch_flags["XP2"] = bool(
            pd.notna(sma20) and pd.notna(atr14) and atr14
            and (close - sma20) > 2.5 * atr14
        )
        if result.watch_flags["XP2"]:
            result.watch_notes["XP2"] = f"extended; pullback target ~{sma20:.2f}"

        # XP3: overbought
        result.watch_flags["XP3"] = bool(pd.notna(rsi14) and rsi14 > 80)
        if result.watch_flags["XP3"]:
            result.watch_notes["XP3"] = f"RSI14 {rsi14:.0f} > 80"

        # XP4: a deep base. Not disqualifying — O'Neil's cups run to 33% and
        # bear-market bases deeper still — but a deep base is a damaged one.
        deep = best is not None and best.depth_pct > self.max_depth_pct
        result.watch_flags["XP4"] = bool(deep)
        if deep:
            result.watch_notes["XP4"] = (
                f"{best.code} is {best.depth_pct:.0f}% deep "
                f"(> {self.max_depth_pct:g}%)"
            )

    def watch_cap(self, result: StrategyResult) -> str:
        caps = []
        if result.watch_flags.get("XP1"):
            caps.append("WATCH_WAIT")
        for code in ("XP2", "XP3", "XP4"):
            if result.watch_flags.get(code):
                caps.append("TRADE_ON_TRIGGER")
        return min(caps, key=CAP_ORDER.index) if caps else "TRADE_HIGH_CONFIDENCE"

    def setup_quality(
        self, result: StrategyResult, geometric: float | None = None
    ) -> float:
        """Ranking score, 0-2 to match the other strategies.

        `geometric` is the detector's own 0-1 quality score, which lives on
        `ctx.extras` rather than on StrategyResult — classify() passes it;
        callers that only hold a result get the flag-penalty version, which
        still orders a clean setup above a flagged one.
        """
        if not any(result.setups.get(code) for code in self.setup_codes):
            return 0.0
        score = 2.0 * geometric if geometric is not None else 2.0
        if result.watch_flags.get("XP1"):
            score -= 1.0
        if result.watch_flags.get("XP2"):
            score -= 0.5
        if result.watch_flags.get("XP4"):
            score -= 0.25
        return score

    # ---------- entry ----------

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        """A close through the pivot on confirming volume. Unlike `breakout`
        and `donchian`, the setup and the trigger are separate here: a base
        can be complete and actionable for weeks before it breaks."""
        pivot = ctx.extras.get("pattern_pivot")
        if not pivot or not result.has_setup:
            return False
        if ctx.close <= float(pivot):
            return False
        vol_sma50 = ctx.daily["vol_sma50"].iloc[-1]
        vol = float(ctx.daily["volume"].iloc[-1])
        if pd.isna(vol_sma50) or not vol_sma50:
            return False
        return bool(vol >= VOL_CONFIRM * float(vol_sma50))

    def build_plans(
        self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig
    ) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no active setup")
        atr14 = ctx.atr
        pivot = ctx.extras.get("pattern_pivot")
        stop_ref = ctx.extras.get("pattern_stop")
        move = ctx.extras.get("pattern_move")
        code = ctx.extras.get("pattern")
        if pivot is None or stop_ref is None or move is None or pd.isna(atr14) or not atr14:
            return PlanChoice(None, None, "missing pattern geometry/ATR")

        pivot, stop_ref, move = float(pivot), float(stop_ref), float(move)
        # A tick through the pivot while price is still under it — that is
        # where a resting buy-stop fills. Once price has ALREADY cleared the
        # pivot (gate P7 allows up to 4% past it) there is no buy-stop to
        # rest: you pay the market. Quoting the pivot anyway understates both
        # the risk and the R of a breakout you are chasing.
        entry = round_tick(max(pivot * 1.001, ctx.close), cfg.tick_size, "up")
        # Under the structural low the pattern itself names — but never wider
        # than 2 ATR, because a 25% stop under a deep cup's handle is not a
        # position anyone can size.
        stop = round_tick(
            max(stop_ref - 0.1 * atr14, entry - 2 * atr14), cfg.tick_size, "down"
        )
        risk = entry - stop
        if risk <= 0:
            return PlanChoice(None, None, "degenerate stop (pivot at/below the base low)")

        # The measured move, with no floor: `structural_r` is what the chart
        # offers, and classify() rejects anything under min_structural_r
        # rather than padding the target up to look acceptable.
        target = entry + move
        structural_r = move / risk
        nearest_above = sw.nearest_overhead_above(entry, ctx.overhead)
        # Overhead supply caps the target — but NOT the levels that form the
        # pivot itself. The base's resistance is a cluster of swing highs
        # within a hair of the entry by construction, so capping there says
        # "this breakout cannot travel past the level it is breaking", which
        # is incoherent. Measured on 400 US symbols, the uncorrected version
        # collapsed 20 of 25 targets below 0.5R and rejected them for a
        # reason that was an artefact of the entry's own definition.
        cluster_edge = entry + self.overhead_cluster_atr * atr14
        binding = min(
            (lvl for lvl in ctx.overhead if lvl >= cluster_edge), default=None
        )
        if binding is not None and binding < target:
            target = binding
        ctx.extras["structural_r"] = round(structural_r, 3)
        ctx.extras["overhead_caps_target"] = bool(
            binding is not None and binding < entry + move
        )

        plan = TradePlan(
            plan="CP", setup=code or "CP", entry=entry, stop=stop, target=target,
            risk_per_share=risk, reward_per_share=target - entry,
            r_multiple=(target - entry) / risk,
            nearest_overhead_above_entry=nearest_above,
        )
        return PlanChoice(
            plan, None,
            f"{cp.PATTERN_NAMES.get(code, code)} pivot {pivot:.2f}",
        )

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
        quality = ctx.extras.get("pattern_quality")
        quality = float(quality) if isinstance(quality, (int, float)) else None
        reasons: list[str] = []

        if sizing_result.too_large:
            label = "WATCH_WAIT"
            reasons.append("too large for account")
        elif risk_pct > 8 or r_mult < self.min_structural_r:
            label = "WATCH_WAIT"
            if risk_pct > 8:
                reasons.append(f"stop {risk_pct:.1f}% > 8%")
            if r_mult < self.min_structural_r:
                capped = ctx.extras.get("overhead_caps_target")
                structural = ctx.extras.get("structural_r")
                reasons.append(
                    f"{plan.setup} projects {r_mult:.2f}R < "
                    f"{self.min_structural_r:g}R — not enough reward for the risk"
                    + (
                        f" (the measured move is {structural:.2f}R; overhead at "
                        f"{plan.target:.2f} caps it)"
                        if capped and isinstance(structural, (int, float))
                        else ""
                    )
                )
        elif cap == "WATCH_WAIT":
            label = "WATCH_WAIT"
            reasons.append(result.watch_notes.get("XP1", "capped by watch flag"))
        elif fired and cap == "TRADE_HIGH_CONFIDENCE":
            label = "TRADE_HIGH_CONFIDENCE"
            reasons.append(
                f"{plan.setup} broke its pivot on volume, {r_mult:.2f}R"
                + (f", quality {quality:.2f}" if quality is not None else "")
            )
        else:
            label = "TRADE_ON_TRIGGER"
            if not fired:
                reasons.append(
                    f"{plan.setup} complete, waiting for a close through "
                    f"{plan.entry:.2f} on volume"
                )
            if cap == "TRADE_ON_TRIGGER":
                active = [c for c in ("XP2", "XP3", "XP4") if result.watch_flags.get(c)]
                reasons.append(f"capped by watch flag ({'/'.join(active)})")

        before = label
        if regime_downgrade_active and label != "AVOID":
            label = DOWNGRADE_MAP[label]
            reasons.append("market-regime downgrade applied")

        return Decision(
            label_before=LABELS[before],
            label_after=LABELS[label],
            reason="; ".join(reasons),
            risk_pct=risk_pct,
            r_multiple=r_mult,
            setup_quality=self.setup_quality(result, geometric=quality),
        )

    def report_extras(
        self, ctx: StockContext, result: StrategyResult, plan: TradePlan | None
    ) -> dict:
        e = ctx.extras
        pivot = e.get("pattern_pivot")
        sr = e.get("structural_r")
        return {
            "pattern": e.get("pattern"),
            "patterns_seen": e.get("patterns_seen"),
            "pattern_pivot": round(float(pivot), 2) if pivot else None,
            "pct_from_pivot": round((ctx.close / float(pivot) - 1) * 100, 2) if pivot else None,
            "pattern_depth_pct": round(float(e["pattern_depth_pct"]), 1)
            if e.get("pattern_depth_pct") is not None else None,
            "pattern_length": e.get("pattern_length"),
            "pattern_quality": e.get("pattern_quality"),
            "structural_r": round(float(sr), 2) if sr is not None else None,
            "pattern_note": e.get("pattern_note"),
        }
