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

import math

import pandas as pd

from ..config.base import MarketConfig
from ..core import pattern_spec as ps
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

# ---- §2 and §12: the spec's parameters
K_MINOR, K_MAJOR = 3, 8
MIN_SWING_PCT, ATR_MULT = 3.0, 1.5
TOL_PCT, TOL_ATR_MULT = 3.0, 0.75
BO_BUFFER = 0.5          # BO-01, %
BO_VOL = 1.4             # BO-02, x the 50-day average
MAX_WAIT = 20            # BO-04, days from completion to expiry
FAIL_DAYS = 10           # BO-05, days in which a close back through T fails it
HORIZON = 60             # §3.3, bars over which an outcome is recorded
# O'Neil's W (research/learn-bases.md §4), which DBOT is since v1.3
W_UNDERCUT_MAX = 5.0     # the second low sits 0 to this % under the first
W_MIN_DEPTH, W_MAX_DEPTH = 20.0, 35.0   # OW-01: the high before B to the lower low, %
W_MIN_DAYS = 35          # OW-02: that high to the second low, about 7 weeks
TRIPLE_MAX_DRIFT = 1.5   # TL-LV: a triple's lows may not step one way by more than this %
CUP_RIGHT_LEFT_MIN = 0.5  # CH-06: a cup's recovery (B to C) takes at least this × its decline (A to B)
# A cup's rims are a resistance zone, graded rather than judged (CH-03 stays the outer limit):
RIM_IDEAL_PCT = 3.0       # the right rim within this % of the left: "ideal"
RIM_OK_PCT = 8.0          # ...within this: "acceptable"; beyond it (inside CH-03): "loose"
RIM_IDEAL_BONUS = 0.2     # setup quality added for ideal rims (it ranks signals for the position slots)
RIM_LOOSE_PENALTY = 0.3   # ...and taken off for loose ones
PARAMS = ps.PatternParams(
    k_minor=K_MINOR, k_major=K_MAJOR, min_swing_pct=MIN_SWING_PCT, atr_mult=ATR_MULT,
    tol_pct=TOL_PCT, tol_atr_mult=TOL_ATR_MULT, bo_buffer=BO_BUFFER / 100, bo_vol=BO_VOL,
    max_wait=MAX_WAIT, fail_days=FAIL_DAYS, horizon=HORIZON,
    oneil_undercut=(0.0, W_UNDERCUT_MAX), oneil_depth=(W_MIN_DEPTH, W_MAX_DEPTH),
    oneil_min_days=W_MIN_DAYS, triple_max_drift=TRIPLE_MAX_DRIFT, right_left_min=CUP_RIGHT_LEFT_MIN,
    rim_ideal_pct=RIM_IDEAL_PCT, rim_ok_pct=RIM_OK_PCT, trigger_clears_rims=True,
)
# bars after the breakout bar on which a pattern is still an entry. The detector keeps a confirmed
# pattern "live" for HORIZON bars to record its outcome; that is NOT an entry window — buying on
# any of those bars buys pullbacks into an old pivot and re-buys after a stop.
BREAKOUT_MAX_AGE = 0

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
# long-only book a top is a veto (gate G2, flag W1), never a setup.
BULLISH: dict[str, tuple[str, object]] = {
    CUP: ("§4", lambda d: ps.detect_cup(d, PARAMS)),
    CUPNH: ("§4", lambda d: ps.detect_cup(d, PARAMS, require_handle=False)),
    DBOT: ("§5.1", lambda d: ps.detect_double_bottom(d, PARAMS, oneil_w=True)),
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
# what each code is, in words: the Strategies page lists these, and the
# backtest's trades panel names the pattern a trade was taken on with them
PATTERN_NAMES = {
    CUP: "Cup with handle", CUPNH: "Cup without handle", DBOT: "Double bottom (O'Neil W)",
    TBOT: "Triple bottom", IHS: "Inverse head and shoulders",
    ATRI: "Ascending triangle", SYMM: "Symmetrical triangle", FWDG: "Falling wedge",
    RECT: "Rectangle", FBASE: "Flat base", FLAG: "Bull flag or pennant",
    HTF: "High tight flag",
}
# the detectors' point names, as the chart labels them
POINT_NAMES = {
    "A": "left lip", "B": "low", "C": "right lip", "D": "handle low",
    "B1": "low 1", "P1": "peak", "B2": "low 2", "P2": "peak", "B3": "low 3",
    "LS": "left shoulder", "N1": "neck", "HD": "head", "N2": "neck",
    "RS": "right shoulder", "P0": "pole start", "X": "flag low", "S": "start",
}
# a double bottom reuses the cup's letters for different points, and a double top mirrors it
POINT_NAMES_BY_CODE = {DBOT: {"B": "low 1", "C": "peak", "D": "low 2"},
                       "double top": {"B": "top 1", "C": "trough", "D": "top 2"}}
BEARISH = {
    "double top": lambda d: ps.detect_double_top(d, PARAMS),
    "head and shoulders top": lambda d: ps.detect_head_shoulders(d, PARAMS),
    "rising wedge": lambda d: _of_kind(d, (ps.RISING_WEDGE,)),
    "descending triangle": lambda d: _of_kind(d, (ps.DESCENDING,)),
}


def _of_kind(daily, kinds: tuple[str, ...]) -> dict:
    return ps._pick_kinds(ps.detect_boundaries(daily, PARAMS), kinds, ps.TR_RULES)


def _live(res: dict) -> bool:
    """Complete, or confirmed within the outcome horizon — a topping pattern vetoes for that long."""
    return bool(res.get("ok") and res.get("metrics", {}).get("is_live"))


def _tradeable(res: dict) -> bool:
    """A bullish pattern worth acting on: COMPLETE (a buy-stop can rest at its trigger) or
    breaking out on this very bar — never an old breakout still inside its outcome horizon."""
    if not res.get("ok"):
        return False
    if res.get("state") == ps.COMPLETE:
        return bool(res.get("metrics", {}).get("is_live"))
    age = res.get("metrics", {}).get("bars_since_breakout")
    return res.get("state") == ps.CONFIRMED and age is not None and age <= BREAKOUT_MAX_AGE


class ChartPatternSpecStrategy(Strategy):
    selection = "time_series"
    family = "chart_pattern"
    version = "1.8"
    changelog = (
        ("1.8", "2026-10-17",
         "A cup's rims are a resistance zone. The right rim was either inside CH-03's band (85-103% of the "
         "left) or rejected, and every cup inside it counted the same. Now the gap is graded — within "
         "{RIM_IDEAL_PCT}% ideal, within {RIM_OK_PCT}% acceptable, beyond that loose — and the grade moves "
         "setup quality (+{RIM_IDEAL_BONUS} / -{RIM_LOOSE_PENALTY}), which ranks signals when slots are "
         "short: a clean resistance level makes the pattern and its breakout easier to trade, but a few "
         "percent of misalignment is no reason to reject one. And a cup with a handle's trigger is raised "
         "to the left rim when the handle's high sits under it (PatternParams.trigger_clears_rims): with "
         "the right rim up to 15% below the left, the old trigger could buy under the left rim's supply."),
        ("1.7", "2026-10-16",
         "Eligibility floor lowered from 320 bars to the screen's own {min_bars} (screens.base.MIN_BARS). "
         "320 was never something the detectors needed: they look back up to PatternParams.lookback, guard "
         "their own shorter minimums, and a truncated prior-trend window only makes PT-01/PT-02 harder to "
         "pass. The gap mattered once screening began enforcing min_bars alike with the backtest and the "
         "pattern endpoint: a stock with 13-15 months of history (NIQ, 311 bars) passed near_highs but was "
         "refused by the strategy. About 80 US and 61 India stocks sat in that gap on 2026-10-16, and in a "
         "backtest every new listing now qualifies 60 bars (about three months) sooner. "
         "Made the same day as 1.6, which had already moved the spec id, before any 1.6 run."),
        ("1.6", "2026-10-16",
         "Gate, watch and setup codes renamed to one scheme shared by every strategy: G1..Gn for the hard "
         "gates, W1..Wn for the watch flags, S1..Sn for the setups. "
         "The old letters meant nothing and collided across strategies: B1-B4 were minervini's WATCH flags "
         "and breakout's GATES, so one string blocked a trade in the first and merely noted something in "
         "the second. The prefix now states the only thing that matters when reading a drop reason -- "
         "whether the code can stop a trade. No rule changed, but the code tuples are part of the "
         "fingerprint, so this moves the spec id and earlier runs stay under their own versions."
         "The pattern names (CUP, IHS, DBOT...) stay as setup codes: a pattern's name identifies it "
         "better than a number ever could."),
        ("1.5", "2026-10-13",
         "Entries only on the breakout bar, and one entry per pattern. The detector keeps a "
         "confirmed pattern live for {HORIZON} bars to record its outcome, and that window was "
         "also the entry window: every bar up to {HORIZON} days after a breakout re-fired the "
         "signal, so the strategy bought pullbacks into an old pivot and re-bought after a stop. "
         "In the v1.1 India run, 120 of 600 trades (20%) re-used a pattern another trade had "
         "already traded and 82 (13%) entered more than 5% above the trigger; AAPL bought the "
         "same Dec 2025 cup on 10 Jun 2026 and again on 29 Jun, both well after its breakout. "
         "Gate S1 now admits a CONFIRMED pattern only on its breakout bar ({BREAKOUT_MAX_AGE} "
         "bars after), and each pattern carries its identity (code + first key point) so the "
         "simulator never enters it twice (EN-04). Cups must also recover in at least "
         "{CUP_RIGHT_LEFT_MIN}x the time they took to fall (CH-06): AAPL's cup fell for 30 "
         "bars and recovered in 13, a V the spec's 25%-of-the-cup floor let through."),
        ("1.4", "2026-10-12",
         "A triple bottom's lows must be LEVEL, not stepping (TL-LV): when each low is higher "
         "than the last, or each lower, the first-to-third drift may not exceed "
         "{TRIPLE_MAX_DRIFT}%. The spec only asked all three to be within tolerance (3% here), "
         "which let ITC.NS's 2015 range through -- lows 192.6, 194.5, 197.1, a rising floor "
         "with spike peaks, traded on 2 Nov 2015 and stopped at -1R."),
        ("1.3", "2026-10-12",
         "Two buy rules brought in line with O'Neil (research/learn-bases.md §4). A cup "
         "without a handle triggers at the OLD HIGH max(A, C), not at the right lip C: CH-03 "
         "lets C sit up to 15% under A, so buying through C bought under the left lip's "
         "overhead supply. DBOT is now O'Neil's W -- a continuation base after a prior "
         "UPTREND, second low 0-{W_UNDERCUT_MAX}% under the first, {W_MIN_DEPTH}-{W_MAX_DEPTH}% "
         "deep from the high it corrects and at least {W_MIN_DAYS} bars long -- in place of "
         "the textbook reversal (two equal lows after a decline), which the near_highs screen "
         "mostly excluded anyway."),
        ("1.2", "2026-10-12",
         "A cup without a handle now expires. It was judged as re-completing on every bar, so "
         "BO-04's clock never started and an old cup stayed live whenever price came back to "
         "its rim: ITC.NS traded a cup whose right lip (2013-09-20) was 20 months old. It now "
         "completes once, {K_MAJOR} bars after the right lip, and walks §3.2 like a double "
         "bottom — void after {MAX_WAIT} bars without a breakout, or on a close under the cup "
         "low. CUPNH was 185 of 253 trades in the 2026-10-09 run, so every result measured "
         "before this version is dominated by stale cups."),
        ("1.1", "2026-10-10",
         "The point-in-time pre-filter no longer applies cfg.screener.min_price. The floor keeps "
         "live screening out of penny stocks, but a backtest reads it against SPLIT-ADJUSTED "
         "history, so it deleted the early years of exactly the stocks that went up most -- "
         "splitting is what winners do. NVDA traded about $15 in 2013 on $126m a day, 12x the "
         "liquidity floor; stored back-adjusted through a 4:1 and a 10:1 split that is $0.39, "
         "under the $10 US floor, so NVDA did not qualify until 2020-07-08 and SMCI not until "
         "2023. Liquidity is now carried by min_dollar_volume alone, which is split-invariant "
         "(close falls by the split factor, volume rises by it). Live screening keeps the price "
         "floor in screens/base.py, where today's price really is today's price. On NVDA this "
         "takes evaluable bars from 815 to 1,841 of 3,464; India is unaffected (min_price=0)."),
        ("1.0", "2026-10-10",
         "v1 baseline, built to the written detection specification: twelve patterns with section-referenced definitions - cup, cup-no-handle, double bottom, triple bottom, inverse head-and-shoulders, flat base, bull flag, ascending triangle, symmetrical triangle, falling wedge, rectangle and high tight flag."),
    )
    key = "chart_pattern"
    name = "Chart patterns"
    #: The LEAD, not a catalogue. It sits above the tabs, so it is the only description on
    #: Candidates and Backtests, which have no Overview. The twelve tradable patterns and the four
    #: vetoes are listed in how_it_works, where there is room to say what each one is.
    description = (
        "The written chart-pattern specification, rule for rule: breakouts from twelve bullish "
        "patterns, vetoed by four topping ones, traded at the spec's own trigger, invalidation "
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

    gate_codes = ("G1", "G2", "G3", "G4", "G5")
    watch_codes = ("W1", "W2", "W3")
    setup_codes = tuple(BULLISH)
    needs_ctx_extras = True
    extra_columns = (
        "pattern", "pattern_name", "pattern_state", "trigger", "invalidation", "measured_target",
        "pct_from_trigger", "structural_r", "topping_pattern", "pattern_note",
        "first_failed_rule",
    )
    extra_numeric_columns = ("trigger", "invalidation", "measured_target",
                             "pct_from_trigger", "structural_r")
    # The strategy's eligibility floor, applied alike by screening, the backtest and the live
    # pattern endpoint. NOT a detector requirement: the detectors examine up to
    # `PatternParams.lookback` bars, guard their own shorter minimums (`ps.min_scan_bars`), and
    # a truncated prior-trend window only makes PT-01/PT-02 harder to pass. The screen's own
    # floor is `screens.base.MIN_BARS`, and since v1.7 this matches it: the strategy refuses no
    # stock the screen admits on history alone. Changing it is a behaviour change (version bump).
    min_bars = 260

    status = (
        "Not yet measured at v1.8 (which grades cup rims and lifts a cup's trigger to its left rim). Last measured at v1.5, with no demonstrated edge: India, full "
        "universe from 2013 (bracket exits, measured 2026-10-14): 3.61% CAGR against the index's "
        "11.6%, max drawdown -27.8%; no US v1.5 run was recorded. v1.6 renamed codes only and "
        "v1.7 admits stocks with {min_bars} bars of history instead of 320. (v1.2 stopped stale "
        "cups-without-handle from trading, v1.3 moved "
        "two buy rules to O'Neil's, v1.4 requires a triple bottom's lows to be level and v1.5 buys "
        "only on the breakout bar, once per pattern.) The earlier v1.0 comparison, dominated by stale "
        "cups and late and repeat entries: backtested 2026-10-09 it lost by less than its sibling: -0.93% "
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
        "**Patterns it detects (setups, long only):** cup with handle (CUP), "
        "cup without handle (CUPNH), double bottom (DBOT), triple bottom "
        "(TBOT), inverse head and shoulders (IHS), ascending triangle (ATRI), "
        "symmetrical triangle (SYMM), falling wedge (FWDG), rectangle (RECT), "
        "flat base (FBASE), bull flag or pennant (FLAG) and high tight flag "
        "(HTF) — eleven pattern types, the cup counted with and without its "
        "handle. Each is detected by its own numbered rules; the report names "
        "which fired and, when none did, the first rule that failed.",
        "**Patterns it detects as vetoes, never traded:** double top, head and "
        "shoulders top, rising wedge and descending triangle. A confirmed one "
        "fails gate G2; one still forming raises flag W1.",
        "**Which pattern a trade was taken on** is the highest-priority live "
        "match on the signal bar; it is the trade's `setup`, named in the "
        "backtest trades panel, and the chart draws that pattern — its swing "
        "points, fitted lines, trigger, invalidation and measured target.",
        "**Gates S1-S5** require a bullish pattern that is complete or breaking "
        "out on this bar, no CONFIRMED topping pattern on the same chart, no "
        "earnings inside {EARNINGS_DAYS} trading days, ATR under {MAX_ATR_PCT}% "
        "of price, and price no more than {MAX_CHASE_PCT}% past the trigger.",
        "**One entry per pattern, on its breakout bar.** A pattern that broke out "
        "earlier is history even while its outcome is still being recorded, and a "
        "pattern already traded is never bought again — stopped out or not.",
        "**Patterns expire.** A double, triple, head and shoulders or cup without a handle "
        "completes once and is void if it does not break out within {MAX_WAIT} bars (BO-04); "
        "a cup with a handle is bounded by its handle's 5-25 days instead.",
        "**Entry** is a tick through T x (1 + {BO_BUFFER}%), the level BO-01 "
        "calls a breakout, or the market price if price has already cleared "
        "it. **Target** is BO-06's measured move, T + H.",
        "**The trigger fires** on a close through it on {BO_VOL}x average "
        "volume (BO-01 + BO-02). Without the volume it stays a setup, capped "
        "at WATCH.",
    )
    caveats = (
        "**Every result before v1.5 includes late and repeat entries.** A pattern "
        "stayed an entry signal for {HORIZON} bars after its breakout: in the v1.1 "
        "India run 20% of trades re-used a pattern another trade had already traded "
        "and 13% entered more than 5% above the trigger. Those runs measure that "
        "behaviour as much as the patterns.",
        "**73% of its trades were one pattern — before v1.2.** Until v1.2 a cup without a "
        "handle never expired, so a years-old cup traded every time price revisited its rim; "
        "much of the count below is that bug. CUPNH took 185 of 253; DBOT "
        "15, IHS 18, FWDG 15, RECT 10, ATRI 4, TBOT 6; and CUP, FBASE, SYMM, "
        "FLAG and HTF took NONE. Whatever the backtest measured, it measured "
        "the cup-without-handle — the weaker O'Neil variant — not the spec's "
        "breadth. DBOT was the only pattern with positive expectancy (+0.05R "
        "on 15 trades, which is nothing) -- and that was the textbook "
        "reversal DBOT, replaced in v1.3 by O'Neil's W.",
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
        "**Recent listings are judged on a short history.** From v1.7 a stock is eligible after "
        "{min_bars} bars (about a year), the screen's own floor. The detectors look back about "
        "two years of bars, so a new listing's prior-trend rules (PT-01/PT-02) see a truncated "
        "window: that can only make a pattern harder to accept, never easier, but a base that "
        "began before the listing cannot be seen at all.",
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
        "above a rising 200-day, while TBOT and IHS require a prior DOWNTREND "
        "(PT-02) and form well below the highs. They are implemented and "
        "tested, and they will rarely fire here. DBOT left this group in v1.3: "
        "O'Neil's W follows an uptrend. It still collides with the screen "
        "another way: a W {W_MIN_DEPTH}-{W_MAX_DEPTH}% deep triggers at a middle "
        "peak that can itself sit more than 15% under the 52-week high, and then "
        "the screen drops it. Measuring them needs a "
        "screen that does not demand an uptrend — a deliberate follow-up, not "
        "an oversight: changing the screen would also break the like-for-like "
        "comparison with `chart_pattern` that this strategy exists for.",
        "Several patterns usually match one chart. The traded one is the "
        "highest-priority live match; `pattern` names it and the setup "
        "columns show the rest.",
    )
    gate_docs = {
        "G1": "A bullish pattern must be COMPLETE (its buy-stop can rest at the "
              "trigger) or break out ON THIS BAR — BO-01 and BO-02 met today, at "
              "most {BREAKOUT_MAX_AGE} bars after the breakout bar. A pattern that "
              "broke out earlier is history even while its {HORIZON}-bar outcome is "
              "still being recorded, and one that BO-03/BO-04 voided never qualifies.",
        "G2": "No CONFIRMED topping pattern (double top, head and shoulders "
              "top, rising wedge, descending triangle) on the same chart. A "
              "long bought inside a confirmed top is the trade this screener "
              "would otherwise keep taking.",
        "G3": "Earnings must not fall within {EARNINGS_DAYS} trading days: a "
              "base breaking out two days before a print is a bet on the print.",
        "G4": "ATR14 must be at most {MAX_ATR_PCT}% of price.",
        "G5": "The close must sit in the actionable band around the trigger: "
              "no more than {MAX_CHASE_PCT}% above it (past that the breakout "
              "happened without you) and no more than "
              "{MAX_BELOW_TRIGGER_PCT}% below it. The spec has no such rule "
              "because §11's tracker holds a pattern from completion and lets "
              "BO-04 expire it; a screener asked about one bar needs the "
              "band, or it reports AEVA as a live double bottom with a "
              "trigger 108% overhead.",
    }
    watch_docs = {
        "W1": "A topping pattern is FORMING (rolled over but not yet through "
               "its neckline) on the same chart. Caps the decision at TRADE ON "
               "TRIGGER; a confirmed one fails gate G2 outright.",
        "W2": "Price is through the trigger but volume is below {BO_VOL}x its "
               "50-day average, so BO-02 has not confirmed the breakout. Caps "
               "at WATCH.",
        "W3": "RSI14 above {OVERBOUGHT_RSI}. Caps at TRADE ON TRIGGER.",
    }
    setup_docs = {
        CUP: "§4 cup with handle: a rounded correction of "
             "12-33% recovering to its left lip — the recovery taking at least "
             "{CUP_RIGHT_LEFT_MIN}x as long as the decline, so a fast V does not "
             "count — then a 5-25 day handle drifting down in the upper half of "
             "the cup on volume below 0.8x its 50-day average. The two rims are a "
             "resistance ZONE, not a line: the right rim may sit 15% under to 3% over "
             "the left, and inside that the gap is graded — within {RIM_IDEAL_PCT}% "
             "ideal, within {RIM_OK_PCT}% acceptable, beyond that loose — and the "
             "grade moves setup quality (+{RIM_IDEAL_BONUS} ideal, -{RIM_LOOSE_PENALTY} "
             "loose), which ranks signals for the position slots. T is the handle's "
             "high, raised to the left rim when the handle sits under it, so the "
             "breakout clears the whole zone.",
        CUPNH: "§4 the same cup read before a handle exists, with price still "
               "at the rim. T is the OLD HIGH, the higher of the two lips -- "
               "O'Neil's buy point -- since the right lip may sit up to 15% "
               "under the left. O'Neil treats it as the "
               "weaker variant, which is why it is a separate code. Its rims are "
               "graded like CUP's ({RIM_IDEAL_PCT}% ideal, {RIM_OK_PCT}% acceptable). It is "
               "complete {K_MAJOR} bars after C and void {MAX_WAIT} bars later "
               "without a breakout.",
        DBOT: "§5.1 O'Neil's W, a continuation base: a prior uptrend into the "
              "high it corrects, a second low 0-{W_UNDERCUT_MAX}% UNDER the "
              "first (the shakeout), {W_MIN_DEPTH}-{W_MAX_DEPTH}% deep from that "
              "high and at least {W_MIN_DAYS} bars long, with a middle peak at "
              "least 10% above the lows. T is that peak. (The spec's textbook "
              "reversal -- two equal lows after a decline -- is not traded.)",
        TBOT: "§5 triple bottom: three lows after a decline, all within "
              "tolerance of each other AND level -- lows that step up (or "
              "down) each time may drift no more than {TRIPLE_MAX_DRIFT}% "
              "first to third, since a rising floor is a range, not three "
              "tests of one support. T is the higher of the two middle peaks.",
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
        "**Once per pattern, on its breakout bar.** The signal fires only on the "
        "bar the breakout is confirmed; in a backtest each pattern carries its "
        "identity (code and first key point) and the simulator skips a pattern "
        "already entered (EN-04), so a stop-out is final for that pattern.",
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
        ("Breakout age", "BREAKOUT_MAX_AGE",
         "Bars after its breakout bar on which a confirmed pattern is still an "
         "entry ({BREAKOUT_MAX_AGE}: the breakout bar only)."),
        ("Rim alignment", "RIM_IDEAL_PCT",
         "A cup's rims are graded, not judged: the right rim within {RIM_IDEAL_PCT}% of the left is "
         "ideal (+{RIM_IDEAL_BONUS} setup quality), within {RIM_OK_PCT}% acceptable (no change), beyond "
         "that loose (-{RIM_LOOSE_PENALTY}). No published percentage exists; these are starting points."),
        ("Cup symmetry", "CUP_RIGHT_LEFT_MIN",
         "CH-06, beyond the spec: a cup's recovery (B to C) must take at least "
         "{CUP_RIGHT_LEFT_MIN}x as many bars as its decline (A to B)."),
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
         "LIVE SCREENING ONLY: closes below this price are excluded. Not applied point in\n          time in a backtest -- see base.tradable_point_in_time."),
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
        ok, why = tradable_point_in_time(cfg, last)
        if not ok:
            return False, why
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
            live = _tradeable(res)
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
                "pattern_name": PATTERN_NAMES.get(code, code),
                "pattern_note": _note(res),
                "pattern_geometry": _geometry(code, res),
                "bars_since_breakout": res["metrics"].get("bars_since_breakout"),
                # a cup's rim alignment (graded, not judged); it adjusts setup quality in classify
                "rim_gap_pct": res["metrics"].get("rim_gap_pct"),
                "rim_grade": res["metrics"].get("rim_grade"),
                # §11's identity, so the simulator enters each pattern once (EN-04)
                "pattern_anchor": str(ps.anchor_of(res).date()) if ps.anchor_of(res) is not None else None,
            })
        if top_name is not None:
            ctx.extras["topping_pattern"] = top_name
            ctx.extras["topping_state"] = top_res["state"]

        # S1: a live bullish pattern
        if best is None:
            result.fail("G1", f"no live pattern ({first_fail or 'nothing detected'})")
        else:
            result.ok("G1", f"{best[0]} {best[1]['state']}")

        # S2: not inside a confirmed top
        if top_name is not None and top_res["state"] == ps.CONFIRMED:
            result.fail("G2", f"confirmed {top_name} on the same chart")
        else:
            result.ok("G2")

        # S3: earnings
        if ctx.earnings_days_away is not None and ctx.earnings_days_away <= EARNINGS_DAYS:
            result.fail("G3", f"earnings in {ctx.earnings_days_away} trading days")
        else:
            result.ok("G3")

        # S4: volatility
        atr_pct = d["atr_pct"].iloc[-1]
        if pd.notna(atr_pct) and atr_pct > MAX_ATR_PCT:
            result.fail("G4", f"ATR% {atr_pct:.1f} > {MAX_ATR_PCT:g}%")
        else:
            result.ok("G4")

        # S5: price is in the actionable band around the trigger
        trigger = ctx.extras.get("trigger")
        if trigger:
            gap = (close / float(trigger) - 1) * 100
            ctx.extras["pct_from_trigger"] = gap
            if gap > MAX_CHASE_PCT:
                result.fail("G5", f"{gap:.1f}% above the trigger")
            elif gap < -MAX_BELOW_TRIGGER_PCT:
                result.fail("G5", f"{-gap:.1f}% below the trigger — not actionable")
            else:
                result.ok("G5")
        else:
            result.ok("G5")

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
        result.watch_flags["W1"] = bool(forming)
        if forming:
            result.watch_notes["W1"] = f"{top_name} forming on the same chart"

        through = bool(trigger) and ctx.close > float(trigger)
        thin = pd.notna(vol_sma50) and vol_sma50 and vol < BO_VOL * vol_sma50
        result.watch_flags["W2"] = bool(through and thin)
        if result.watch_flags["W2"]:
            result.watch_notes["W2"] = (
                f"through the trigger on {vol / vol_sma50:.2f}x volume "
                f"(BO-02 wants {BO_VOL:g}x)")

        result.watch_flags["W3"] = bool(pd.notna(rsi14) and rsi14 > OVERBOUGHT_RSI)
        if result.watch_flags["W3"]:
            result.watch_notes["W3"] = f"RSI14 {rsi14:.0f} > {OVERBOUGHT_RSI:g}"

    def watch_cap(self, result: StrategyResult) -> str:
        caps = []
        if result.watch_flags.get("W2"):
            caps.append("WATCH_WAIT")
        for code in ("W1", "W3"):
            if result.watch_flags.get(code):
                caps.append("TRADE_ON_TRIGGER")
        return min(caps, key=CAP_ORDER.index) if caps else "TRADE_HIGH_CONFIDENCE"

    def setup_quality(self, result: StrategyResult) -> float:
        active = [c for c in self.setup_codes if result.setups.get(c)]
        if not active:
            return 0.0
        score = 2.0 - 0.1 * min(_priority(active[0]), 10)
        if result.watch_flags.get("W1"):
            score -= 0.5
        if result.watch_flags.get("W2"):
            score -= 1.0
        return max(score, 0.0)

    # ---------- entry ----------

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        """BO-01 and BO-02, met ON day t — not a breakout from earlier in the outcome horizon."""
        age = ctx.extras.get("bars_since_breakout")
        return ctx.extras.get("pattern_state") == ps.CONFIRMED and age is not None and age <= BREAKOUT_MAX_AGE

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        """One entry per pattern (EN-04): a pattern already traded — stopped out or not — is not
        bought again, even if it re-fires (a resting buy-stop on a COMPLETE pattern can)."""
        anchor = ctx.extras.get("pattern_anchor")
        return {"base_id": f"{ctx.extras.get('pattern')}:{anchor}"} if anchor else {}

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
            reasons.append(result.watch_notes.get("W2", "capped by watch flag"))
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
                active = [c for c in ("W1", "W3") if result.watch_flags.get(c)]
                reasons.append(f"capped by watch flag ({'/'.join(active)})")

        before = label
        if regime_downgrade_active and label != "AVOID":
            label = DOWNGRADE_MAP[label]
            reasons.append("market-regime downgrade applied")
        return Decision(LABELS[before], LABELS[label], "; ".join(reasons),
                        risk_pct, r_mult, self.setup_quality(result) + self._rim_quality(ctx))

    @staticmethod
    def _rim_quality(ctx: StockContext) -> float:
        """A cup's rim alignment as a quality adjustment, read from the extras (which survive the
        backtest's signal cache, where the result alone would not): ideal rims rank higher for the
        position slots, loose ones lower; acceptable ones and every other pattern are unchanged."""
        grade = ctx.extras.get("rim_grade") if ctx.extras.get("pattern") in (CUP, CUPNH) else None
        return RIM_IDEAL_BONUS if grade == "ideal" else -RIM_LOOSE_PENALTY if grade == "loose" else 0.0

    def report_extras(
        self, ctx: StockContext, result: StrategyResult, plan: TradePlan | None
    ) -> dict:
        e = ctx.extras
        trig = e.get("trigger")
        return {
            "pattern": e.get("pattern"),
            "pattern_name": e.get("pattern_name"),
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


    setup_names = PATTERN_NAMES
    # short names for the chart's checklist; the rules themselves are gate_docs
    gate_titles = {"G1": "Pattern complete or breaking out", "G2": "No confirmed top on the chart",
                   "G3": "No earnings within 10 days", "G4": "Volatility sane", "G5": "Close near the trigger"}

    def cached_signal_ok(self, extras: dict) -> bool:
        """A pattern row saved before its geometry (and each line's touches) was recorded is
        recomputed, so the chart can draw it; the rules did not change, so the version did not."""
        if not extras.get("pattern"):
            return True
        geo = extras.get("pattern_geometry")
        return bool(geo) and all("touches" in ln for ln in geo.get("lines") or [])

    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The traded pattern as the detector saw it on the signal bar — its swing points joined
        in order, its fitted lines (triangle and wedge boundaries, channel, neckline, flat-base
        range) — plus the spec levels: trigger, invalidation and measured target. The geometry is
        the `pattern_geometry` the run itself recorded; a signal written without it draws the
        levels alone."""
        e = sig.get("extras") or {}
        d = str(sig["date"])
        code = e.get("pattern")
        if not (code and e.get("trigger")):
            return super().chart_anatomy(sig)
        name = e.get("pattern_name") or PATTERN_NAMES.get(code, code)
        geo = e.get("pattern_geometry") or {}
        # a topping pattern (the chart indicator draws them; a trade never is one) breaks DOWN
        bear = e.get("direction") == "bearish"
        shape_role = "stop" if bear else "base"
        cup_r2 = None
        pts = geo.get("points") or []
        start = pts[0]["date"] if pts else None
        for ln in geo.get("lines") or []:
            start = min(start or ln["from"], ln["from"])
        out: list[dict] = []
        if code in (CUP, CUPNH) and len(pts) >= 3:
            fitted = _cup_from_prices(sig, pts)
            path, cup_r2 = fitted if fitted else (_cup_curve(pts), None)
            low = pts[1]
            out.append({"shape": "dots", "role": shape_role, "label": "cup low",
                        "points": [{"at": low["date"], "price": low["price"], "label": low["label"]}]})
            # the rims as a resistance zone, graded by how well they line up
            a_pt, c_pt = pts[0], pts[2]
            gap, grade = e.get("rim_gap_pct"), e.get("rim_grade")
            out.append({"shape": "box", "from": a_pt["date"], "to": d,
                        "top": max(a_pt["price"], c_pt["price"]), "bottom": min(a_pt["price"], c_pt["price"]),
                        "role": "level", "label": "resistance zone" + (f" · rims {gap:+.1f}%, {grade}" if gap is not None else "")})
        else:
            path = [{"at": q["date"], "price": q["price"], "label": q["label"]} for q in pts]
        if len(path) >= 2:
            out.append({"shape": "path", "from": path[0]["at"], "to": path[-1]["at"], "role": shape_role,
                        "points": path, "label": name})
        for ln in geo.get("lines") or []:
            out.append({"shape": "line", "from": ln["from"], "to": ln["to"], "p0": ln["p0"], "p1": ln["p1"],
                        "role": shape_role, "label": ln["name"]})
            if ln.get("touches"):
                out.append({"shape": "dots", "role": shape_role, "label": f"{ln['name']} line touches",
                            "points": [{"at": q["date"], "price": q["price"]} for q in ln["touches"]]})
        span = {"from": start} if start else {"bars": 60}
        out.append({"shape": "level", **span, "to": d, "price": float(e["trigger"]),
                    "role": "stop" if bear else "pivot",
                    "label": f"{'breakdown' if bear else 'trigger'} {e['trigger']:.2f} — confirms the {name.lower()}"})
        if e.get("invalidation"):
            out.append({"shape": "level", **span, "to": d, "price": float(e["invalidation"]),
                        "role": "support", "label": f"invalidation {e['invalidation']:.2f} — the pattern is wrong "
                                                    f"{'above' if bear else 'below'} this"})
        if e.get("measured_target"):
            out.append({"shape": "level", "bars": 20, "to": d, "price": float(e["measured_target"]),
                        "role": "stop" if bear else "target", "label": f"measured target {e['measured_target']:.2f}",
                        "dash": True})
        note = f"Pattern: {name} ({code if code != name else 'topping'}, {e.get('pattern_state', '')})"
        if cup_r2 is not None:
            note += f" · fitted cup R² {cup_r2:.2f}"
        if e.get("pattern_note"):
            note += f" · {e['pattern_note']}"
        if e.get("height"):
            note += f" · height {e['height']:.2f} projected {'below' if bear else 'above'} the trigger"
        if e.get("topping_pattern"):
            note += f" · WARNING: topping {e['topping_pattern']} ({e.get('topping_state', '')})"
        out.append({"shape": "note", "at": d, "price": float(e["trigger"]), "text": note})
        return out


    def detect_live(self, daily: pd.DataFrame, market: str, symbol: str, *, show_all: bool = True,
                    topping: bool = True) -> list[dict]:
        """What the detectors see on the last bar of `daily` — the chart's Patterns indicator, which
        asks on demand instead of reading stored signals. The same detectors and the same drawing
        as a backtest trade (`chart_anatomy`), so a pattern looks identical in both places; but this
        is exploration, not a record of what any run traded. Bullish matches are the live ones
        (complete, or confirmed within the outcome horizon), best first by the strategy's own
        priority; `tradeable` marks the ones it would act on. Topping patterns are drawn in red."""
        date = daily.index[-1].date()
        found: list[tuple[str, dict, str]] = []
        for code, (_section, detect) in BULLISH.items():
            try:
                res = detect(daily)
            except (IndexError, ValueError, ZeroDivisionError, KeyError):
                continue
            if _live(res):
                found.append((code, res, "bullish"))
        found.sort(key=lambda x: _priority(x[0]))
        if not show_all:
            found = found[:1]
        if topping:
            for name, detect in BEARISH.items():
                try:
                    res = detect(daily)
                except (IndexError, ValueError, ZeroDivisionError, KeyError):
                    continue
                if _live(res):
                    found.append((name, res, "bearish"))
        out = []
        for code, res, direction in found:
            lv = res["levels"]
            name = PATTERN_NAMES.get(code, code[:1].upper() + code[1:])
            extras = {"pattern": code, "pattern_name": name, "pattern_state": res["state"], "direction": direction,
                      "trigger": float(lv.trigger), "invalidation": float(lv.invalidation), "height": float(lv.height),
                      "measured_target": float(lv.target), "pattern_note": _note(res),
                      "pattern_geometry": _geometry(code, res),
                      "rim_gap_pct": res["metrics"].get("rim_gap_pct"), "rim_grade": res["metrics"].get("rim_grade")}
            shapes = self.chart_anatomy({"market": market, "symbol": symbol, "date": date, "extras": extras})
            geo = extras["pattern_geometry"]
            dates = [q["date"] for q in geo["points"]] + [ln["from"] for ln in geo["lines"]]
            out.append({"code": code, "name": name, "direction": direction, "state": res["state"],
                        "tradeable": direction == "bullish" and _tradeable(res),
                        "trigger": round(float(lv.trigger), 4), "invalidation": round(float(lv.invalidation), 4),
                        "target": round(float(lv.target), 4), "start": min(dates) if dates else str(date),
                        "shapes": shapes})
        return out

    def patterns_history(self, daily: pd.DataFrame, market: str, symbol: str, years: int | None = 5) -> list[dict]:
        """Every pattern the detectors saw over the last `years` of `daily`, for the chart's pattern list:
        `detect_live` run as of every `_pattern_scan_step`-th bar (each run sees only the bars up to it,
        as a live chart would), with the sightings of one pattern merged — the same code starting within
        `_pattern_merge_bars` bars of a pattern already seen is that pattern, drawn as last seen. Nothing
        here is a rule of its own, so a change to a detector shows in the list. Exploration only.

        Each pattern: {code, name, direction, start, first_seen, last_seen, sightings, state (as last
        seen), states, tradeable (on any sighting), trigger, invalidation, target, shapes, and what price
        did against its own levels afterwards: crossed (the first close through the trigger after it was
        first seen — above for a bullish pattern, below for a topping one) and invalidated (the first
        close beyond its invalidation level)}, newest first."""
        if daily.empty:
            return []
        since = daily.index[-1] - pd.DateOffset(years=years) if years else daily.index[0]
        idx = [i for i in range(len(daily)) if daily.index[i] >= since and i + 1 >= self.min_bars]
        if not idx:
            return []
        stops = sorted(set(idx[::_pattern_scan_step] + [idx[-1]]))
        pos = {d: k for k, d in enumerate(daily.index)}
        found: list[dict] = []
        for i in stops:
            as_of = str(daily.index[i].date())
            for m in self.detect_live(daily.iloc[: i + 1], market, symbol):
                start = pd.Timestamp(m["start"])
                same = next((p for p in found if p["code"] == m["code"] and abs(pos.get(start, 0) - pos.get(pd.Timestamp(p["start"]), 0))
                             <= _pattern_merge_bars), None)
                if same is None:
                    found.append({**m, "first_seen": as_of, "last_seen": as_of, "sightings": 1, "states": [m["state"]],
                                  "tradeable": m["tradeable"]})
                else:
                    same.update({k: m[k] for k in ("state", "trigger", "invalidation", "target", "shapes", "start")})
                    same["last_seen"] = as_of
                    same["sightings"] += 1
                    same["tradeable"] = same["tradeable"] or m["tradeable"]
                    if m["state"] not in same["states"]:
                        same["states"].append(m["state"])
        close = daily["close"]
        for p in found:
            after = close[close.index > pd.Timestamp(p["first_seen"])]
            bull = p["direction"] == "bullish"
            hit = after[after > p["trigger"]] if bull else after[after < p["trigger"]]
            bad = after[after < p["invalidation"]] if bull else after[after > p["invalidation"]]
            p["crossed"] = str(hit.index[0].date()) if len(hit) else None
            p["invalidated"] = str(bad.index[0].date()) if len(bad) else None
        return sorted(found, key=lambda p: p["last_seen"], reverse=True)


# The chart's pattern list (patterns_history): how often to ask the detectors, and how close two
# sightings' starts must be to count as one pattern. Lowercase on purpose: they draw a list and decide
# nothing, so they stay out of the strategy's fingerprint.
_pattern_scan_step = 5
_pattern_merge_bars = 10


def _geometry(code: str, res: dict) -> dict:
    """The matched pattern's swing points (in time order) and fitted lines, as plain JSON for the
    signal record, so the chart can draw the shape the run traded on without re-detecting it."""
    pts = sorted(res.get("points", {}).items(), key=lambda kv: kv[1]["pos"])
    names = {**POINT_NAMES, **POINT_NAMES_BY_CODE.get(code, {})}
    return {
        "points": [{"label": names.get(k, k), "date": str(pd.Timestamp(v["date"]).date()),
                    "price": round(float(v["price"]), 4)} for k, v in pts],
        "lines": [{"name": k, "from": str(pd.Timestamp(v["from"]).date()),
                   "to": str(pd.Timestamp(v["to"]).date()),
                   "p0": round(float(v["p0"]), 4), "p1": round(float(v["p1"]), 4),
                   "touches": [{"date": str(pd.Timestamp(q["date"]).date()),
                                "price": round(float(q["price"]), 4)}
                               for q in v.get("touches") or []]}
                  for k, v in (res.get("lines") or {}).items()],
    }


def _cup_from_prices(sig: dict, pts: list[dict]) -> tuple[list[dict], float] | None:
    """The cup as a U FITTED to the closes from the left lip A to the right lip C, by least
    squares, and the fit's R². The curve is the chord from A to C minus a depth k times a U
    profile (4v(1-v))^q, where v remaps time so the bottom can sit off-centre at m. k is solved
    in closed form; the roundness q and the bottom's position m are searched on a grid. So it
    starts and ends exactly at the lips, its shape comes from the prices, and the gap between
    it and the candles — summarised by R² — shows how cup-like the base really is. Any handle
    (D) is joined on straight. None when no prices are stored."""
    import numpy as np

    from ..marketdata import cache

    if not (sig.get("market") and sig.get("symbol")):
        return None
    daily = cache.load_cached(sig["market"], sig["symbol"])
    if daily is None or daily.empty:
        return None
    a, c = pts[0], pts[2]
    close = daily["close"][(daily.index >= pd.Timestamp(a["date"])) & (daily.index <= pd.Timestamp(c["date"]))]
    n = len(close)
    if n < 10:
        return None
    y = close.to_numpy(float)
    u = np.linspace(0.0, 1.0, n)
    chord = a["price"] + (c["price"] - a["price"]) * u
    resid = chord - y                           # how far below the chord each close sits
    best = None
    for m in np.arange(0.25, 0.751, 0.05):
        v = np.where(u < m, u / (2 * m), 0.5 + (u - m) / (2 * (1 - m)))
        base = 4 * v * (1 - v)
        for q in (0.3, 0.4, 0.5, 0.7, 1.0, 1.5):
            g = base ** q
            k = max(float(resid @ g / (g @ g)), 0.0)
            sse = float(((resid - k * g) ** 2).sum())
            if best is None or sse < best[0]:
                best = (sse, chord - k * g)
    sse, fit = best
    sst = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - sse / sst if sst else float("nan")
    path = [{"at": str(t.date()), "price": float(v), "label": ""} for t, v in zip(close.index, fit)]
    path[0]["label"], path[-1]["label"] = a["label"], c["label"]
    return path + [{"at": q["date"], "price": q["price"], "label": q["label"]} for q in pts[3:]], r2


def _cup_curve(pts: list[dict], steps: int = 24) -> list[dict]:
    """Fallback when no prices are stored: a cup drawn as the U that CH-05 demands rather than a V: from each lip
    down to the low B along a quarter-sine, steep at the lip and flat at the
    bottom, so the drawn bottom is rounded. It runs through the detector's own
    A, B and C, and any handle (D) is joined on straight. Dates between the
    points are business days, which the chart snaps to its nearest bar."""
    a, b, c = pts[0], pts[1], pts[2]

    def side(p0: dict, p1: dict, down: bool) -> list[dict]:
        days = pd.bdate_range(p0["date"], p1["date"])
        if len(days) < 3:
            return []
        out = []
        for i in range(1, steps):
            u = i / steps                          # 0 at p0, 1 at p1
            f = 1 - math.sin(math.pi / 2 * u) if down else 1 - math.cos(math.pi / 2 * u)
            hi = p0["price"] if down else p1["price"]
            out.append({"at": str(days[round(u * (len(days) - 1))].date()),
                        "price": b["price"] + (hi - b["price"]) * f, "label": ""})
        return out

    pt = lambda q: {"at": q["date"], "price": q["price"], "label": q["label"]}  # noqa: E731
    out = ([pt(a)] + side(a, b, True) + [pt(b)] + side(b, c, False) + [pt(c)]
           + [pt(q) for q in pts[3:]])
    # one vertex per date: two on one bar (a holiday snapped to its neighbour) draw a vertical step
    return [q for i, q in enumerate(out) if q["label"] or i == 0 or q["at"] != out[i - 1]["at"]]


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
            if k in ("depth_pct", "cup_days", "handle_depth_pct", "handle_days", "rim_gap_pct", "rim_grade",
                     "separation_days", "middle_pct", "duration_days",
                     "apex_progress", "window_days", "pole_gain_pct",
                     "retrace_pct", "head_clearance_pct")]
    return ", ".join(bits)
