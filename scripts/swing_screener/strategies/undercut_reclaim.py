"""Undercut and reclaim -- draft 0 of research/undercut-reclaim-spec.md (@ohiain on X).

In a leader's base, do not buy the obvious breakout of the pivot: buy when price undercuts the base's tested
support and closes back above it, with the stop under the undercut low, and again at the break of the first
bounce's high after a higher low.

  * candidates: Minervini's Trend Template without C1 (the `stage2` screen's C2-C8 as G1-G7), because the
    undercut of a base often dips under the 50-day;
  * the setups are core/undercut_reclaim.py's causal scan, with the numbers below: S1 the reclaim, S2 the
    higher high after a higher low, S3 the comparison entry (the same base's breakout, ENTRY_MODE 2 only);
  * each is bought at the signal session's close, sized so its stop risks the account's risk per trade; an S2
    in a stock held from S1 adds a tranche;
  * management is the backtest's `--exit-mode reclaim` (backtesting/portfolio_sim.py, the kell exit's
    tranches and adds): each tranche's own stop, everything at the exit line's signal (`exit_frame`).
"""

import pandas as pd

from ..config.base import MarketConfig
from ..core import indicators as ind
from ..core import undercut_reclaim as ur
from ..core.context import StockContext
from ..marketdata import corporate_actions
# the Trend Template's thresholds, named here so the docs render them and the fingerprint covers them
from ..screens.criteria import (MAX_PCT_BELOW_52W_HIGH, MIN_PCT_ABOVE_52W_LOW,  # noqa: F401
                                RS_MIN_RANK, RS_MIN_SCORE, SMA200_RISING_BARS)
from .base import DOWNGRADE_MAP, LABELS, Decision, PlanChoice, Strategy, StrategyResult, TradePlan
from .minervini_spec import _min_turnover, _without_liquidity_floor, trend_template_row
from .trend_pullback import round_tick

# ---- the scan (evaluate() reads these, through _params(); spec section 2)
BASE_BARS = 30            # the base: this many sessions ...
UNDERCUT_WINDOW = 5       # ... ending this many sessions before today; the undercut is in these sessions
BASE_MAX_PCT = 20.0       # the base's height, pivot ÷ support − 1, at most this %
MIN_TOUCHES = 2           # support tested: at least this many swing lows near it ...
TOUCH_PCT = 2.0           # ... each within this % of support ...
SWING_SEP = 5             # ... at least this many sessions apart
UNDERCUT_MAX_ATR = 1.5    # the undercut low at most this many ATR under support
HOLD_SPAN = 100           # the trend line the undercut must hold: the EMA of this many sessions (≈ weekly 21-EMA);
                          #   enrich_daily must carry ema<HOLD_SPAN> (it has ema10, 20, 21, 30, 100)
HOLD_ATR = 0.5            # no close under it by more than this many ATR
REARM_BARS = 30           # one S1 per base: none within this many sessions of the last
S2_WINDOW = 15            # S2 comes within this many sessions of its S1
BO_WINDOW = 30            # S3 (ENTRY_MODE 2): the breakout comes within this many sessions of its S1
MIN_ROOM_R = 2.0          # W2: flagged when the pivot is less than this many R above the entry
ENTRY_MODE = 1            # 1: the reclaim entries (S1, S2); 2: the same bases' breakout (S3) instead -- the comparison
S2_ONLY = 0               # 1: S2 only (S1 is found, never bought)

# ---- after the scan (build_plans / classify / the backtest's --exit-mode reclaim read these)
MAX_STOP_PCT = 8.0        # S1/S2: a stop further than this % under the entry is not bought; S3: raised to it
MIN_STOP_ATR = 0.0        # research switch (0 = off): every stop at least this many ATR under the entry
NOMINAL_TARGET_R = 3      # the plan's target when the pivot is not above the entry, for the R column only
EXIT_MODE = 1             # 1: the 9-day EMA closes under the 21-day (a cross); 2: a close under the 21-day by EXIT_BREAK_ATR ATR
EXIT_FAST_EMA = 9
EXIT_SLOW_EMA = 21
EXIT_BREAK_ATR = 0.5

