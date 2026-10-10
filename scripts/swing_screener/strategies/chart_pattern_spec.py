"""Classical chart patterns, built to the written specification
(research/chart-pattern-spec.md).

A second, rule-for-rule version of `chart_pattern`, kept alongside it so the
two can be compared: the original stays the baseline, with its measured
-4.08% CAGR. What differs:

- **Detection** (core/pattern_spec.py) carries the spec's rule ids. Swing
  points come at two scales ({K_MINOR} and {K_MAJOR} bars each side) with
  alternation and a minimum swing of max({MIN_SWING_PCT}%, {ATR_MULT} x
  ATR/close); "about equal" is max({TOL_PCT}%, {TOL_ATR_MULT} x ATR/close)
  rather than a fixed percentage; boundary patterns use least-squares
  trendlines with touch counts and containment; and every pattern carries a
  prior-trend context rule (PT-01/PT-02), which `chart_pattern` applies to
  only two of its seven.
- **Eleven pattern types** instead of seven, including the two
  head-and-shoulders, triples, rectangles, wedges, pennants and the high
  tight flag.
- **Levels come from the spec**: the trigger T, the invalidation X and the
  height H are each pattern's own, and the target is BO-06's T + H. No ATR
  heuristic chooses them.
- **States**, not just matches: a pattern is complete, confirmed, failed or
  void under BO-01..BO-05, so an old base that never broke out stops being
  reported as a live setup.

Where this deviates from the spec, and why
------------------------------------------
**X is not the stop.** BO-03 voids a pattern on a close beyond X; the spec
never says to place a stop there, and for a double bottom X sits a full
pattern height below the trigger. The stop here is a risk decision the spec
leaves open: under the pattern's own X, but never wider than {MAX_STOP_ATR}
ATR and never tighter than max({MIN_STOP_ATR} ATR, {MIN_STOP_PCT}%). The
spec's X is reported as `invalidation` either way.

**§11's tracker is not used.** `core.pattern_spec.PatternScanner` keeps
instances across days, which is what §3.3's outcome study needs; a strategy
is asked about one bar at a time, so the detectors are called fresh at day t.
Their per-bar states (BO-01..BO-05) are what this strategy reads.
"""

import pandas as pd

from ..config.base import MarketConfig
from ..core import pattern_spec as ps
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

# ---- §2 and §12: the spec's parameters
K_MINOR, K_MAJOR = 3, 8
MIN_SWING_PCT, ATR_MULT = 3.0, 1.5
TOL_PCT, TOL_ATR_MULT = 3.0, 0.75
BO_BUFFER = 0.5          # BO-01, %
BO_VOL = 1.4             # BO-02, x the 50-day average
MAX_WAIT = 20            # BO-04, days from completion to expiry
FAIL_DAYS = 10           # BO-05, days in which a close back through T fails it
HORIZON = 60             # §3.3, bars over which an outcome is recorded
PARAMS = ps.PatternParams(
    k_minor=K_MINOR, k_major=K_MAJOR, min_swing_pct=MIN_SWING_PCT, atr_mult=ATR_MULT,
    tol_pct=TOL_PCT, tol_atr_mult=TOL_ATR_MULT, bo_buffer=BO_BUFFER / 100, bo_vol=BO_VOL,
    max_wait=MAX_WAIT, fail_days=FAIL_DAYS, horizon=HORIZON,
)

# ---- this strategy's own trade rules (the spec stops at the levels)
MAX_CHASE_PCT = 4.0      # S5: how far past the trigger price may already be
MAX_BELOW_TRIGGER_PCT = 10.0  # S5: ...and how far below it may still be
MAX_ATR_PCT = 10.0       # S4: volatility ceiling
EARNINGS_DAYS = 10       # S3
MAX_STOP_ATR = 2.0       # the stop is never wider than this
MIN_STOP_ATR = 0.6       # ...nor tighter than this
MIN_STOP_PCT = 1.5       # ...nor tighter than this
MAX_RISK_PCT = 8.0       # beyond this the plan is WATCH, not a trade
MIN_R = 2.0              # BO-06's measured move must project at least this
OVERBOUGHT_RSI = 80.0    # XS3

