"""Stage analysis — Weinstein's Stage 2 breakout, on weekly bars.

Stan Weinstein's method sorts every stock into four stages with one line, the 30-week moving
average: Stage 1 a sideways base, Stage 2 an advance above a rising line, Stage 3 a flattening
top, Stage 4 a decline. This buys the Stage 1-to-2 transition and holds while the weekly close
stays above the line.

THE ONLY WEEKLY STRATEGY HERE. Everything else in this package decides on daily bars. That is not
a detail: a weekly close ignores four days of noise, so the same idea on daily bars is a different
and much twitchier rule. `StockContext` already carries resampled weekly bars, so the strategy
reads `ctx.weekly` and its daily sibling only for the entry price.

The 30-week average is a SIMPLE average of weekly closes. `ctx.weekly` already carries `ema30`,
which is a 30-week exponential average serving a different screen's criterion; Weinstein's line is
the simple one and substituting the exponential would change both the stage boundaries and the
exit.

WHAT IT SHARES. Its universe gates come from the `near_highs` screen, evaluated by that screen's
own criteria -- above the 200-day, 200-day not falling, near the 52-week high -- which is as close
as the daily screens come to "above a rising 30-week line, breaking out near highs". The weekly
conditions that have no screen equivalent are the strategy's own gates G4 onward.
"""
from __future__ import annotations

import pandas as pd

from ..config.base import MarketConfig
from ..core.context import StockContext
from .base import (LABELS, Decision, PlanChoice, Strategy, StrategyResult, TradePlan,
                   tradable_point_in_time)
from .trend_pullback import round_tick

STG01 = "S1"   # the Stage 1 -> Stage 2 breakout

# ---- the line, and the stages it defines
MA_WEEKS = 30                 # Weinstein's 30-week simple average of weekly closes
SLOPE_WEEKS = 4               # the line is compared with its own value this many weeks ago
FLAT_TOL_PCT = 1.0            # within this much either way counts as flat, not rising or falling

# ---- the Stage 1 base and the breakout
BASE_MIN_WEEKS = 12           # sideways for at least this long
#: A base is a CONTAINED range, so it needs a depth limit. Without one, "sideways" was tested as
#: "the weekly close is below the highest high of the last 26 weeks", which is almost always true
#: -- so every stock reported a base the full 104-week cap, BASE_MIN_WEEKS never bound, and the
#: base low used for the stop was the lowest low of two years, which pinned every stop to the
#: MAX_STOP_PCT floor. Weinstein's bases are shallow; 30% is generous for one.
BASE_MAX_DEPTH_PCT = 30.0
BASE_MAX_WEEKS = 104          # stop looking back beyond this
RESISTANCE_WEEKS = 26         # resistance is the highest weekly high of this many weeks
RS_WEEKS = 13                 # the stock must match the index over this period
VOL_MULT = 2.0                # breakout week's volume against the previous weeks' average
VOL_WEEKS = 10

# ---- the trade
MAX_STOP_PCT = 15.0           # skip or shrink if the structural stop is further than this
BASE_TARGET_MULT = 1.0        # nominal target: the base's own height above the breakout


def _market_of(symbol: str) -> str:
    """Which market a symbol belongs to, from the configured ticker suffixes.

    Shared reasoning with rs_leaders: StockContext carries no market, and the index-level stage
    check needs one. Read from MARKETS so a new country stays a config entry (CLAUDE.md).
    """
    from ..config import MARKETS
    best, blank = None, None
    for k, cfg in MARKETS.items():
        sfx = getattr(cfg, "symbol_suffix", "") or ""
        if not sfx:
            blank = k
        elif symbol.upper().endswith(sfx.upper()):
            best = k
    return best or blank or "us"


def ma30(weekly: pd.DataFrame) -> pd.Series:
    return weekly["close"].rolling(MA_WEEKS).mean()


