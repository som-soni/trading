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

The first such test has been run, and it went badly: on US data from 2020 the
strategy returned -3.26% CAGR while the benchmark made +13.63%, at a 19% win
rate and -0.214R per trade. See `caveats` below for the per-pattern split.
Nothing here should be traded on the strength of the idea alone.

What it shares with the other strategies
----------------------------------------
Entry geometry is uniform across all seven patterns — buy a tick through the
pivot, stop under the structural low the pattern names, target the measured
move, downgrade anything projecting under 2R to WATCH. Only the pivot/stop/measured-move
differ by pattern, and those come from the detector.
"""

import pandas as pd

from ..config.base import MarketConfig
from ..core import chart_patterns as cp
from ..core import swings as sw
from ..core.context import StockContext
from .base import (
    tradable_point_in_time,
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
    selection = "time_series"
    family = "chart_pattern"
    version = "1.0"
    changelog = (
        ("1.0", "2026-10-07",
         "First implementation: seven detectors (cup, cup-no-handle, double bottom, flat base, bull flag, ascending triangle, VCP)."),
    )
    key = "chart_pattern_legacy"
    name = "Chart patterns (superseded)"
    description = (
        "Breakouts from a named base — cup-and-handle, double bottom, flat "
        "base, bull flag, ascending triangle, or VCP."
    )
    style = "breakout"
    gate_codes = ("P1", "P2", "P3", "P4", "P5", "P6", "P7")
    screen_key = "near_highs"
    screen_gates = {"P1": "H1", "P2": "H2", "P3": "H3"}
    watch_codes = ("XP1", "XP2", "XP3", "XP4", "XP5")
    # bullish bases only — a topping structure can never become a setup in a
    # long-only book; it enters through the XP5 veto instead
    setup_codes = cp.BULLISH_CODES
    # which detectors may produce a setup. Subclasses narrow this; see
    # ChartPatternCupStrategy for why that is worth doing.
    allowed_codes: tuple[str, ...] = cp.BULLISH_CODES
    min_bars = cp.MIN_BARS

    needs_ctx_extras = True
    extra_columns = (
        "pattern", "patterns_seen", "pattern_confidence", "pattern_pivot",
        "pct_from_pivot", "pattern_depth_pct", "pattern_length",
        "pattern_quality", "structural_r", "pattern_note", "pattern_flaws",
        "topping_pattern", "topping_note",
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
    # Floor on the stop distance. The 2 ATR clamp below only stops a stop
    # being too WIDE; nothing stopped one being absurdly TIGHT. TECH printed
    # a cup whose handle was 0.5% deep, which put the stop 0.40 below a 72.77
    # entry — inside the spread, certain to be taken out by noise — and the
    # measured move then divided by that to report "14.13R" and a TRADE ON
    # TRIGGER. `donchian` already floors its stop for the same reason.
    min_stop_atr: float = 0.6
    min_stop_pct: float = 1.5

    thesis = (
        "A base with a recognised shape — rounded cup, matched double bottom, "
        "tightening contractions — has absorbed supply in a way a merely "
        "narrow range has not, so its breakout meets less resistance."
    )
    how_it_works = (
        "**Screen** for liquid stocks above their SMA200 and within 20% of the "
        "52-week high, with enough history for a long base.",
        "**Detect** all seven patterns geometrically (see `core/chart_patterns.py`); "
        "each returns a pivot, the structural low a stop belongs under, and the "
        "measured move it projects. Pivots are computed from bars BEFORE the "
        "current one, so a breakout bar can never define the level it breaks.",
        f"**Setups** fire per pattern once price is within {NEAR_PIVOT_PCT * 100:.0f}% "
        f"below the pivot and the pattern scores at least {min_quality:g}; several "
        "patterns may match one chart and all are reported.",
        "**Gates P1-P7** require the SMA200 intact and not falling, price within "
        "15% of the 52-week high, sane volatility, no earnings inside 10 days, a "
        f"pattern scoring at least {min_quality:g}, and price no more than "
        f"{MAX_CHASE_PCT * 100:.0f}% above the pivot.",
        "**Entry** 0.1% above the pivot (rounded up to the tick), or the market "
        "price if price has already cleared it. **Stop** under the pattern's own structural low "
        "(handle low, second bottom, box low, flag low), never wider than 2 "
        f"ATR and never tighter than {min_stop_atr:g} ATR or "
        f"{min_stop_pct:g}% of price. **Target** the measured move, capped at overhead supply more "
        "than 1 ATR above the entry — nearer levels are the base's own "
        "resistance zone, not new supply. A plan projecting under 2R, or with a "
        "stop more than 8% below entry, is downgraded to WATCH rather than rejected. "
        "(The stop floor is applied after the 2 ATR cap, so on a very quiet stock "
        "the stop can end up wider than 2 ATR.)",
        "**Confirmation**: the trigger is a close through the pivot on "
        f"{VOL_CONFIRM:g}x average volume; without the volume it is still a "
        "setup, capped at WATCH.",
    )
    caveats = (
        "**RE-MEASURED 2026-10-09: -5.60% CAGR, 139 trades, -0.309R per trade "
        "(t = -1.90), profit factor 0.62.** The earlier -4.08% / -0.213R "
        "figures below came from a 4 October run; the data has since "
        "extended and the `near_highs` screen was formalised, so the "
        "baseline itself moved. Quote one vintage or the other, not a mix.",
        "**A DAY OF DETECTOR REFINEMENT MOVED EXPECTANCY BY 0.001R.** "
        "Tightening the handle, anchoring the cup to the prior peak, adding "
        "CUPNH and the XP5 topping veto took per-trade expectancy from -0.214R "
        "to -0.213R over the same window and sample (CAGR -3.26% to -4.08%, "
        "146 trades). Every change was individually defensible and a human "
        "chart review motivated most of them; together they bought nothing "
        "measurable. Assume the same of the next refinement.",
        "**BACKTESTED AND IT LOST MONEY.** US, 2020-01-02 to 2026-10-02, a "
        "300-symbol sample, bracket exit: -3.26% CAGR against the benchmark's "
        "+13.63% (excess -16.90%), -38.98% max drawdown, 140 trades at a 19.0% "
        "win rate, -0.214R per trade, profit factor 0.75. Per pattern, total R "
        "was FLAT -11.9 (57 trades), DBOT -7.5 (13), ATRI -4.7 (34), CUP -3.0 "
        "(3), FLAG +0.1 (26), VCP +2.4 (7) — nothing with a meaningful sample "
        "made money. 111 trades stopped out against 26 that reached a target.",
        "**Three quarters of random walks contain one of these patterns.** "
        "Measured over 150 seeded walks: VCP 44%, FLAT 31%, DBOT 31%, FLAG "
        "11%, ATRI 9%, CUP 0.7%; 75% match something. Against 519 liquid US "
        "names the same day: VCP 27%, DBOT 27%, FLAT 11%, CUP 0.2%, 55% "
        "overall. Three of the seven detect noise about as readily as they "
        "detect the market, and they are exactly the ones the backtest traded "
        "most (FLAT 57 trades, ATRI 34). CUP is the only one whose match is "
        "rare in both columns. `tests/test_chart_patterns.py` holds the "
        "measurement and fails if any detector drifts looser.",
        "**The CUP numbers above are STALE.** A manual chart review after that "
        "backtest found the handle test was accepting things no one would call "
        "a handle — a 6-bar 8.5% rejection at the rim on rising volume "
        "(META), 37-38 bar drifts (EHC, EMBJ), a 0.5%-deep flat pause (TECH). "
        "The handle now has to be 5-20 bars, 2-15% deep, drifting at under "
        "1.2%/bar, on volume below the cup's. That cut a live scan from 76 "
        "cup matches to a handful, so CUP's 3 backtest trades were taken under "
        "a definition that no longer exists. Re-run before quoting them. The "
        "other five patterns are untouched.",
        "**The exit is not what is wrong.** All eight exit policies were run "
        "over that identical 193-signal set: the best (a 20-day Donchian exit, "
        "no target) reached +0.27% CAGR and a 5 ATR trail 0.00%, against "
        "-3.26% for the bracket. So the exit costs about three points of CAGR, "
        "and none of the 13-17 point shortfall against the benchmark. The "
        "entry carries no edge to protect.",
        "That result is the strategy's headline, not a footnote. It is one "
        "market and one window, so it does not prove the patterns carry no "
        "information — but anyone trading this off the screener is trading a "
        "measured loss. Re-measure before believing otherwise.",
        "Pattern recognition is the most over-claimed idea in technical "
        "analysis, and this is one reading of seven informally-defined shapes. "
        "The open question is whether shape adds anything over `breakout`, "
        "which needs no shape at all; on the evidence above the burden of "
        "proof sits with the shape.",
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

    # ---------- full reference documentation (the Strategy page) ----------
    status = (
        "Backtested and lost money: US 2020-2026, 300-symbol sample, bracket "
        "exit, -4.08% CAGR vs the benchmark's +13.63%, -0.213R per trade over "
        "146 trades. No demonstrated edge."
        " Measured before the 2026-10 cost fix (exit slippage was charged twice); re-measured runs moved by "
        "−0.8 to +0.9 points of CAGR (the extra cash changes which later signals are taken), so re-run before relying on it."
    )
    gate_docs = {
        "P1": "The close must be above the 200-day SMA. Every pattern here is a "
              "continuation base; the same shape under a broken long-term trend "
              "is treated as a bear-market rally.",
        "P2": "The 200-day SMA must not be falling, i.e. not more than 0.5% "
              "below its value 20 bars ago. Flat or rising both pass.",
        "P3": "The close must be at least 85% of the 52-week high (within 15% "
              "of it). Fails if there is not enough history to compute the high.",
        "P4": "ATR14 as a percentage of price must be 10% or less. A missing "
              "ATR% passes.",
        "P5": "No earnings report within the next 10 trading days. Passes when "
              "no earnings date is known, which is always the case in the "
              "backtest (there is no point-in-time earnings calendar).",
        "P6": "At least one of this strategy's allowed patterns must be detected "
              "with a quality score of at least 0.45 AND a close at or above "
              "pivot x (1 - {NEAR_PIVOT_PCT}). The failure note says whether "
              "nothing was found, the best match scored too low, or its pivot "
              "is too far overhead.",
        "P7": "The close must not be more than pivot x (1 + {MAX_CHASE_PCT}) — "
              "a breakout already further past its pivot than that is a chase, "
              "not an entry. Only checked when P6 found an actionable pattern.",
    }
    watch_docs = {
        "XP1": "Raised when the close is already above the traded pattern's "
               "pivot but volume is below {VOL_CONFIRM}x its 50-day average — "
               "the classic unconfirmed breakout. Caps the decision at WATCH "
               "and cuts the ranking score by 1.0.",
        "XP2": "Raised when the close is more than 2.5 ATR above the 20-day "
               "SMA (extended from the mean). Caps the decision at TRADE ON "
               "TRIGGER and cuts the ranking score by 0.5.",
        "XP3": "Raised when RSI14 is above 80 (overbought). Caps the decision "
               "at TRADE ON TRIGGER.",
        "XP4": "Raised when the traded pattern is more than 35% deep. Not "
               "disqualifying, but a deep base is a damaged one: caps the "
               "decision at TRADE ON TRIGGER and cuts the ranking score by 0.25.",
        "XP5": "Raised when a live topping structure (double top or head and "
               "shoulders top) is on the same chart — one whose last peak is "
               "under 90 bars old, has not been exceeded by more than 1%, and "
               "has either broken its neckline (confirmed) or rolled over below "
               "both 95% of the peak and the peak-to-neckline midpoint "
               "(forming). A confirmed top caps the decision at WATCH; a forming "
               "one at TRADE ON TRIGGER. It never creates or removes a setup.",
    }
    setup_docs = {
        "CUP": "Cup-and-handle. The left rim is the highest confirmed swing high "
               "of the last 250 bars; the cup bottom sits 12-50% below it, the "
               "right rim recovers to 90-105% of the left, the cup spans 25-250 "
               "bars with neither side shorter than 20% of it, and enough bars "
               "sit in its lower third to make it rounded rather than a V. The "
               "handle is the last 5-20 bars: 2-15% deep and no deeper than a "
               "third of the cup, its low in the cup's upper half, falling no "
               "faster than 1.2% per bar, on average volume below the cup's. "
               "Pivot: right rim. Stop: handle low. Move: cup depth.",
        "CUPNH": "Cup without a handle. The same cup body as CUP, but price is "
                 "still pinned to the rim: fewer than 5 bars since the right "
                 "rim or less than a 2% pullback from it, never more than 4% "
                 "off it, a close within 7% of it, and a right rim within 3% "
                 "of the left. Pivot: right rim. Stop: the lowest low since "
                 "about 5 bars before the rim. Move: cup depth.",
        "DBOT": "Double bottom (W). Two confirmed swing lows 15-160 bars apart "
                "within 5% of each other, with a rally of at least 8% between "
                "them, preceded by a high at least 15% above the lows in the 80 "
                "bars before the first. The second low must be at most 80 bars "
                "old and have held (nothing since more than 2% below it), and "
                "nothing since may have cleared the middle peak by more than "
                "3%. An undercutting second low scores higher. Pivot: highest "
                "high since the second low, at least the middle peak. Stop: "
                "second low. Move: middle peak minus the lower low.",
        "FLAT": "Flat base / Darvas box. A box of 25, 35, 45 or 65 bars ending "
                "yesterday whose high-to-low range is at most 15% deep, topping "
                "an advance of at least 20% from the lowest low of the 60 bars "
                "before it, with the close in the upper 60% of the box. Pivot: "
                "box high. Stop: box low. Move: the PRIOR ADVANCE (box high "
                "minus that pre-box low), not the box height.",
        "FLAG": "Bull flag. The pole high is the highest high of the last 45 "
                "bars, 4-35 bars ago; the pole rises at least 20% from the "
                "lowest low of the 40 bars before it; the flag since then has "
                "retraced no more than 40% of the pole. A gain of 80%+ with a "
                "retrace of 25% or less is labelled a high tight flag and "
                "scores higher. Pivot: pole high. Stop: flag low. Move: pole "
                "height.",
        "ATRI": "Ascending triangle. Within the last 120 bars, the three most "
                "recent confirmed swing highs all lie within 3% of the highest, "
                "the structure spans at least 25 bars, and the swing lows since "
                "it began rise (last more than 1% above first). The triangle is "
                "at least 6% tall at its left edge, the lows have closed 40-92% "
                "of that gap, and no high since the last touch is more than 3% "
                "above resistance. Pivot: resistance. Stop: last rising low. "
                "Move: triangle height.",
        "VCP": "Volatility contraction pattern. Within the last 140 bars, "
               "alternating confirmed swing highs and lows form pullbacks; the "
               "most recent run in which each pullback is at most 0.8x as deep "
               "as the one before must hold at least 2 contractions, the last "
               "no deeper than 12%. Pivot: the final contraction's high, or any "
               "higher high since. Stop: the final contraction's low. Move: "
               "first contraction's high minus the base low.",
    }
    entry_rules = (
        "A pattern is a setup once the close is at or above pivot x "
        "(1 - {NEAR_PIVOT_PCT}) and its quality score is at least 0.45. When "
        "several qualify, the highest-scoring one is traded. Pivots come only "
        "from bars before the current one.",
        "The trigger is a daily close above that pivot on volume of at least "
        "{VOL_CONFIRM}x the 50-day average. That close, with gates passed and "
        "no watch-flag cap, is TRADE HIGH CONFIDENCE. A setup that has not "
        "triggered yet is TRADE ON TRIGGER.",
        "Entry is the higher of pivot x 1.001 and the current close, rounded "
        "up to the tick. Once price has cleared the pivot, you pay the market "
        "price, not the pivot.",
        "Stop is 0.1 ATR under the pattern's structural low, but no more than "
        "2 ATR below entry. It is then widened if needed so it sits at least "
        "0.6 ATR and at least 1.5% below entry. It is rounded down to the "
        "tick.",
        "Target is entry plus the pattern's measured move, with no floor. It "
        "is capped at the nearest overhead swing-high level that is at least "
        "1 ATR above entry. Levels nearer than that are the base's own "
        "resistance zone and are ignored.",
        "A plan whose reward:risk is under 2R (after the overhead cap), whose "
        "stop is more than 8% below entry, or whose size is too large for the "
        "account is downgraded to WATCH. It is not padded up to look "
        "acceptable.",
    )
    exit_rules = (
        "A fixed bracket. The stop and target are set at entry and never move. "
        "The strategy has no trailing stop, time stop or discretionary exit.",
        "In the backtest, a TRADE HIGH CONFIDENCE signal becomes a resting "
        "buy-stop at the entry price. It fills on a later bar whose high "
        "reaches it, at the open if that bar gaps above. It is cancelled if "
        "the low reaches the stop first, if the open gaps past the target, or "
        "if it is still unfilled after 10 business days.",
        "A position exits on whichever of stop or target a later bar touches "
        "first. When both are touched on the same bar, the stop is assumed to "
        "fill. Gaps through either level fill at the open. Positions still "
        "open at the end are marked at the last close.",
        "Backtest only: the earnings gate (P5) and the market-regime downgrade "
        "are not applied, and only TRADE HIGH CONFIDENCE signals are taken.",
    )
    param_docs = (
        ("Near-pivot zone", "NEAR_PIVOT_PCT",
         "Fraction below the pivot within which a detected pattern counts as "
         "a setup ({NEAR_PIVOT_PCT}). Further out, it is reported but not "
         "actionable."),
        ("Max chase", "MAX_CHASE_PCT",
         "Fraction above the pivot beyond which gate P7 fails "
         "({MAX_CHASE_PCT})."),
        ("Breakout volume", "VOL_CONFIRM",
         "Multiple of 50-day average volume that a close through the pivot "
         "needs to count as the trigger ({VOL_CONFIRM}x). Below it, XP1 fires."),
        ("Minimum price", "cfg.screener.min_price",
         "Screen: closes below this price are excluded."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume",
         "Screen: the 20-day average of close x volume must reach this."),
        ("Tick size", "cfg.tick_size",
         "Entry is rounded up and the stop rounded down to this increment."),
        ("Risk per trade", "cfg.risk_pct",
         "Fraction of equity risked between entry and stop, which sets "
         "position size."),
        ("Max open positions", "cfg.max_open_positions",
         "Portfolio backtest slot limit. Triggered orders beyond it keep "
         "resting until they expire."),
    )
    backtest_args = ""

    # ---------- screen ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        ok, why = tradable_point_in_time(cfg, last)
        if not ok:
            return False, why
        if pd.isna(last["sma200"]) or last["close"] <= last["sma200"]:
            return False, "close <= SMA200"
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

        matches = [m for m in cp.detect_patterns(d) if m.code in self.allowed_codes]
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

        # A LIVE topping structure on the same chart — one that price has not
        # already taken out, whose neckline break has not failed, and which
        # has actually rolled over (see `_top_state`). It never creates or
        # blocks a setup; it caps confidence, because a breakout bought inside
        # a confirmed top is the trade this screener would otherwise keep
        # taking.
        top = next(iter(cp.detect_topping(d)), None)
        if top is not None:
            ctx.extras["topping_pattern"] = top.code
            ctx.extras["topping_note"] = top.note
            ctx.extras["topping_confirmed"] = top.note.startswith("confirmed")
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
                # how far the match sits from the textbook description, and
                # why — a `low` match is still reported, never silently
                # equated with a clean one
                "pattern_confidence": best.confidence,
                "pattern_flaws": best.flaw_text,
                "pattern_actionable": bool(actionable),
            })

        # P1-P3: the Near-highs screen's criteria H1-H3 (above a rising 200-day, within 15% of the high).
        # Every pattern here is a CONTINUATION setup; the same shapes below a falling SMA200 are
        # bear-market rallies, and a base 30% below the high is a recovery attempt, not a breakout.
        self.apply_screen(ctx, result)

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

        # XP5: a live topping structure on the same chart
        top_code = ctx.extras.get("topping_pattern")
        result.watch_flags["XP5"] = bool(top_code)
        if top_code:
            result.watch_notes["XP5"] = (
                f"{cp.PATTERN_NAMES.get(top_code, top_code)} on the same chart "
                f"— {ctx.extras.get('topping_note', '')}"
            )

    def watch_cap(self, result: StrategyResult) -> str:
        caps = []
        if result.watch_flags.get("XP1"):
            caps.append("WATCH_WAIT")
        for code in ("XP2", "XP3", "XP4"):
            if result.watch_flags.get(code):
                caps.append("TRADE_ON_TRIGGER")
        if result.watch_flags.get("XP5"):
            # a CONFIRMED top (price below the neckline) is the stronger
            # statement, so it caps harder than one still forming
            note = result.watch_notes.get("XP5", "")
            caps.append("WATCH_WAIT" if "confirmed" in note else "TRADE_ON_TRIGGER")
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
        # position anyone can size, and never tighter than the floor, because
        # a stop inside the daily noise is not a stop (see min_stop_atr).
        structural_stop = max(stop_ref - 0.1 * atr14, entry - 2 * atr14)
        floor_stop = min(
            entry - self.min_stop_atr * atr14,
            entry * (1 - self.min_stop_pct / 100),
        )
        stop = round_tick(min(structural_stop, floor_stop), cfg.tick_size, "down")
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
            reasons.append(
                result.watch_notes.get("XP5")
                if result.watch_flags.get("XP5") and "confirmed" in result.watch_notes.get("XP5", "")
                else result.watch_notes.get("XP1", "capped by watch flag")
            )
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
                active = [c for c in ("XP2", "XP3", "XP4", "XP5") if result.watch_flags.get(c)]
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
            "pattern_confidence": e.get("pattern_confidence"),
            "pattern_flaws": e.get("pattern_flaws"),
            "topping_pattern": e.get("topping_pattern"),
            "topping_note": e.get("topping_note"),
        }


    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The traded pattern's body as a box (pivot down to the structural stop, over its stored
        bar length), plus the detector's own note, score, flaws and topping warning — the full
        'why was this a base' record the detector wrote at the signal."""
        e = sig.get("extras") or {}
        d = str(sig["date"])
        out: list[dict] = []
        pat, piv, stop = e.get("pattern"), e.get("pattern_pivot"), e.get("pattern_stop")
        if pat and piv and stop:
            bars = int(e.get("pattern_length") or 30)
            depth = e.get("pattern_depth_pct")
            out.append({"shape": "box", "bars": bars, "to": d, "top": float(piv), "bottom": float(stop),
                        "role": "base", "label": f"{pat} · {bars} bars" + (f" · {depth:.1f}% deep" if isinstance(depth, (int, float)) else "")})
            out.append({"shape": "level", "bars": bars + 10, "to": d, "price": float(piv),
                        "role": "pivot", "label": f"pivot {piv:g} — a close above it on expanding volume triggers"})
            out.append({"shape": "level", "bars": bars, "to": d, "price": float(stop),
                        "role": "support", "label": f"structural stop {stop:g}"})
            note = f"{pat} identified: {e.get('pattern_note') or 'geometry matched'} · quality {e.get('pattern_quality', '?')} (0.45 needed)"
            if e.get("pattern_flaws"):
                note += f" · flaws: {e['pattern_flaws']}"
            if e.get("pattern_move"):
                note += f" · measured move +{e['pattern_move']:g} above the pivot"
            if e.get("topping_pattern"):
                note += f" · WARNING: topping structure {e['topping_pattern']} ({e.get('topping_note', '')})"
            out.append({"shape": "note", "at": d, "price": float(piv), "text": note})
        else:
            out = super().chart_anatomy(sig)
        return out