S1, S2, S3 = "S1", "S2", "S3"
W1, W2 = "W1", "W2"
# a base can be undercut while the 50-day still lags above it: C1 is left out on purpose
_GATES = {"G1": "C2", "G2": "C3", "G3": "C4", "G4": "C5", "G5": "C6", "G6": "C7", "G7": "C8"}


def _params() -> ur.Params:
    """The scan's numbers, read at call time, so a `--const` override is the one used."""
    return ur.Params(base_bars=BASE_BARS, undercut_window=UNDERCUT_WINDOW, base_max_pct=BASE_MAX_PCT,
                     min_touches=MIN_TOUCHES, touch_pct=TOUCH_PCT, swing_sep=SWING_SEP,
                     undercut_max_atr=UNDERCUT_MAX_ATR, hold_col=f"ema{HOLD_SPAN}", hold_atr=HOLD_ATR, rearm_bars=REARM_BARS,
                     s2_window=S2_WINDOW, bo_window=BO_WINDOW)


def exit_frame(df: pd.DataFrame) -> pd.Series:
    """The exit signal on every session (backtesting/portfolio_sim.py's `--exit-mode reclaim` sells everything
    left at that close). EXIT_MODE 1: the session the fast EMA closes under the slow one, having been at or above
    it the session before -- so a position bought while the fast line is still under the slow one is sold only
    after the lines have crossed up and back down. EXIT_MODE 2: any close under the slow EMA by EXIT_BREAK_ATR ATR."""
    c = df["close"].astype(float)
    slow = ind.ema(c, EXIT_SLOW_EMA)
    if EXIT_MODE == 2:
        return (c < slow - EXIT_BREAK_ATR * df["atr14"].astype(float)).fillna(False)
    fast = ind.ema(c, EXIT_FAST_EMA)
    return ((fast < slow) & (fast.shift(1) >= slow.shift(1))).fillna(False)