# setup codes: one per bullish pattern the spec defines
CUP, CUPNH, DBOT, TBOT = "CUP", "CUPNH", "DBOT", "TBOT"
IHS, ATRI, SYMM, FWDG = "IHS", "ATRI", "SYMM", "FWDG"
RECT, FBASE, FLAG, HTF = "RECT", "FBASE", "FLAG", "HTF"

# code -> (spec section, how to detect it). Bearish types are NOT here: in a
# long-only book a top is a veto (gate S2, flag XS1), never a setup.
BULLISH: dict[str, tuple[str, object]] = {
    CUP: ("§4", lambda d: ps.detect_cup(d, PARAMS)),
    CUPNH: ("§4", lambda d: ps.detect_cup(d, PARAMS, require_handle=False)),
    DBOT: ("§5.1", lambda d: ps.detect_double_bottom(d, PARAMS)),
    TBOT: ("§5", lambda d: ps.detect_triple_bottom(d, PARAMS)),
    IHS: ("§6.2", lambda d: ps.detect_head_shoulders(d, PARAMS, inverse=True)),
    ATRI: ("§7", lambda d: _of_kind(d, (ps.ASCENDING,))),
    SYMM: ("§7", lambda d: _of_kind(d, (ps.SYMMETRICAL,))),
    FWDG: ("§10", lambda d: _of_kind(d, (ps.FALLING_WEDGE,))),
    RECT: ("§8.1", lambda d: _of_kind(d, (ps.RECTANGLE,))),
    FBASE: ("§8.2", lambda d: ps.detect_flat_base(d, PARAMS)),
    FLAG: ("§9.2", lambda d: ps.detect_flag(d, PARAMS)),
    HTF: ("§9.3", lambda d: ps.detect_flag(d, PARAMS, high_tight=True)),
}
BEARISH = {
    "double top": lambda d: ps.detect_double_top(d, PARAMS),
    "head and shoulders top": lambda d: ps.detect_head_shoulders(d, PARAMS),
    "rising wedge": lambda d: _of_kind(d, (ps.RISING_WEDGE,)),
    "descending triangle": lambda d: _of_kind(d, (ps.DESCENDING,)),
}


def _of_kind(daily, kinds: tuple[str, ...]) -> dict:
    return ps._pick_kinds(ps.detect_boundaries(daily, PARAMS), kinds, ps.TR_RULES)


def _live(res: dict) -> bool:
    """Complete or freshly confirmed — not an old breakout still on the books."""
    return bool(res.get("ok") and res.get("metrics", {}).get("is_live"))