class ChartPatternCupStrategy(ChartPatternStrategy):
    """The same machinery, restricted to the cup — the selectivity experiment.

    `tests/test_chart_patterns.py` measures how often each detector fires on a
    pure random walk: VCP 44%, FLAT 31%, DBOT 31%, and 75% of walks match
    something, against 55% of real liquid stocks. Three of the seven detect
    noise about as readily as they detect the market — and they are the ones
    the full strategy traded most (FLAT 57 trades, ATRI 34, out of 140).

    CUP is the exception at 0.7% of random walks and 0.2% of real names. If
    shape carries anything, the selective detector should show it; if this
    does no better than the full set, the shape is not the thing and no
    seventh pattern will change that. That is the entire point of running it.
    """

    key = "chart_pattern_cup"
    name = "Cup and handle (superseded)"
    description = (
        "The chart-pattern strategy restricted to CUP and CUPNH — the only "
        "two detectors that are rare in random data."
    )
    variant_of = "chart_pattern_legacy"  # style is inherited from ChartPatternStrategy
    setup_codes = (cp.CUP, cp.CUPNH)
    allowed_codes = (cp.CUP, cp.CUPNH)

    thesis = (
        "If classical chart patterns carry information, the one that a random "
        "walk almost never produces should carry more of it than the ones a "
        "random walk produces constantly."
    )
    caveats = (
        "**RUN, AND THE RESULT IS INDECISIVE.** US, 2020-01-02 to 2026-10-02, "
        "300-symbol sample, identical to `chart_pattern`'s run: -0.24% CAGR "
        "(vs -4.08%), -13.0% max drawdown (vs -42.2%), 32 trades at a 25.0% "
        "win rate, -0.019R per trade (vs -0.213R), profit factor 0.94. Every "
        "headline favours the selective detector AND NONE OF IT IS "
        "SIGNIFICANT: the difference is +0.194R with a Welch t of 0.42, "
        "bootstrap 95% CI [-0.67, +1.12], P(cup better) = 0.66. Its own "
        "expectancy is -0.019R at t = -0.04 — indistinguishable from zero in "
        "either direction. Do not read the CAGR gap as evidence.",
        "**32 trades in 6.75 years is the price of selectivity.** CUP fires on "
        "~0.2% of names, so the more selective the detector the longer it "
        "takes to learn whether it works. Settling this needs roughly 10x the "
        "sample: the full universe over the full 13.75-year window, not a "
        "300-symbol draw.",
        "Of those 32 trades, 27 were CUPNH (-0.25R) and 5 were CUP proper "
        "(+1.23R). Five trades is not a finding, and the temptation to read "
        "one into it is exactly what the t-statistics above exist to resist.",
        "**This exists to be falsified.** It is the same code as "
        "`chart_pattern` with five of seven detectors switched off; compare "
        "the two over an identical window and sample, and read the difference, "
        "not either number alone.",
        "CUP fires on ~0.2% of liquid names, so expect FEW trades and wide "
        "error bars. A difference of a point or two of CAGR over ~20 trades "
        "says nothing at all.",
        "Every caveat on `chart_pattern` applies here unchanged.",
    )

    status = (
        "Indecisive: US 2020-2026, 300-symbol sample, bracket exit, -0.24% "
        "CAGR and -0.019R per trade over 32 trades (t = -0.04). That is "
        "indistinguishable from zero and not significantly better than the "
        "full pattern set."
    )
    setup_docs = {
        code: ChartPatternStrategy.setup_docs[code] for code in (cp.CUP, cp.CUPNH)
    }