def line_state(line: pd.Series) -> tuple[str, float]:
    """("rising" | "flat" | "falling", percent change) of the 30-week line over SLOPE_WEEKS.

    Weinstein's stages turn on the line's SLOPE, not on price relative to it, so this is the one
    measurement the whole method rests on. A band is required: a line that is dead flat in reality
    wanders by fractions of a percent, and calling that "rising" would put every basing stock in
    Stage 2.
    """
    if len(line) <= SLOPE_WEEKS:
        return "flat", float("nan")
    now, then = line.iloc[-1], line.iloc[-1 - SLOPE_WEEKS]
    if pd.isna(now) or pd.isna(then) or then <= 0:
        return "flat", float("nan")
    chg = (now / then - 1) * 100
    if chg > FLAT_TOL_PCT:
        return "rising", chg
    if chg < -FLAT_TOL_PCT:
        return "falling", chg
    return "flat", chg


def stage_of(weekly: pd.DataFrame) -> int:
    """Weinstein's four stages from the close and the line's slope. 0 when undecidable.

    Stage 1 (base) and Stage 3 (top) are BOTH a flat line; what separates them is whether the
    advance already happened, which the close relative to the line cannot tell you. This returns
    1 when flat and below the line and 3 when flat and above it -- a simplification, and the
    reason the Stage 3 warning here is a watch flag rather than a gate.
    """
    if len(weekly) < MA_WEEKS + SLOPE_WEEKS:
        return 0
    line = ma30(weekly)
    state, _ = line_state(line)
    close = float(weekly["close"].iloc[-1])
    lv = line.iloc[-1]
    if pd.isna(lv):
        return 0
    above = close > float(lv)
    if state == "rising":
        return 2 if above else 1
    if state == "falling":
        return 4 if not above else 3
    return 3 if above else 1