class ChartPatternSpecStrategy(Strategy):
    selection = "time_series"
    family = "chart_pattern"
    version = "1.0"
    changelog = (
        ("1.0", "2026-10-10",
         "v1 baseline, built to the written detection specification: twelve patterns with section-referenced definitions - cup, cup-no-handle, double bottom, triple bottom, inverse head-and-shoulders, flat base, bull flag, ascending triangle, symmetrical triangle, falling wedge, rectangle and high tight flag."),
    )
    key = "chart_pattern"
    name = "Classical chart-pattern breakout"
    description = (
        "The written chart-pattern specification, rule for rule: eleven "
        "patterns detected with ATR-scaled tolerances, fitted trendlines and "
        "prior-trend context, traded at the spec's own trigger, invalidation "
        "and measured move."
    )
    style = "breakout"
    # The same screen as `chart_pattern`, deliberately: the question this
    # strategy exists to answer is whether the spec's detection beats the
    # ad-hoc one, and running the two over different candidate sets would
    # confound that. The cost is real and is named in the caveats — the
    # spec's REVERSAL patterns (double bottom, inverse head and shoulders)
    # form after a decline, so a screen demanding price within 15% of the
    # 52-week high above a rising 200-day mostly excludes them.
    screen_key = "near_highs"

    gate_codes = ("S1", "S2", "S3", "S4", "S5")
    watch_codes = ("XS1", "XS2", "XS3")
    setup_codes = tuple(BULLISH)
    needs_ctx_extras = True
    extra_columns = (
        "pattern", "pattern_state", "trigger", "invalidation", "measured_target",
        "pct_from_trigger", "structural_r", "topping_pattern", "pattern_note",
        "first_failed_rule",
    )
    extra_numeric_columns = ("trigger", "invalidation", "measured_target",
                             "pct_from_trigger", "structural_r")
    min_bars = 320

    status = (
        "Backtested 2026-10-09 and it loses, by less than its sibling: -0.93% "
        "CAGR and -0.072R per trade over 253 trades (US, 2020-2026, 300-symbol "
        "sample), against `chart_pattern`'s -5.60% and -0.309R on the same "
        "run. The +0.234R difference has a Welch t of 1.16 and a 95% interval "
        "of [-0.16, +0.62], so the spec's discipline is NOT demonstrated to "
        "help; both lose 14-19 points of CAGR to the benchmark."
    )
    thesis = (
        "If classical chart patterns carry information, a detector built to a "
        "written specification — ATR-scaled tolerances, a prior-trend rule on "
        "every pattern, fitted boundary lines, and a breakout judged against "
        "a trigger frozen the day before — should find it where a looser "
        "reading of the same textbooks did not."
    )
    how_it_works = (
        "**Swing points** come at two scales ({K_MINOR} and {K_MAJOR} bars "
        "each side), alternating high/low, with moves under "
        "max({MIN_SWING_PCT}%, {ATR_MULT} x ATR/close) dropped as wiggles. "
        "Every level a pattern uses is built from them.",
        "**Each pattern carries its own context rule** — a prior uptrend for "
        "continuations, a prior downtrend for reversals — so the same shape "
        "after a rise and after a fall are not treated as one thing.",
        "**Setups** are the eleven bullish types, each detected by its own "
        "numbered rules; the report names which fired and, when none did, the "
        "first rule that failed.",
        "**Gates S1-S5** require a live bullish pattern, no CONFIRMED topping "
        "pattern on the same chart, no earnings inside {EARNINGS_DAYS} trading "
        "days, ATR under {MAX_ATR_PCT}% of price, and price no more than "
        "{MAX_CHASE_PCT}% past the trigger.",
        "**Entry** is a tick through T x (1 + {BO_BUFFER}%), the level BO-01 "
        "calls a breakout, or the market price if price has already cleared "
        "it. **Target** is BO-06's measured move, T + H.",
        "**The trigger fires** on a close through it on {BO_VOL}x average "
        "volume (BO-01 + BO-02). Without the volume it stays a setup, capped "
        "at WATCH.",
    )
    caveats = (
        "**73% of its trades are one pattern.** CUPNH took 185 of 253; DBOT "
        "15, IHS 18, FWDG 15, RECT 10, ATRI 4, TBOT 6; and CUP, FBASE, SYMM, "
        "FLAG and HTF took NONE. Whatever the backtest measured, it measured "
        "the cup-without-handle — the weaker O'Neil variant — not the spec's "
        "breadth. DBOT was the only pattern with positive expectancy (+0.05R "
        "on 15 trades, which is nothing).",
        "**It is signal-saturated.** 942 signals produced 253 trades: 85 were "
        "passed up with all 10 slots full and 132 for insufficient cash, and "
        "exposure ran at 93.9% against `chart_pattern`'s 79.3%. A position "
        "cap, not the detector, decided much of what got traded.",
        "**Five of the spec's rules cannot fire at its own default "
        "parameters** (CH-09, HS-06, TR-04, TR-07, FL-04) because §2.1's 3% "
        "minimum swing and §2.2's 3% tolerance are large relative to what "
        "those rules ask for. They are implemented and tested, and the "
        "defaults are left as written; see core/pattern_spec.py.",
        "**Flags and the high tight flag find nothing in practice.** Over 283 "
        "liquid US names the pole rules rejected 255 of them (FP-01 172, "
        "FP-02 63): a 15% rise inside 15 days on 1.3x volume is simply rare.",
        "**The flat base is the least selective pattern here**, firing on "
        "24% of random walks against the cup's 0%. It has no touch "
        "requirement and its volume rule is off by default.",
        "**Detection costs ~40ms per symbol-day** against `chart_pattern`'s "
        "~1ms, because eleven detectors run where seven did and each refits "
        "swings. A backtest of it is slower in proportion.",
        "**§5 has no ceiling on the middle swing**, so two lows either side "
        "of a spike pass DB-03: AEVA screened as a live double bottom with "
        "lows of 13.51 and 13.90 around a 28.42 peak. Gate S5's band keeps "
        "it out of the report rather than the detector rejecting it, because "
        "the detector implements the spec as written; "
        "`PatternParams.db_max_peak` exists to test a cap.",
        "**The reversal patterns are mostly unreachable through this "
        "screen.** `near_highs` wants price within 15% of the 52-week high "
        "above a rising 200-day, while DBOT and IHS require a prior DOWNTREND "
        "(PT-02) and form well below the highs. They are implemented and "
        "tested, and they will rarely fire here. Measuring them needs a "
        "screen that does not demand an uptrend — a deliberate follow-up, not "
        "an oversight: changing the screen would also break the like-for-like "
        "comparison with `chart_pattern` that this strategy exists for.",
        "Several patterns usually match one chart. The traded one is the "
        "highest-priority live match; `pattern` names it and the setup "
        "columns show the rest.",
    )
    gate_docs = {
        "S1": "A bullish pattern must be COMPLETE or newly CONFIRMED on this "
              "bar. A pattern that broke out more than its outcome horizon ago, "
              "or that BO-03/BO-04 voided, is history and does not qualify.",
        "S2": "No CONFIRMED topping pattern (double top, head and shoulders "
              "top, rising wedge, descending triangle) on the same chart. A "
              "long bought inside a confirmed top is the trade this screener "
              "would otherwise keep taking.",
        "S3": "Earnings must not fall within {EARNINGS_DAYS} trading days: a "
              "base breaking out two days before a print is a bet on the print.",
        "S4": "ATR14 must be at most {MAX_ATR_PCT}% of price.",
        "S5": "The close must sit in the actionable band around the trigger: "
              "no more than {MAX_CHASE_PCT}% above it (past that the breakout "
              "happened without you) and no more than "
              "{MAX_BELOW_TRIGGER_PCT}% below it. The spec has no such rule "
              "because §11's tracker holds a pattern from completion and lets "
              "BO-04 expire it; a screener asked about one bar needs the "
              "band, or it reports AEVA as a live double bottom with a "
              "trigger 108% overhead.",
    }
    watch_docs = {
        "XS1": "A topping pattern is FORMING (rolled over but not yet through "
               "its neckline) on the same chart. Caps the decision at TRADE ON "
               "TRIGGER; a confirmed one fails gate S2 outright.",
        "XS2": "Price is through the trigger but volume is below {BO_VOL}x its "
               "50-day average, so BO-02 has not confirmed the breakout. Caps "
               "at WATCH.",
        "XS3": "RSI14 above {OVERBOUGHT_RSI}. Caps at TRADE ON TRIGGER.",
    }
    setup_docs = {
        CUP: "§4 cup with handle: a rounded correction of "
             "12-33% recovering to its left lip, then a 5-25 day handle "
             "drifting down in the upper half of the cup on volume below 0.8x "
             "its 50-day average. T is the handle's high.",
        CUPNH: "§4 the same cup read before a handle exists, with price still "
               "at the rim. T is the right lip C. O'Neil treats it as the "
               "weaker variant, which is why it is a separate code.",
        DBOT: "§5.1 double bottom: two lows about equal within tolerance, at "
              "least 20 days apart, with a middle peak at least 10% above "
              "them. T is that peak.",
        TBOT: "§5 triple bottom: the same with a third low, all three level. "
              "T is the higher of the two middle peaks.",
        IHS: "§6.2 inverse head and shoulders: three lows with the middle one "
             "lowest and the shoulders level, under a neckline sloping no "
             "more than 0.3% per day. T is the neckline at today's bar, so it "
             "moves.",
        ATRI: "§7 ascending triangle: a flat upper line and a rising lower "
              "one, at least five touches between them, converging with the "
              "apex still ahead and volume declining. T is the upper line.",
        SYMM: "§7 symmetrical triangle: both lines converging at rates within "
              "a factor of two. Neutral by reputation; recorded here as a "
              "bullish break of the upper line.",
        FWDG: "§10 falling wedge: both lines falling with the upper falling "
              "faster. The textbook reading is a bullish break.",
        RECT: "§8.1 rectangle: two flat lines, a 5-25% range held for 20-250 "
              "days with at least four touches. T is the upper line.",
        FBASE: "§8.2 flat base: a range no deeper than 15% over the longest "
               "window of 25-120 days that holds it, after a 20% advance, "
               "sitting within 5% of the 52-week high. T is the window high.",
        FLAG: "§9.2 bull flag or pennant: a 15%+ pole inside 15 days on "
              "1.3x volume, then a 5-20 day pause retracing at most half of "
              "it on falling volume. T is the pause's upper line.",
        HTF: "§9.3 high tight flag: a pole that at least doubles in 20-40 "
             "days, then a 15-25 day flag no deeper than 25%. It carries no "
             "measured target, because the textbooks give none.",
    }
    entry_rules = (
        "**Entry** is a tick through T x (1 + {BO_BUFFER}%) — BO-01's "
        "breakout level — rounded up to the tick size, or the market price "
        "when price has already cleared it, since there is no resting "
        "buy-stop below the market.",
        "**Stop.** The spec's X is an INVALIDATION level, not a stop: BO-03 "
        "voids a pattern on a close beyond X, and for a double bottom that "
        "sits a full pattern height below the trigger. The stop is placed "
        "under X but never wider than {MAX_STOP_ATR} ATR, and never tighter "
        "than max({MIN_STOP_ATR} ATR, {MIN_STOP_PCT}%) — a stop inside the "
        "spread is not a stop, and dividing a measured move by it fabricates R.",
        "**Target** is BO-06's measured move, T + H, with no floor. A setup "
        "projecting under {MIN_R}R is rejected rather than padded.",
        "**Rejected as a trade** when the stop is more than {MAX_RISK_PCT}% "
        "below the entry or the measured move projects under {MIN_R}R; the "
        "row is kept as WATCH with the reason.",
    )
    exit_rules = (
        "Live: the plan's fixed bracket — the stop under the pattern's low, "
        "or BO-06's measured target.",
        "The spec's own exit is BO-05: a close back through T within "
        "{FAIL_DAYS} days marks the pattern FAILED. That is a pattern-status "
        "rule, not a position rule, and the portfolio simulator does not "
        "implement it; a backtest of this strategy uses the shared exit "
        "policies like any other.",
        "Backtest: whatever `--exit-mode` selects (default the fixed bracket).",
    )
    param_docs = (
        ("Swing scales", "K_MAJOR",
         "Bars each side defining a confirmed swing point: {K_MINOR} for "
         "flags and handles, {K_MAJOR} for cups, doubles and shoulders. A "
         "swing at bar i is only known at bar i + k."),
        ("Minimum swing", "MIN_SWING_PCT",
         "Moves smaller than max({MIN_SWING_PCT}%, {ATR_MULT} x ATR/close) "
         "are wiggles and are dropped before any pattern is looked for."),
        ("Price tolerance", "TOL_PCT",
         "Two prices count as equal within max({TOL_PCT}%, {TOL_ATR_MULT} x "
         "ATR/close) — wider on a volatile stock, which a fixed percentage "
         "is not."),
        ("Breakout buffer", "BO_BUFFER",
         "BO-01: a close must clear the trigger by this percentage "
         "({BO_BUFFER}%)."),
        ("Breakout volume", "BO_VOL",
         "BO-02: and do it on {BO_VOL}x the 50-day average volume."),
        ("Actionable band", "MAX_CHASE_PCT",
         "Gate S5 wants the close between {MAX_BELOW_TRIGGER_PCT}% below the "
         "trigger and {MAX_CHASE_PCT}% above it."),
        ("Stop width", "MAX_STOP_ATR",
         "The stop sits under the pattern's invalidation level but never "
         "wider than {MAX_STOP_ATR} ATR nor tighter than "
         "max({MIN_STOP_ATR} ATR, {MIN_STOP_PCT}%)."),
        ("Minimum reward", "MIN_R",
         "A measured move projecting under {MIN_R}R is WATCH, not a trade."),
        ("Minimum price", "cfg.screener.min_price",
         "Screen: closes below this price are excluded."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume",
         "Screen: the 20-day average of close x volume must reach this."),
        ("Tick size", "cfg.tick_size",
         "Entry is rounded up and the stop rounded down to this increment."),
        ("Risk per trade", "cfg.risk_pct",
         "Fraction of equity risked between entry and stop, which sets "
         "position size."),
    )
    backtest_args = ""

    # ---------- screen ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        """Price and liquidity only. Trend and context are the spec's own
        rules (PT-01/PT-02), applied per pattern inside the detectors, so
        screening on trend here would double-count them — and would delete
        the reversal patterns, which form by definition after a decline."""
        if cfg.screener.min_price and last["close"] < cfg.screener.min_price:
            return False, f"price {last['close']:.2f} < {cfg.screener.min_price}"
        if cfg.screener.min_dollar_volume:
            dv = last.get("dollar_vol_sma20")
            if pd.isna(dv) or dv < cfg.screener.min_dollar_volume:
                return False, f"liquidity below {cfg.screener.min_dollar_volume:,.0f}"
        if pd.isna(last.get("atr14")) or not last.get("atr14"):
            return False, "no ATR"
        return True, "passed"

    # ---------- detection and gates ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        d = ctx.daily
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        close, atr14 = ctx.close, ctx.atr

        best: tuple[str, dict] | None = None
        first_fail: str | None = None
        for code, (_section, detect) in BULLISH.items():
            try:
                res = detect(d)
            except (IndexError, ValueError, ZeroDivisionError, KeyError):
                continue
            live = _live(res)
            result.setups[code] = live
            if live and (best is None or _priority(code) < _priority(best[0])):
                best = (code, res)
            if not live and res.get("fail") and first_fail is None:
                first_fail = f"{code}:{res['fail']}"

        top_name, top_res = None, None
        for name, detect in BEARISH.items():
            try:
                res = detect(d)
            except (IndexError, ValueError, ZeroDivisionError, KeyError):
                continue
            if _live(res):
                top_name, top_res = name, res
                break

        ctx.extras["first_failed_rule"] = first_fail or ""
        if best is not None:
            code, res = best
            lv = res["levels"]
            ctx.extras.update({
                "pattern": code,
                "pattern_state": res["state"],
                "trigger": float(lv.trigger),
                "invalidation": float(lv.invalidation),
                "height": float(lv.height),
                "measured_target": float(lv.target),
                "pattern_note": _note(res),
            })
        if top_name is not None:
            ctx.extras["topping_pattern"] = top_name
            ctx.extras["topping_state"] = top_res["state"]

        # S1: a live bullish pattern
        if best is None:
            result.fail("S1", f"no live pattern ({first_fail or 'nothing detected'})")
        else:
            result.ok("S1", f"{best[0]} {best[1]['state']}")

        # S2: not inside a confirmed top
        if top_name is not None and top_res["state"] == ps.CONFIRMED:
            result.fail("S2", f"confirmed {top_name} on the same chart")
        else:
            result.ok("S2")

        # S3: earnings
        if ctx.earnings_days_away is not None and ctx.earnings_days_away <= EARNINGS_DAYS:
            result.fail("S3", f"earnings in {ctx.earnings_days_away} trading days")
        else:
            result.ok("S3")

        # S4: volatility
        atr_pct = d["atr_pct"].iloc[-1]
        if pd.notna(atr_pct) and atr_pct > MAX_ATR_PCT:
            result.fail("S4", f"ATR% {atr_pct:.1f} > {MAX_ATR_PCT:g}%")
        else:
            result.ok("S4")

        # S5: price is in the actionable band around the trigger
        trigger = ctx.extras.get("trigger")
        if trigger:
            gap = (close / float(trigger) - 1) * 100
            ctx.extras["pct_from_trigger"] = gap
            if gap > MAX_CHASE_PCT:
                result.fail("S5", f"{gap:.1f}% above the trigger")
            elif gap < -MAX_BELOW_TRIGGER_PCT:
                result.fail("S5", f"{-gap:.1f}% below the trigger — not actionable")
            else:
                result.ok("S5")
        else:
            result.ok("S5")

        result.recompute_first_fail()
        self._watch_flags(ctx, result, top_name, top_res, atr14)
        return result

    def _watch_flags(self, ctx, result, top_name, top_res, atr14) -> None:
        d = ctx.daily
        trigger = ctx.extras.get("trigger")
        vol = float(d["volume"].iloc[-1])
        vol_sma50 = d["vol_sma50"].iloc[-1]
        rsi14 = d["rsi14"].iloc[-1]

        forming = top_name is not None and top_res["state"] == ps.COMPLETE
        result.watch_flags["XS1"] = bool(forming)
        if forming:
            result.watch_notes["XS1"] = f"{top_name} forming on the same chart"

        through = bool(trigger) and ctx.close > float(trigger)
        thin = pd.notna(vol_sma50) and vol_sma50 and vol < BO_VOL * vol_sma50
        result.watch_flags["XS2"] = bool(through and thin)
        if result.watch_flags["XS2"]:
            result.watch_notes["XS2"] = (
                f"through the trigger on {vol / vol_sma50:.2f}x volume "
                f"(BO-02 wants {BO_VOL:g}x)")

        result.watch_flags["XS3"] = bool(pd.notna(rsi14) and rsi14 > OVERBOUGHT_RSI)
        if result.watch_flags["XS3"]:
            result.watch_notes["XS3"] = f"RSI14 {rsi14:.0f} > {OVERBOUGHT_RSI:g}"

    def watch_cap(self, result: StrategyResult) -> str:
        caps = []
        if result.watch_flags.get("XS2"):
            caps.append("WATCH_WAIT")
        for code in ("XS1", "XS3"):
            if result.watch_flags.get(code):
                caps.append("TRADE_ON_TRIGGER")
        return min(caps, key=CAP_ORDER.index) if caps else "TRADE_HIGH_CONFIDENCE"

    def setup_quality(self, result: StrategyResult) -> float:
        active = [c for c in self.setup_codes if result.setups.get(c)]
        if not active:
            return 0.0
        score = 2.0 - 0.1 * min(_priority(active[0]), 10)
        if result.watch_flags.get("XS1"):
            score -= 0.5
        if result.watch_flags.get("XS2"):
            score -= 1.0
        return max(score, 0.0)

    # ---------- entry ----------

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        """BO-01 and BO-02, which the detector already evaluated at day t."""
        return ctx.extras.get("pattern_state") == ps.CONFIRMED

    def build_plans(
        self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig
    ) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no active setup")
        e = ctx.extras
        trigger, invalid = e.get("trigger"), e.get("invalidation")
        height, atr14 = e.get("height"), ctx.atr
        if trigger is None or invalid is None or pd.isna(atr14) or not atr14:
            return PlanChoice(None, None, "missing spec levels")
        trigger, invalid, height = float(trigger), float(invalid), float(height or 0.0)

        level = trigger * (1 + BO_BUFFER / 100)
        entry = round_tick(max(level, ctx.close), cfg.tick_size, "up")
        structural = max(invalid, entry - MAX_STOP_ATR * atr14)
        floor = min(entry - MIN_STOP_ATR * atr14, entry * (1 - MIN_STOP_PCT / 100))
        stop = round_tick(min(structural, floor), cfg.tick_size, "down")
        risk = entry - stop
        if risk <= 0:
            return PlanChoice(None, None, "degenerate stop")

        target = entry + height if height > 0 else entry + MIN_R * risk
        ctx.extras["structural_r"] = round(height / risk, 3) if height > 0 else None
        plan = TradePlan(
            plan="SPEC", setup=e.get("pattern", "?"), entry=entry, stop=stop,
            target=target, risk_per_share=risk, reward_per_share=target - entry,
            r_multiple=(target - entry) / risk, nearest_overhead_above_entry=None,
        )
        return PlanChoice(plan, None, f"{e.get('pattern')} trigger {trigger:.2f}")

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
            return Decision("AVOID", "AVOID", "degenerate plan", float("nan"),
                            float("nan"), 0.0)

        risk_pct = plan.risk_per_share / plan.entry * 100
        r_mult = plan.r_multiple
        cap = self.watch_cap(result)
        fired = self.entry_signal_fired(ctx, result)
        reasons: list[str] = []

        if sizing_result.too_large:
            label, _ = "WATCH_WAIT", reasons.append("too large for account")
        elif risk_pct > MAX_RISK_PCT or r_mult < MIN_R:
            label = "WATCH_WAIT"
            if risk_pct > MAX_RISK_PCT:
                reasons.append(f"stop {risk_pct:.1f}% > {MAX_RISK_PCT:g}%")
            if r_mult < MIN_R:
                reasons.append(
                    f"{plan.setup} projects {r_mult:.2f}R < {MIN_R:g}R")
        elif cap == "WATCH_WAIT":
            label = "WATCH_WAIT"
            reasons.append(result.watch_notes.get("XS2", "capped by watch flag"))
        elif fired and cap == "TRADE_HIGH_CONFIDENCE":
            label = "TRADE_HIGH_CONFIDENCE"
            reasons.append(f"{plan.setup} confirmed (BO-01+BO-02), {r_mult:.2f}R")
        else:
            label = "TRADE_ON_TRIGGER"
            if not fired:
                reasons.append(
                    f"{plan.setup} complete, waiting for a close through "
                    f"{plan.entry:.2f} on {BO_VOL:g}x volume")
            if cap == "TRADE_ON_TRIGGER":
                active = [c for c in ("XS1", "XS3") if result.watch_flags.get(c)]
                reasons.append(f"capped by watch flag ({'/'.join(active)})")

        before = label
        if regime_downgrade_active and label != "AVOID":
            label = DOWNGRADE_MAP[label]
            reasons.append("market-regime downgrade applied")
        return Decision(LABELS[before], LABELS[label], "; ".join(reasons),
                        risk_pct, r_mult, self.setup_quality(result))

    def report_extras(
        self, ctx: StockContext, result: StrategyResult, plan: TradePlan | None
    ) -> dict:
        e = ctx.extras
        trig = e.get("trigger")
        return {
            "pattern": e.get("pattern"),
            "pattern_state": e.get("pattern_state"),
            "trigger": round(float(trig), 2) if trig else None,
            "invalidation": round(float(e["invalidation"]), 2)
            if e.get("invalidation") else None,
            "measured_target": round(float(e["measured_target"]), 2)
            if e.get("measured_target") else None,
            "pct_from_trigger": round((ctx.close / float(trig) - 1) * 100, 2)
            if trig else None,
            "structural_r": e.get("structural_r"),
            "topping_pattern": e.get("topping_pattern"),
            "pattern_note": e.get("pattern_note"),
            "first_failed_rule": e.get("first_failed_rule"),
        }


    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The spec levels of the traded pattern — trigger, invalidation and measured target —
        with the detector's own note. The spec stores levels, not the pattern's start date, so
        the lines span a fixed window rather than the exact body."""
        e = sig.get("extras") or {}
        d = str(sig["date"])
        out: list[dict] = []
        if e.get("pattern") and e.get("trigger"):
            out.append({"shape": "level", "bars": 60, "to": d, "price": float(e["trigger"]),
                        "role": "pivot", "label": f"trigger {e['trigger']:g} — confirms {e['pattern']}"})
            if e.get("invalidation"):
                out.append({"shape": "level", "bars": 60, "to": d, "price": float(e["invalidation"]),
                            "role": "support", "label": f"invalidation {e['invalidation']:g} — the pattern is wrong below this"})
            if e.get("measured_target"):
                out.append({"shape": "level", "bars": 20, "to": d, "price": float(e["measured_target"]),
                            "role": "target", "label": f"measured target {e['measured_target']:g}", "dash": True})
            note = f"{e['pattern']} ({e.get('pattern_state', '')}): {e.get('pattern_note') or 'spec geometry matched'}"
            if e.get("height"):
                note += f" · height {e['height']:g} projected above the trigger"
            if e.get("topping_pattern"):
                note += f" · WARNING: topping {e['topping_pattern']} ({e.get('topping_state', '')})"
            out.append({"shape": "note", "at": d, "price": float(e["trigger"]), "text": note})
        else:
            out = super().chart_anatomy(sig)
        return out


# Which label to trade when several fire at once. Ordered by how selective the
# detector proved on random walks (cup 0%, triangle 4%, rectangle 7%, ... flat
# base 24%): the rarer the shape in noise, the more a match says.
_ORDER = (CUP, HTF, IHS, CUPNH, TBOT, ATRI, FLAG, DBOT, SYMM, RECT, FWDG, FBASE)


def _priority(code: str) -> int:
    return _ORDER.index(code) if code in _ORDER else len(_ORDER)


def _note(res: dict) -> str:
    m = res.get("metrics", {})
    bits = [f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
            for k, v in m.items()
            if k in ("depth_pct", "cup_days", "handle_depth_pct", "handle_days",
                     "separation_days", "middle_pct", "duration_days",
                     "apex_progress", "window_days", "pole_gain_pct",
                     "retrace_pct", "head_clearance_pct")]
    return ", ".join(bits)