class UndercutReclaimStrategy(Strategy):
    key = "undercut_reclaim"
    name = "Undercut and reclaim"
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-17",
         "Draft 0 of research/undercut-reclaim-spec.md, from @ohiain's diagrams: a {BASE_BARS}-session base no "
         "taller than {BASE_MAX_PCT}% with support tested {MIN_TOUCHES}+ times, undercut by at most "
         "{UNDERCUT_MAX_ATR} ATR, the {HOLD_SPAN}-day EMA held, bought on the reclaim (S1) and on the higher high "
         "after a higher low (S2); out on the {EXIT_FAST_EMA}/{EXIT_SLOW_EMA} EMA cross. ENTRY_MODE 2 buys the same "
         "bases' breakout instead, for the spec's comparison. No backtest informed any number."),
    )
    description = (
        "Leaders whose base support is undercut and reclaimed while the long trend holds, bought on the reclaim "
        "and on the next higher high -- not at the obvious breakout -- and sold on the 9/21-day EMA cross."
    )
    style = "pullback"
    horizon = "swing"
    selection = "time_series"
    gate_codes = tuple(_GATES)
    screen_key = "stage2"
    screen_gates = dict(_GATES)
    watch_codes = (W1, W2)
    setup_codes = (S1, S2, S3)
    setup_names = {S1: "Reclaim of support", S2: "Higher high after the reclaim",
                   S3: "Breakout of the same base (comparison)"}
    gate_titles = {
        "G1": "Above the 150-day", "G2": "Above the 200-day", "G3": "Averages stacked", "G4": "200-day rising",
        "G5": "Off the 52-week low", "G6": "Near the 52-week high", "G7": "Relative strength",
    }
    nominal_target = True
    min_bars = 300
    needs_ctx_extras = True
    extra_columns = ("support", "pivot", "undercut_low", "touches", "s1_stop", "s2_stop", "bo_stop")
    extra_numeric_columns = extra_columns
    signal_exempt_consts = ("MAX_STOP_PCT", "MIN_STOP_ATR", "NOMINAL_TARGET_R", "EXIT_MODE", "EXIT_FAST_EMA",
                            "EXIT_SLOW_EMA", "EXIT_BREAK_ATR")

    thesis = (
        "In a leader's base, the obvious buy is the breakout of the pivot, and everyone sees it. A dip under the "
        "base's tested support shakes out the holders whose stops sit just below it; if price closes back above "
        "support while the long trend holds, the sellers were exhausted. Buying that reclaim puts the stop a few "
        "percent away, under the undercut low, with the whole base above as room -- the same risk as a breakout buy "
        "for several times the reward, if the base resolves upwards. The price is more trades that fail inside the "
        "base. Taught in diagrams by @ohiain on X; the spec fixes the rules before any backtest."
    )
    how_it_works = (
        "**The idea.** research/undercut-reclaim-spec.md (draft 0), from four diagrams by @ohiain on X "
        "(research/creator-ohiain.md). The diagrams carry no numbers; every number here is a first guess, set "
        "before any backtest.",
        "**Qualify (G1-G7).** Minervini's Trend Template without its first test, the close above the 50-day: an "
        "undercut of a base's low often dips under it. The other seven apply.",
        "**The base, its undercut and the reclaim.** One pass over the daily bars (the pattern table below) finds "
        "a tight base with tested support, an undercut of that support that keeps the {HOLD_SPAN}-day EMA, and the "
        "first close back above support (S1). A later higher high after a higher low is S2.",
        "**Buy.** S1 or S2 on a session that passes every gate, at that session's close, sized so that its own stop "
        "risks the account's risk per trade. An S2 in a stock held from its S1 adds a tranche (while the first is "
        "in profit and the position is under full size).",
        "**Sell.** Each tranche at its own stop; everything left when the {EXIT_FAST_EMA}-day EMA closes under the "
        "{EXIT_SLOW_EMA}-day (EXIT_MODE 1, now {EXIT_MODE}). No target.",
        "**The comparison.** ENTRY_MODE = 2 (now {ENTRY_MODE}) buys the same bases at their breakout instead (S3), "
        "with the same stop and exit -- the obvious entry the diagrams say to avoid, on exactly the setups the "
        "reclaim buys. The spec's pass criteria compare the two.",
        "**Portfolio rules.** The backtest runs with the minervini strategy's portfolio rules (`--spec`): its costs, "
        "positions, RS rating of {RS_MIN_RANK}+, ranking, caps and market filter, without its results blackout.",
    )
    pattern_title = "The base, the undercut and the reclaim"
    pattern_intro = (
        "Bars are daily. ATR is the 14-day Wilder ATR. The **base** is the {BASE_BARS} sessions ending "
        "{UNDERCUT_WINDOW} sessions before today; **support** is its lowest low and the **pivot** its highest high. "
        "The **undercut window** is the {UNDERCUT_WINDOW} sessions before today."
    )
    pattern_docs = {
        "Base": "The pivot is at most {BASE_MAX_PCT}% above support.",
        "Tested": "At least {MIN_TOUCHES} swing lows in the base (each the lowest of the 2 sessions either side), "
                  "at least {SWING_SEP} sessions apart, each within {TOUCH_PCT}% of support.",
        "Undercut": "The undercut window's lowest low is under support, by at most {UNDERCUT_MAX_ATR} ATR.",
        "Hold": "No close from the undercut window's start to today is under the {HOLD_SPAN}-day EMA by more than "
                "{HOLD_ATR} ATR. The daily stand-in for the weekly 21-EMA: on daily bars a 21-day EMA cannot hold "
                "through an undercut of a six-week base (spec section 3).",
        "Reclaim": "Yesterday closed at or under support and today closes above it, with no reclaim in the previous "
                   "{REARM_BARS} sessions (one per base).",
        "Higher high": "Within {S2_WINDOW} sessions of a reclaim: the highest high from the reclaim to yesterday, "
                       "with at least one session after it; the lowest low since then (the higher low) above the "
                       "undercut low; today closes above that high. Once per reclaim.",
        "Breakout": "Within {BO_WINDOW} sessions of a reclaim: the first close above the base's pivot.",
        "End": "A close under the undercut low ends the watch for a higher high and a breakout.",
    }
    caveats = (
        "**Draft definitions.** The diagrams are schematic, with no numbers. Every threshold is a first guess, fixed "
        "before any backtest; one, the line the undercut must hold, was moved after a count of setups on stored "
        "prices (spec section 3), never on outcomes.",
        "**Daily bars for a weekly idea.** The creator speaks of weekly pivots; the base, support and the trend line "
        "here are daily stand-ins.",
        "**Tight stops.** The median stop on the frequency check was about 3% -- close to the one-bar stops that "
        "stopped out half of kell_cycle's US trades. MIN_STOP_ATR tests a wider one.",
        "**Bought at the close.** The reclaim is known only at the close; the diagrams may buy it intraday.",
        "**Survivorship.** The universe is today's stock lists; bases that broke down into a delisting are "
        "missing, which flatters a buy-the-reclaim rule.",
        "**No results rule.** Positions are held through results dates.",
        "**Run it with its flags** (`backtest_args`).",
        corporate_actions.CAVEAT_TRADED,
    )
    status = (
        "NOT YET RUN. v1.0 built 2026-11-17 from draft 0 of the spec. Pass criteria, fixed before any run (spec "
        "section 6), optimise stage, both markets: at least 100 closed trades per market; at least +0.25R a trade "
        "net of costs in each; the reclaim entry (ENTRY_MODE 1) beats the same bases' breakout entry (ENTRY_MODE "
        "2) in expectancy per trade and in CAGR in both; with the best 5% of trades removed, expectancy above zero "
        "in both. Verify only when all four pass."
    )
    gate_docs = {
        "G1": "Trend Template C2: the close is above the 150-day moving average.",
        "G2": "Trend Template C3: the close is above the 200-day moving average.",
        "G3": "Trend Template C4: the 50-day average is above the 150-day, which is above the 200-day.",
        "G4": "Trend Template C5: the 200-day average is higher than {SMA200_RISING_BARS} sessions ago.",
        "G5": "Trend Template C6: the close is at least {MIN_PCT_ABOVE_52W_LOW}% above the 52-week low.",
        "G6": "Trend Template C7: the close is within {MAX_PCT_BELOW_52W_HIGH}% of the 52-week high.",
        "G7": (
            "Trend Template C8: relative strength.\n\n"
            "- **In the scan:** the weighted RS score is at least {RS_MIN_SCORE}.\n"
            "- **In the backtest:** the signal's stock must also rate {RS_MIN_RANK}+ (1-99 across the market) on "
            "the signal date (`--spec`)."
        ),
    }
    watch_docs = {
        W1: ("A quiet reclaim.\n\n- **Test:** an S1 session's volume is under its 50-day average.\n- **Effect:** "
             "noted only. The creator's cycle diagram stresses volume; the reclaim diagrams do not show it."),
        W2: ("Little room.\n\n- **Test:** the base's pivot is less than {MIN_ROOM_R} R above the entry (the stop being "
             "the setup's own).\n- **Effect:** noted only."),
    }
    setup_docs = {
        S1: ("Reclaim of support: today is a reclaim (pattern table), with ENTRY_MODE 1 and S2_ONLY 0.\n\n"
             "- **Stop:** the undercut low.\n- **Entry:** a new position."),
        S2: ("Higher high after the reclaim: today is a higher high (pattern table), with ENTRY_MODE 1.\n\n"
             "- **Stop:** the higher low.\n- **Entry:** a new position, or an add to one held from its S1."),
        S3: ("Breakout of the same base, the comparison entry: today is a breakout (pattern table), with "
             "ENTRY_MODE 2 only.\n\n- **Stop:** the undercut low, raised to {MAX_STOP_PCT}% under the entry if "
             "further.\n- **Entry:** a new position."),
    }
    entry_rules = (
        "Signal. S1, S2 or S3 on a session that passes G1-G7, graded TRADE - HIGH CONFIDENCE. When two fire on one "
        "session the plan takes the first of S1, S2, S3.",
        "Order. Buy at that session's close (backtest: a close order, filled that session, plus slippage).",
        "Add (backtest). A signal in a stock already held, on a later session, buys another tranche at that close when "
        "every earlier tranche was bought below it and the position's value is under Max position size × equity.",
        "Market. No new buy or add on a session the market filter is risk-off (`--market-filter`, the minervini "
        "strategy's test under `--spec`).",
    )
    stop_rules = (
        "Where it goes. S1 and S3: the undercut low. S2: the higher low. With MIN_STOP_ATR above 0 (now "
        "{MIN_STOP_ATR}), at least that many ATR under the entry. Rounded down to the tick; it defines that "
        "tranche's 1R.",
        "Too wide. An S1 or S2 stop more than {MAX_STOP_PCT}% under the entry is not bought; an S3 stop is raised "
        "to {MAX_STOP_PCT}% under it.",
        "Each tranche keeps its own stop (backtest). The first session whose low touches it sells that tranche at the "
        "stop, or at the open if it opened below it. Stops never move.",
    )
    target_rules = (
        "There is no sell order at the target. The plan's target is the base's pivot, or entry + {NOMINAL_TARGET_R} "
        "R when the pivot is not above the entry, so that the plan has an R column. The backtest runs with "
        "`--no-target`.",
    )
    exit_rules = (
        "Each session after the entry, in this order (backtest, `--exit-mode reclaim`):",
        "1. The stops: each tranche whose stop is touched sells (see Stop).",
        "2. The exit line: EXIT_MODE 1 (now {EXIT_MODE}), the session the {EXIT_FAST_EMA}-day EMA closes under the "
        "{EXIT_SLOW_EMA}-day after being at or above it the session before, sells everything left at its close -- "
        "the creator's 9/21 crossback. A position bought while the fast line is under the slow one is sold only "
        "after they cross up and back down. EXIT_MODE 2: a close under the {EXIT_SLOW_EMA}-day EMA by "
        "{EXIT_BREAK_ATR} ATR (kell_cycle's EMA break).",
        "No other exits. A position still open when the backtest ends is marked at the last close.",
    )
    sizing_rules = (
        "Risk-based, per tranche. Shares = (equity × Risk per trade) ÷ (price paid − that tranche's stop), rounded "
        "down, and the whole position capped at Max position size × equity.",
        "Cash. When cash cannot buy the full size, the backtest buys what it can, but only if that is at least half "
        "the planned shares (`--min-fill 0.5`).",
        "Slots and caps. The minervini strategy's position count and open-risk cap (`--spec`); an add that would breach "
        "the open-risk cap is skipped.",
    )
    filter_rules = (
        "Liquidity: the minervini strategy's turnover floor. History: {min_bars} sessions, so the 200-day average "
        "and its slope exist; young listings are not judged.",
    )
    param_docs = (
        ("Base length", "BASE_BARS", "Sessions in the base."),
        ("Undercut window", "UNDERCUT_WINDOW", "Sessions before today in which the undercut comes; the base ends before them."),
        ("Base height", "BASE_MAX_PCT", "The pivot at most this % above support."),
        ("Support touches", "MIN_TOUCHES", "Swing lows near support the base needs."),
        ("Touch distance", "TOUCH_PCT", "A swing low within this % of support counts."),
        ("Touch spacing", "SWING_SEP", "Counted touches at least this many sessions apart."),
        ("Undercut depth", "UNDERCUT_MAX_ATR", "The undercut low at most this many ATR under support."),
        ("Trend line", "HOLD_SPAN", "The EMA the undercut must hold, in sessions (the daily stand-in for the weekly 21-EMA)."),
        ("Trend line slack", "HOLD_ATR", "No close under that EMA by more than this many ATR."),
        ("One per base", "REARM_BARS", "No reclaim within this many sessions of the last."),
        ("Higher-high window", "S2_WINDOW", "S2 within this many sessions of its reclaim."),
        ("Breakout window", "BO_WINDOW", "S3 within this many sessions of its reclaim."),
        ("Room", "MIN_ROOM_R", "W2: the pivot less than this many R above the entry is flagged."),
        ("Entry mode", "ENTRY_MODE", "1: the reclaim entries (S1, S2); 2: the same bases' breakout (S3), the comparison."),
        ("S2 only", "S2_ONLY", "1: only S2 is bought."),
        ("Maximum stop", "MAX_STOP_PCT", "S1/S2 not bought, S3 raised, when the stop is further than this % under the entry."),
        ("Minimum stop", "MIN_STOP_ATR", "Every stop at least this many ATR under the entry (0 = off). A research switch."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × R when the pivot is not above the entry, for the R column only."),
        ("Exit mode", "EXIT_MODE", "1: the fast EMA closes under the slow one; 2: a close under the slow EMA by Exit break depth."),
        ("Exit fast EMA", "EXIT_FAST_EMA", "EXIT_MODE 1: the fast line, in sessions."),
        ("Exit slow EMA", "EXIT_SLOW_EMA", "The slow line, in sessions."),
        ("Exit break depth", "EXIT_BREAK_ATR", "EXIT_MODE 2: ATRs under the slow EMA."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity each tranche risks between its price and its stop."),
        ("Max position size", "cfg.max_position_pct", "A position's full size, as a fraction of equity."),
        ("Tick size", "cfg.tick_size", "Stops are rounded down to this increment."),
    )
    backtest_args = "--spec --exit-mode reclaim --no-target --market-filter --results-blackout 0 --min-fill 0.5"

    # ---------- screen ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        """The minervini strategy's turnover floor, then the Trend Template without C1."""
        floor = _min_turnover(cfg, getattr(last, "name", None))
        v50, close = last.get("vol_sma50"), last.get("close")
        if pd.isna(v50) or pd.isna(close) or float(v50) * float(close) < floor:
            return False, f"turnover below {floor:,.0f} a day"
        return trend_template_row(_without_liquidity_floor(cfg), last, above_50=False)

    # ---------- gates and setups ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        self.apply_screen(ctx, result)
        row = ur.last(ctx.symbol, ctx.daily, _params())
        s1, s2, bo = bool(row.get("s1")), bool(row.get("s2")), bool(row.get("bo"))
        result.setups[S1] = s1 and ENTRY_MODE == 1 and not S2_ONLY
        result.setups[S2] = s2 and ENTRY_MODE == 1
        result.setups[S3] = bo and ENTRY_MODE == 2
        e = ctx.extras
        for k in self.extra_columns:
            v = row.get(k)
            e[k] = float(v) if v is not None and v == v else None
        active = next((c for c in self.setup_codes if result.setups.get(c)), None)
        if active == S1:
            last = ctx.daily.iloc[-1]
            v, v50 = float(last["volume"]), last.get("vol_sma50")
            if v50 is not None and v50 == v50 and v < float(v50):
                result.watch_flags[W1] = True
                result.watch_notes[W1] = f"reclaim volume {v / float(v50):.2f}× its 50-day average"
        if active is not None:
            stop = e.get({S1: "s1_stop", S2: "s2_stop", S3: "bo_stop"}[active])
            close, pivot = float(ctx.close), e.get("pivot")
            if stop is not None and pivot is not None and close > stop and (pivot - close) < MIN_ROOM_R * (close - stop):
                result.watch_flags[W2] = True
                result.watch_notes[W2] = f"pivot {(pivot - close) / (close - stop):.1f} R above the entry"
        result.recompute_first_fail()
        return result

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        return result.has_setup

    def setup_quality(self, result: StrategyResult) -> float:
        return 2.0 if result.has_setup else 0.0

    # ---------- plan ----------

    def build_plans(self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig) -> PlanChoice:
        setup = next((c for c in self.setup_codes if result.setups.get(c)), None)
        if setup is None:
            return PlanChoice(None, None, "no active setup")
        entry = float(ctx.close)
        e = ctx.extras
        level = e.get({S1: "s1_stop", S2: "s2_stop", S3: "bo_stop"}[setup])
        if level is None:
            return PlanChoice(None, None, f"{setup}: no stop level recorded")
        level = float(level)
        if MIN_STOP_ATR > 0:
            level = min(level, entry - MIN_STOP_ATR * ctx.atr)
        if (entry - level) / entry * 100 > MAX_STOP_PCT:
            if setup != S3:
                return PlanChoice(None, None, f"{setup}: stop {(entry - level) / entry * 100:.1f}% away, over "
                                              f"{MAX_STOP_PCT:g}%")
            level = entry * (1 - MAX_STOP_PCT / 100)
        stop = round_tick(level, cfg.tick_size, "down")
        risk = entry - stop
        pivot = e.get("pivot")
        target = float(pivot) if pivot is not None and pivot > entry else entry + NOMINAL_TARGET_R * risk
        plan = TradePlan(plan="UR", setup=setup, entry=entry, stop=stop, target=target,
                         risk_per_share=risk, reward_per_share=target - entry,
                         r_multiple=(target - entry) / risk if risk > 0 else float("nan"),
                         nearest_overhead_above_entry=None)
        return PlanChoice(plan, None, f"{self.setup_names[setup]}; stop {stop:g}")

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        return {"order": "close", "add_only": False}

    # ---------- decision ----------

    def classify(self, ctx, result, plan, sizing_result, earnings_days_away, regime_downgrade_active) -> Decision:
        if not result.hard_gates_passed:
            code = result.first_hard_fail
            return Decision("AVOID", "AVOID", f"fails hard gate {code}: {result.hard_notes.get(code, '')}",
                            float("nan"), float("nan"), 0.0)
        if not plan.is_valid:
            return Decision("AVOID", "AVOID", "degenerate plan (non-positive or undefined risk)",
                            float("nan"), float("nan"), 0.0)
        risk_pct = plan.risk_per_share / plan.entry * 100
        if sizing_result.too_large:
            label, reason = "WATCH_WAIT", "too large for account"
        else:
            label, reason = "TRADE_HIGH_CONFIDENCE", f"{self.setup_names[plan.setup]}; stop {risk_pct:.1f}% away"
        before = label
        if regime_downgrade_active:
            label = DOWNGRADE_MAP[label]
            reason += "; market-regime downgrade applied"
        return Decision(LABELS[before], LABELS[label], reason, risk_pct, plan.r_multiple, self.setup_quality(result))

    def report_extras(self, ctx: StockContext, result: StrategyResult, plan: TradePlan | None) -> dict:
        e = ctx.extras
        r = lambda v: round(float(v), 2) if v is not None and v == v else None
        return {k: r(e.get(k)) for k in self.extra_columns}

    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The base's support and pivot, the undercut low, and the setup's stop."""
        e = sig.get("extras") or {}
        d = str(sig["date"])
        active = [k for k, v in (sig.get("setups") or {}).items() if v]
        out: list[dict] = []
        if e.get("support") and e.get("pivot"):
            out.append({"shape": "box", "bars": BASE_BARS + UNDERCUT_WINDOW, "to": d, "top": float(e["pivot"]),
                        "bottom": float(e["support"]), "role": "base", "label": "the base"})
        elif e.get("pivot"):
            out.append({"shape": "level", "bars": 20, "to": d, "price": float(e["pivot"]), "role": "pivot",
                        "label": f"pivot {float(e['pivot']):g}"})
        for code, key in ((S1, "s1_stop"), (S2, "s2_stop"), (S3, "bo_stop")):
            if code in active and e.get(key):
                out.append({"shape": "level", "bars": 10, "to": d, "price": float(e[key]), "role": "stop",
                            "label": f"{self.setup_names[code]} stop {float(e[key]):g}"})
                break
        if active:
            out.append({"shape": "note", "at": d, "text": f"Undercut and reclaim {d}: " + ", ".join(
                self.setup_names.get(c, c) for c in active)})
        return out or super().chart_anatomy(sig)