class StageAnalysisStrategy(Strategy):
    """Weinstein's Stage 2 breakout, bought on the weekly bar and held above the 30-week line."""

    key = "stage_analysis"
    name = "Stage analysis"
    description = ("Buy the weekly breakout from a Stage 1 base into Stage 2 -- above "
                   "{RESISTANCE_WEEKS}-week resistance and a rising {MA_WEEKS}-week average on "
                   "{VOL_MULT}x volume -- and hold while the weekly close stays above the line.")
    family = "stage_analysis"
    version = "1.0"
    changelog = (("1.0", "2026-10-18",
                  "First version. The stage model was validated against the guide's own Trent "
                  "narrative before any trade logic existed: Stage 2 from August 2023 through "
                  "October 2024 (close 2,049 -> 7,128) and Stage 4 by March 2025, matching the "
                  "guide's '1,500 to more than 7,000, held until October 2024'."),)

    style = "breakout"
    behaviour = "trend_momentum"
    selection = "time_series"

    screen_key = "near_highs"
    screen_gates = {"G1": "H1", "G2": "H2", "G3": "H3"}
    gate_codes = ("G1", "G2", "G3", "G4", "G5", "G6", "G7")
    gate_titles = {
        "G1": "Above the 200-day", "G2": "200-day not falling", "G3": "Near the 52-week high",
        "G4": "Weekly close above the 30-week line", "G5": "30-week line rising",
        "G6": "Matching the index over 13 weeks", "G7": "Market not in Stage 4",
    }
    watch_codes = ("W1", "W2", "W3")
    setup_codes = (STG01,)
    setup_names = {STG01: "Stage 2 breakout"}
    #: 60 weeks of weekly bars, which the guide requires for the line and the 52-week range, plus
    #: the daily history needed to resample them.
    min_bars = 330
    needs_ctx_extras = True
    extra_columns = ("stage", "line_slope_pct", "resistance", "base_weeks", "base_depth_pct",
                     "vol_ratio", "ma30")
    #: `broke_out` is carried in extras but is a BOOL, so it is not a numeric column.
    extra_numeric_columns = extra_columns

    thesis = (
        "A stock spends most of its life going nowhere, and the 30-week line sorts the going-nowhere "
        "from the going-somewhere without predicting either. The transition out of a base is where "
        "the money is made, because that is when the holders who have been selling into every rally "
        "finally run out and institutions have to pay up for stock. Weekly bars are the point, not a "
        "convenience: they discard the four days of noise that make the same idea unusable daily."
    )
    how_it_works = (
        "Everything is decided on WEEKLY bars -- a week's high, low, Friday close and total volume. "
        "The {MA_WEEKS}-week simple average of weekly closes is the only line used.",
        "The stage comes from the line's slope over {SLOPE_WEEKS} weeks and the close's position "
        "against it, with a {FLAT_TOL_PCT}% band so a wandering flat line is not read as a trend: "
        "rising and above is Stage 2, falling and below is Stage 4.",
        "Resistance is the highest weekly high of the previous {RESISTANCE_WEEKS} weeks. The base "
        "is the LONGEST window of at least {BASE_MIN_WEEKS} weeks whose high-to-low depth is within "
        "{BASE_MAX_DEPTH_PCT}% -- a contained range, not merely a stretch below resistance.",
        "The breakout week closes above that resistance, above a rising {MA_WEEKS}-week line, with "
        "volume at least {VOL_MULT}x the average of the previous {VOL_WEEKS} weeks, and the stock "
        "must have matched the index over {RS_WEEKS} weeks.",
        "Weinstein's forest-before-trees rule is gate G7: no new buys while the market's own index "
        "is in Stage 4.",
        "The stop is just below the higher of the {MA_WEEKS}-week line and the base's low. If that "
        "is more than {MAX_STOP_PCT}% away the trade is flagged rather than silently resized.",
    )
    caveats = (
        "**Stage 1 and Stage 3 are both a flat line, and this cannot fully separate them.** What "
        "distinguishes a base from a top is whether the advance already happened, which the close "
        "relative to the line does not say. `stage_of` returns 3 when flat and above the line and 1 "
        "when flat and below, so a stock basing at a high reads as Stage 3. That is why the Stage 3 "
        "warning is a watch flag, not a gate -- making it a gate would block legitimate bases.",
        "**Weekly bars mean weekly reaction.** The exit is a weekly close below the line, so a "
        "stock can fall for four sessions before the rule looks. Weinstein placed real stop orders "
        "for exactly this reason; this strategy's stop is held between weekly decisions, which is "
        "closer to his practice than a weekly-only exit would be.",
        "**The screen gates are daily and the strategy's are weekly.** G1-G3 come from the "
        "`near_highs` screen on daily bars, which is the closest available proxy for Weinstein's "
        "universe and is not the same thing as his conditions. A stock can pass a daily 200-day "
        "test and fail the weekly 30-week one.",
        "**The sector filter is absent.** The guide requires the stock's sector index to be in "
        "Stage 1 or 2, not Stage 4. Group strength is applied by the backtest cross-sectionally "
        "(`--min-group-rs`) rather than as a stage, which is a related but different test.",
        "**Overhead supply is noted, not enforced.** The guide says to avoid stocks with a band of "
        "trapped buyers just above the breakout. The plan reports the nearest overhead level so it "
        "is visible, but no gate rejects on it.",
    )
    status = (
        "NOT YET MEASURED. The stage model is validated against the guide's Trent narrative "
        "(Stage 2 from August 2023 through October 2024, close 2,049 to 7,128; Stage 4 by March "
        "2025) but no backtest has been run, so there is no result to report and nothing here "
        "should be read as one. Expect it to resemble the other per-symbol swing strategies: all "
        "six measured so far have NEGATIVE selection, between -0.38 and -4.48, which is worse than "
        "a 10-month moving average with no edge at all (see `ma_trend`). The reason to measure this "
        "one anyway is that it is the only WEEKLY strategy here, and weekly decisions are the one "
        "structural difference none of the others test."
    )
    gate_docs = {
        "G1": "H1: the close is above its 200-day average.",
        "G2": "H2: the 200-day average is not falling.",
        "G3": "H3: the close is within the screen's distance of its 52-week high.",
        "G4": "The weekly close is above the {MA_WEEKS}-week simple average of weekly closes.",
        "G5": "That average is more than {FLAT_TOL_PCT}% higher than it was {SLOPE_WEEKS} weeks ago "
              "-- the line is rising, which is what makes it Stage 2 rather than Stage 1.",
        "G6": "Relative strength is not deteriorating: the stock has at least matched the index over "
              "{RS_WEEKS} weeks.",
        "G7": "Forest before trees: the market's own index is not in Stage 4.",
    }
    watch_docs = {
        "W1": "The breakout week's volume was below {VOL_MULT}x the previous {VOL_WEEKS} weeks' "
              "average. Weinstein treated volume as confirmation, so this is noted but never blocks.",
        "W2": "Stage 3 warning: the {MA_WEEKS}-week line has flattened to within {FLAT_TOL_PCT}% "
              "after an advance, which is where a top forms.",
        "W3": "The structural stop sits more than {MAX_STOP_PCT}% below the entry, so the position "
              "has to be cut rather than taken at normal size.",
    }
    setup_docs = {
        STG01: "The weekly close clears {RESISTANCE_WEEKS}-week resistance for the first time, with "
               "the {MA_WEEKS}-week line rising beneath it and the base at least {BASE_MIN_WEEKS} "
               "weeks old.",
    }
    entry_rules = (
        "Bought at the close of the breakout week. The guide's alternative is the next session's "
        "open; on weekly bars the difference is one session of drift and it is not modelled.",
        "All seven gates must pass and the setup must fire in the same week. A breakout that happens "
        "while the market is in Stage 4 is not taken.",
        "No pyramiding and no half-position-on-the-pullback variant: the guide offers it, and adding "
        "it would mean two entry prices per trade, which the plan has no way to express.",
    )
    exit_rules = (
        "A weekly close below the {MA_WEEKS}-week average -- the main exit, and the one that defines "
        "the method. Everything is held through intra-week noise above the line.",
        "Or the stop, just below the higher of the line at entry and the base's low, which is held "
        "continuously rather than checked weekly.",
        "No profit target. The target shown on the plan is the base's own height projected above the "
        "breakout and is REPORTING ONLY -- the guide sets no target and the trend ends the trade.",
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "Every gate passes and the week closed above "
                                 "{RESISTANCE_WEEKS}-week resistance on at least {VOL_MULT}x volume.",
        "TRADE_ON_TRIGGER": "A valid Stage 1 base with the {MA_WEEKS}-week line already rising "
                            "beneath it, but resistance not yet cleared: a buy stop rests just "
                            "above it. This is the guide's variant for anyone watching daily.",
        "WATCH_WAIT": "A valid setup held back -- the breakout came on light volume, the line has "
                      "flattened into a Stage 3 warning, or the structural stop is more than "
                      "{MAX_STOP_PCT}% away.",
        "AVOID": "A gate failed, or there is no base to trade.",
    }
    param_docs = (
        ("The line", "MA_WEEKS", "Weeks in the simple average of weekly closes."),
        ("Slope window", "SLOPE_WEEKS", "Weeks over which the line's slope is measured."),
        ("Flat band", "FLAT_TOL_PCT", "Percent either way that counts as flat rather than trending."),
        ("Base length", "BASE_MIN_WEEKS", "Minimum weeks of sideways movement before a breakout counts."),
        ("Base depth", "BASE_MAX_DEPTH_PCT", "Maximum high-to-low depth for a window to count as a base."),
        ("Resistance", "RESISTANCE_WEEKS", "Weeks whose highest weekly high defines resistance."),
        ("RS window", "RS_WEEKS", "Weeks over which the stock must match the index."),
        ("Volume", "VOL_MULT", "Breakout week's volume against the previous weeks' average."),
        ("Maximum stop", "MAX_STOP_PCT", "Beyond this the position is flagged for resizing."),
    )
    backtest_args = "--exit-mode ma --no-target"

    # ---------- screen ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        """The daily proxy for Weinstein's universe, as of one row.

        Daily because the backtest's pre-filter walks daily rows and a row carries no weekly
        history. The weekly conditions are gates G4-G6, applied in `evaluate` where the full
        weekly frame exists.
        """
        ok, why = tradable_point_in_time(cfg, last)
        if not ok:
            return False, why
        close, s200 = last.get("close"), last.get("sma200")
        if any(pd.isna(v) for v in (close, s200)):
            return False, "insufficient history"
        if float(close) <= float(s200):
            return False, "close is not above the 200-day"
        return True, "passed"

    # ---------- the market's own stage ----------

    _mkt_stage: dict = {}

    @classmethod
    def _market_stage_weeks(cls, market_key: str):
        """{week-ending date: stage} for the market index, computed once per market.

        Cached on the class for the same reason rs_leaders caches its recovery window: every
        symbol on every bar asks the identical question of the identical series, and recomputing
        it per row dominated the scan.
        """
        if market_key in cls._mkt_stage:
            return cls._mkt_stage[market_key]
        from ..config import MARKETS
        from ..core import indicators as ind
        from ..marketdata import cache
        b = cache.load_cached(market_key, MARKETS[market_key].benchmark_ticker)
        if b is None or b.empty:
            cls._mkt_stage[market_key] = None
            return None
        wk = ind.resample_weekly(b)
        line = wk["close"].rolling(MA_WEEKS).mean()
        out = {}
        for i in range(MA_WEEKS + SLOPE_WEEKS, len(wk)):
            sub = wk.iloc[: i + 1]
            st, _ = line_state(line.iloc[: i + 1])
            above = float(sub["close"].iloc[-1]) > float(line.iloc[i])
            out[wk.index[i]] = (2 if above else 1) if st == "rising" else (
                (4 if not above else 3) if st == "falling" else (3 if above else 1))
        cls._mkt_stage[market_key] = out
        return out

    def market_risk_off(self, market_key: str, default: bool) -> bool:
        """Live: no new buys while the market index is itself in Stage 4."""
        stages = self._market_stage_weeks(market_key)
        if not stages:
            return default
        last_week = max(stages)
        return stages[last_week] == 4

    # ---------- evaluation ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        wk = ctx.weekly
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        self.apply_screen(ctx, result)

        if len(wk) < MA_WEEKS + SLOPE_WEEKS + 1:
            for g in ("G4", "G5", "G6", "G7"):
                result.fail(g, "insufficient weekly history")
            result.recompute_first_fail()
            return result

        line = ma30(wk)
        lv = float(line.iloc[-1]) if pd.notna(line.iloc[-1]) else float("nan")
        wclose = float(wk["close"].iloc[-1])
        state, slope = line_state(line)

        if lv != lv:
            result.fail("G4", "30-week average not available")
        elif wclose > lv:
            result.ok("G4", f"weekly close {wclose:.2f} above the 30-week line {lv:.2f}")
        else:
            result.fail("G4", f"weekly close {wclose:.2f} is below the 30-week line {lv:.2f}")

        if state == "rising":
            result.ok("G5", f"30-week line {slope:+.2f}% over {SLOPE_WEEKS} weeks")
        else:
            result.fail("G5", f"30-week line is {state} ({slope:+.2f}% over {SLOPE_WEEKS} weeks)")

        # Relative strength: the stock against the index over RS_WEEKS, both on weekly closes.
        mkt = _market_of(ctx.symbol)
        bench_wk = self._bench_weekly(mkt)
        if bench_wk is None or len(wk) <= RS_WEEKS:
            result.ok("G6", "no benchmark stored — relative strength not checked")
        else:
            b = bench_wk["close"].reindex(wk.index).ffill()
            if len(b.dropna()) <= RS_WEEKS:
                result.ok("G6", "insufficient overlapping benchmark history")
            else:
                s_ret = wclose / float(wk["close"].iloc[-1 - RS_WEEKS]) - 1
                b_ret = float(b.iloc[-1]) / float(b.iloc[-1 - RS_WEEKS]) - 1
                if s_ret >= b_ret:
                    result.ok("G6", f"{s_ret * 100:+.1f}% vs the index's {b_ret * 100:+.1f}% "
                                    f"over {RS_WEEKS} weeks")
                else:
                    result.fail("G6", f"lagging the index over {RS_WEEKS} weeks "
                                      f"({s_ret * 100:+.1f}% vs {b_ret * 100:+.1f}%)")

        stages = self._market_stage_weeks(mkt)
        if not stages:
            result.ok("G7", "no benchmark stored — market stage not checked")
        else:
            prior = [d for d in stages if d <= wk.index[-1]]
            mstage = stages[max(prior)] if prior else 0
            if mstage == 4:
                result.fail("G7", "the market index is in Stage 4")
            else:
                result.ok("G7", f"market index in Stage {mstage or 'unknown'}")

        # ---- the base, its resistance, and the breakout week
        hist = wk.iloc[:-1]
        resistance = (float(hist["high"].iloc[-RESISTANCE_WEEKS:].max())
                      if len(hist) >= RESISTANCE_WEEKS else float("nan"))
        # The LONGEST contained range ending last week: walk back from the cap and take the first
        # window whose high-to-low depth is within BASE_MAX_DEPTH_PCT. Longest rather than
        # shortest, because a 40-week base is a stronger setup than a 12-week one and taking the
        # shortest qualifying window would report every long base as a minimal one.
        base_weeks, base_depth = 0, float("nan")
        for n in range(min(len(hist), BASE_MAX_WEEKS), BASE_MIN_WEEKS - 1, -1):
            w = hist.iloc[-n:]
            hi, lo = float(w["high"].max()), float(w["low"].min())
            if hi > 0 and (hi - lo) / hi * 100 <= BASE_MAX_DEPTH_PCT:
                base_weeks, base_depth = n, (hi - lo) / hi * 100
                break
        vol = float(wk["volume"].iloc[-1])
        vbase = (float(hist["volume"].iloc[-VOL_WEEKS:].mean())
                 if len(hist) >= VOL_WEEKS else float("nan"))
        vol_ratio = vol / vbase if vbase == vbase and vbase else float("nan")
        prev_close = float(hist["close"].iloc[-1]) if len(hist) else float("nan")

        # Two states, one setup. `broke` is the week that cleared resistance; `armed` is a valid
        # base with the line already rising beneath it and resistance still overhead, which is the
        # guide's own variant for anyone watching daily ("buy on the day the price clears
        # resistance, with a buy stop just above it"). Both are the same setup at different
        # moments, which is what the TRADE_ON_TRIGGER label exists for.
        base_ok = bool(resistance == resistance and base_weeks >= BASE_MIN_WEEKS
                       and wclose > lv and state == "rising")
        broke = bool(base_ok and prev_close <= resistance < wclose)
        armed = bool(base_ok and not broke and wclose <= resistance)
        result.setups[STG01] = broke or armed
        result.watch_flags["W1"] = bool(broke and not (vol_ratio >= VOL_MULT))
        result.watch_flags["W2"] = bool(state == "flat" and wclose > lv)
        if result.watch_flags["W1"]:
            result.watch_notes["W1"] = f"volume {vol_ratio:.2f}x the {VOL_WEEKS}-week average"
        if result.watch_flags["W2"]:
            result.watch_notes["W2"] = f"30-week line flat ({slope:+.2f}%) above the price's base"

        ctx.extras.update(
            broke_out=bool(broke),
            stage=stage_of(wk) or None,
            line_slope_pct=round(slope, 2) if slope == slope else None,
            resistance=round(resistance, 2) if resistance == resistance else None,
            base_weeks=base_weeks or None,
            base_depth_pct=round(base_depth, 2) if base_depth == base_depth else None,
            vol_ratio=round(vol_ratio, 2) if vol_ratio == vol_ratio else None,
            ma30=round(lv, 2) if lv == lv else None,
        )
        result.recompute_first_fail()
        return result

    _bench_wk: dict = {}

    @classmethod
    def _bench_weekly(cls, market_key: str):
        if market_key not in cls._bench_wk:
            from ..config import MARKETS
            from ..core import indicators as ind
            from ..marketdata import cache
            b = cache.load_cached(market_key, MARKETS[market_key].benchmark_ticker)
            cls._bench_wk[market_key] = ind.resample_weekly(b) if b is not None and len(b) else None
        return cls._bench_wk[market_key]

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        return result.has_setup

    def setup_quality(self, result: StrategyResult) -> float:
        return 1.0 if result.setups.get(STG01) else 0.0

    # ---------- plan ----------

    def build_plans(self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no Stage 2 breakout this week")
        e = ctx.extras
        line, resistance = e.get("ma30"), e.get("resistance")
        if line is None or resistance is None:
            return PlanChoice(None, None, "missing 30-week line / resistance")
        # A completed breakout is bought at the close; an armed base rests a buy stop one tick
        # above resistance, so the trade only happens if the market actually clears it.
        if e.get("broke_out"):
            entry = float(ctx.close)
        else:
            entry = round_tick(float(resistance) + cfg.tick_size, cfg.tick_size, "up")
        n = int(e.get("base_weeks") or BASE_MIN_WEEKS)
        base_low = float(ctx.weekly["low"].iloc[-(n + 1):-1].min())
        # "Just below the HIGHER of the line and the base's low" -- the higher, because a stop under
        # the base low when the line sits above it gives away far more than the method intends.
        structural = max(float(line), base_low)
        floor_ = entry * (1 - MAX_STOP_PCT / 100)
        result.watch_flags["W3"] = bool(structural < floor_)
        stop = round_tick(max(structural, floor_), cfg.tick_size, "down")
        if stop <= 0 or stop >= entry:
            return PlanChoice(None, None, "degenerate stop")
        risk = entry - stop
        # REPORTING ONLY: the guide sets no target, so this is the base's own height projected
        # above the breakout -- a conventional measured move, never a rule this strategy acts on.
        base_height = max(float(resistance) - base_low, risk)
        target = entry + base_height * BASE_TARGET_MULT
        r = (target - entry) / risk
        ctx.extras["structural_r"] = round(r, 2)
        from ..core import swings as sw
        plan = TradePlan(plan="STG", setup=STG01, entry=entry, stop=stop, target=target,
                         risk_per_share=risk, reward_per_share=target - entry, r_multiple=round(r, 2),
                         nearest_overhead_above_entry=sw.nearest_overhead_above(entry, ctx.overhead))
        return PlanChoice(plan, None,
                          f"resistance {resistance:.2f}, stop {(entry - stop) / entry * 100:.1f}% "
                          f"below entry ({'line' if float(line) >= base_low else 'base low'})")

    def classify(self, ctx, result, plan, sizing_result, earnings_days_away,
                 regime_downgrade_active) -> Decision:
        q = self.setup_quality(result)
        if not result.hard_gates_passed:
            return Decision(LABELS["AVOID"], LABELS["AVOID"],
                            f"fails {result.first_hard_fail}: "
                            f"{result.hard_notes.get(result.first_hard_fail, '')}", 0.0, 0.0, q)
        if plan is None or not plan.is_valid:
            return Decision(LABELS["AVOID"], LABELS["AVOID"], "no valid entry plan", 0.0, 0.0, q)
        risk_pct = plan.risk_per_share / plan.entry * 100
        if ctx.extras.get("broke_out"):
            label, reasons = "TRADE_HIGH_CONFIDENCE", ["Stage 2 breakout above 26-week resistance"]
        else:
            label, reasons = "TRADE_ON_TRIGGER", ["valid base, buy stop above resistance"]
        if result.watch_flags.get("W1"):
            label = "WATCH_WAIT"; reasons.append("breakout volume below the threshold")
        if result.watch_flags.get("W2"):
            label = "WATCH_WAIT"; reasons.append("30-week line flat: Stage 3 warning")
        if result.watch_flags.get("W3"):
            label = "WATCH_WAIT"; reasons.append(f"structural stop more than {MAX_STOP_PCT:g}% away")
        before = label
        # Weinstein's forest-before-trees rule again, this time at the portfolio level: the gate
        # G7 check is point-in-time on the signal week, and this is the live downgrade.
        if regime_downgrade_active and label.startswith("TRADE"):
            label = "WATCH_WAIT"; reasons.append("market not in an uptrend: no new buys")
        return Decision(LABELS[before], LABELS[label], "; ".join(reasons), risk_pct,
                        plan.r_multiple, q)

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        e = ctx.extras
        return {
            "stage": e.get("stage"), "line_slope_pct": e.get("line_slope_pct"),
            "resistance": e.get("resistance"), "base_weeks": e.get("base_weeks"),
            "vol_ratio": e.get("vol_ratio"), "ma30": e.get("ma30"),
            "base_depth_pct": e.get("base_depth_pct"),
            "structural_r": e.get("structural_r"),
        }
