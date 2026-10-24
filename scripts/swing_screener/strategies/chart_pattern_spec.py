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
TRADE_CUPNH = 1           # 1 trades a cup WITHOUT a handle (CUPNH); 0 detects and draws it but never buys it
CUP_UNDER_RIM = 1         # CH-12, beyond the spec: no high between a cup's lips above its rim (1 = on)
HS_ORIGIN = 1             # HS-09, beyond the spec: the left shoulder belongs to the trend being reversed (1 = on)
HS_MAX_NECK_CHANGE = 5.0  # HS-10, beyond the spec: the neckline may run against the pattern by at most this %, N1 to N2
EARLY_BREAKOUT = 1        # beyond the spec: a breakout is searched from the last key point, not from its confirmation
WEDGE_MIN_CONVERGE = 1.5  # WG-04, beyond the spec: a wedge's steep line falls/rises at least this x the shallow one
CONTAIN_BREAKOUT_SIDE = 1  # TL-04, beyond the spec: no earlier close through the breakout-side line (1 = on)
def _build_params() -> ps.PatternParams:
    return ps.PatternParams(
    k_minor=K_MINOR, k_major=K_MAJOR, min_swing_pct=MIN_SWING_PCT, atr_mult=ATR_MULT,
    tol_pct=TOL_PCT, tol_atr_mult=TOL_ATR_MULT, bo_buffer=BO_BUFFER / 100, bo_vol=BO_VOL,
    max_wait=MAX_WAIT, fail_days=FAIL_DAYS, horizon=HORIZON,
    oneil_undercut=(0.0, W_UNDERCUT_MAX), oneil_depth=(W_MIN_DEPTH, W_MAX_DEPTH),
    oneil_min_days=W_MIN_DAYS, triple_max_drift=TRIPLE_MAX_DRIFT, right_left_min=CUP_RIGHT_LEFT_MIN,
    rim_ideal_pct=RIM_IDEAL_PCT, rim_ok_pct=RIM_OK_PCT, trigger_clears_rims=True,
    cup_under_rim=bool(CUP_UNDER_RIM), hs_origin=bool(HS_ORIGIN), hs_max_neck_change=HS_MAX_NECK_CHANGE,
    early_breakout=bool(EARLY_BREAKOUT), wg_min_converge=WEDGE_MIN_CONVERGE,
    contain_breakout_side=bool(CONTAIN_BREAKOUT_SIDE),
)


_PARAM_CONSTANTS = ("K_MINOR", "K_MAJOR", "MIN_SWING_PCT", "ATR_MULT", "TOL_PCT", "TOL_ATR_MULT", "BO_BUFFER",
                    "BO_VOL", "MAX_WAIT", "FAIL_DAYS", "HORIZON", "W_UNDERCUT_MAX", "W_MIN_DEPTH", "W_MAX_DEPTH",
                    "W_MIN_DAYS", "TRIPLE_MAX_DRIFT", "CUP_RIGHT_LEFT_MIN", "RIM_IDEAL_PCT", "RIM_OK_PCT", "CUP_UNDER_RIM",
                    "HS_ORIGIN", "HS_MAX_NECK_CHANGE", "EARLY_BREAKOUT", "WEDGE_MIN_CONVERGE",
                    "CONTAIN_BREAKOUT_SIDE")
PARAMS = _build_params()
_PARAMS_KEY: tuple = tuple(globals()[k] for k in _PARAM_CONSTANTS)


def _params() -> ps.PatternParams:
    """PARAMS, rebuilt if a module constant was overridden since (backtest --const sets the constant,
    not the dataclass built from it at import — without this, an override never reached the detectors)."""
    global PARAMS, _PARAMS_KEY
    key = tuple(globals()[k] for k in _PARAM_CONSTANTS)
    if key != _PARAMS_KEY:
        PARAMS, _PARAMS_KEY = _build_params(), key
    return PARAMS
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
    CUP: ("§4", lambda d: ps.detect_cup(d, _params())),
    CUPNH: ("§4", lambda d: ps.detect_cup(d, _params(), require_handle=False)),
    DBOT: ("§5.1", lambda d: ps.detect_double_bottom(d, _params(), oneil_w=True)),
    TBOT: ("§5", lambda d: ps.detect_triple_bottom(d, _params())),
    IHS: ("§6.2", lambda d: ps.detect_head_shoulders(d, _params(), inverse=True)),
    ATRI: ("§7", lambda d: _of_kind(d, (ps.ASCENDING,))),
    SYMM: ("§7", lambda d: _of_kind(d, (ps.SYMMETRICAL,))),
    FWDG: ("§10", lambda d: _of_kind(d, (ps.FALLING_WEDGE,))),
    RECT: ("§8.1", lambda d: _of_kind(d, (ps.RECTANGLE,))),
    FBASE: ("§8.2", lambda d: ps.detect_flat_base(d, _params())),
    FLAG: ("§9.2", lambda d: ps.detect_flag(d, _params())),
    HTF: ("§9.3", lambda d: ps.detect_flag(d, _params(), high_tight=True)),
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
    "LS": "left shoulder", "N1": "neckline L", "HD": "head", "N2": "neckline R",
    "RS": "right shoulder", "P0": "pole start", "X": "flag low", "S": "start",
}
# a double bottom reuses the cup's letters for different points, and a double top mirrors it
POINT_NAMES_BY_CODE = {DBOT: {"B": "low 1", "C": "peak", "D": "low 2"},
                       "double top": {"B": "top 1", "C": "trough", "D": "top 2"}}
BEARISH = {
    "double top": lambda d: ps.detect_double_top(d, _params()),
    "head and shoulders top": lambda d: ps.detect_head_shoulders(d, _params()),
    "rising wedge": lambda d: _of_kind(d, (ps.RISING_WEDGE,)),
    "descending triangle": lambda d: _of_kind(d, (ps.DESCENDING,)),
}


def _of_kind(daily, kinds: tuple[str, ...]) -> dict:
    return ps._pick_kinds(ps.detect_boundaries(daily, _params()), kinds, ps.TR_RULES)


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
    version = "1.12"
    changelog = (
        ("1.12", "2026-10-20",
         "Four detector fixes from a review of ICICIBANK.NS's trades. (1) TR-05's near end: the spec's "
         "triangle and wedge break out between 50% and 80% of the way to the apex, but only the 80% end was "
         "enforced -- a falling wedge was bought 27% of the way (2015-08-04). (2) WG-04 (WEDGE_MIN_CONVERGE): "
         "a wedge's steeper line must slope at least {WEDGE_MIN_CONVERGE}x the shallower one; that wedge's "
         "were 1.08x apart, a channel. (3) TL-04 (CONTAIN_BREAKOUT_SIDE): TL-03 lets a close sit up to the "
         "price tolerance (3%+) beyond a line, but beyond the breakout line by {BO_BUFFER}% it IS a breakout; "
         "an ascending triangle (2025-03-24) was bought although it closed above its upper line in September "
         "2024 and touched it twice after. (4) EARLY_BREAKOUT: a double, triple or head-and-shoulders completes {K_MAJOR} bars after its "
         "last point, and the spec searches for the breakout only from there -- an inverse H&S that broke "
         "out on 2016-04-21 at 230 was bought on 2016-04-27, a down day closing back near the 220 neckline. "
         "The breakout is now searched from the last point, so a breakout inside those bars is an old one, "
         "not an entry. The chart draws the invalidation of a sloping line as a tick at the signal bar, like "
         "the trigger."),
        ("1.11", "2026-10-20",
         "Head and shoulders, two rules beyond the spec. HS-09 (HS_ORIGIN): the left shoulder must belong to "
         "the trend being reversed -- the reaction after it may not run past where that trend began (for the "
         "inverse, the highest high in the window before the left shoulder that HS-01 measures the decline over). HS-10 "
         "(HS_MAX_NECK_CHANGE): the neckline may fall (inverse) or rise (top) by at most {HS_MAX_NECK_CHANGE}% "
         "from its left anchor to its right; HS-05's per-day slope cap still lets a long pattern's neckline "
         "drop a lot. JINDALSTEL.NS (2022-10-27, +7.2R) was bought as an inverse H&S whose 'left shoulder' "
         "was the 367.80 low of 2022-02-24 -- a low followed by a NEW high at 577.80, so part of the uptrend, "
         "not a bottom -- under a neckline that fell 19% (577.80 to 468.00). Both rules also apply to the "
         "topping H&S that vetoes a trade (G2, W1). The chart now marks the trigger at the breakout bar "
         "rather than as a flat line across a sloping neckline, labels the neckline anchors 'neckline L/R', "
         "and a traded pattern shows only the trade's own target."),
        ("1.10", "2026-10-19",
         "The signal-bar checks now hold at the fill. An order that triggers while every position slot is "
         "full keeps resting, and filled at whatever the open was once a slot freed up — however far price "
         "had run: AUBANK.NS (ascending triangle, trigger 715.30) was bought eight sessions late at 770.70, "
         "7.7% past the trigger, with 0.14R left to its target. A fill above the trigger plus "
         "{MAX_CHASE_PCT}% is now skipped, as is one whose measured move no longer projects {MIN_R}:1 or "
         "whose risk exceeds {MAX_RISK_PCT}%. Also a switch, TRADE_CUPNH (on), to test the cup without a "
         "handle: it was 207 of v1.8's 519 India trades and the cup WITH a handle none, because the "
         "handle-less signal fires first at the rim and its resting order blocks the later, better one."),
        ("1.9", "2026-10-19",
         "A cup must stay under its rim (CH-12, beyond the spec, CUP_UNDER_RIM): no high between the left "
         "and right lips may sit above the higher lip by more than the price tolerance (max({TOL_PCT}%, "
         "{TOL_ATR_MULT} x ATR/close)). The spec checks the lips, the low, the depth, the rounding and the "
         "balance of the sides, but never the inside, so a 'cup' whose middle made a new high passed: "
         "TECHM.NS was read as a cup without handle from a 1,732.80 left lip (2025-06-18) to a 1,633.20 right "
         "lip (2026-09-15), although it traded 1,854 in February 2026, 7% above the rim -- a breakout that "
         "failed and a second decline, not one rounded correction. Applies to cups with and without a handle."),
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
        "Not yet measured since v1.5: v1.8 to v1.12 (graded cup rims, a cup's trigger lifted to its left rim, CH-12, fill-time checks, HS-09/HS-10, TR-05's near end, WG-04, TL-04 and the early breakout search) have no run. Last measured at v1.5, with no demonstrated edge: India, full "
        "universe from 2013 (bracket exits, measured 2026-10-14): 3.61% CAGR against the index's "
        "11.6%, max drawdown -27.8%; no US v1.5 run was recorded. v1.6 renamed codes only and "
        "v1.7 admits stocks with {min_bars} bars of history instead of 320. (v1.2 stopped stale "
        "cups-without-handle from trading, v1.3 moved "
        "two buy rules to O'Neil's, v1.4 requires a triple bottom's lows to be level and v1.5 buys "
        "only on the breakout bar, once per pattern.) The earlier v1.0 comparison, dominated by stale "
        "cups and late and repeat entries: backtested 2026-10-09 it lost by less than its sibling: -0.93% "
        "CAGR and -0.072R per trade over 253 trades (US, 2020-2026, 300-symbol "
        "sample), against `chart_pattern_legacy`'s -5.60% and -0.309R on the same "
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
        "The idea: find classical chart patterns by fixed, numbered rules (research/chart-pattern-spec.md), "
        "and buy a bullish one on the session it breaks out — unless a topping pattern on the same chart "
        "says the trend is ending. Long only.",
        "Step 1, pre-filter (When no new trade is taken): liquidity and length of history only. No trend "
        "screen: each pattern carries its own prior-trend rule.",
        "Step 2, detect (The patterns table): on every session's close, twelve bullish detectors and four "
        "topping ones run on the bars up to that close. Each reports its state — complete, broke out, "
        "failed or void — and, when it fails, the first check it failed.",
        "Step 3, choose one pattern (Rules, G1): of the bullish patterns that are complete or broke out on "
        "this bar, the first in a fixed priority order is the trade's setup. Its trigger, invalidation "
        "level and height drive everything after.",
        "Step 4, gates and flags (Rules): five hard gates (G1–G5) and three watch flags (W1–W3) decide the "
        "label, from TRADE - HIGH CONFIDENCE down to AVOID (Decisions).",
        "Step 5, the trade (Entry, Stop, Target, Exit): a buy-stop at the breakout close, a stop at the "
        "pattern's invalidation level held within an ATR band, and a sell order at the measured move.",
        "Timing.\n\n"
        "- **Swing points** are known only {K_MINOR} or {K_MAJOR} sessions after they print, so a "
        "pattern is seen late, never early.\n"
        "- **The trigger** is set from bars up to the day before, so the breakout bar cannot move the level "
        "it breaks (the flat base is the exception; see Caveats).\n"
        "- **The signal** is decided on a session's close; the order can fill from the next session.",
        "Rule ids. Each check opens with an id (CH-03, BO-01 …) that names the same rule in "
        "core/pattern_spec.py and in the written spec, and in a stock's first-failed-rule note.",
    )
    caveats = (
        "**Where the code departs from the written spec.**\n\n"
        "- **CH-03:** every lip in the {PARAMS.right_lip[0]:g}–{PARAMS.right_lip[1]:g} × A band is tried, not only the first — judged on one day, the "
        "first lip can be months old.\n"
        "- **CH-06:** the recovery must also take {CUP_RIGHT_LEFT_MIN}x the decline's bars — a fast V passed "
        "the {PARAMS.side_frac} floor.\n"
        "- **CH-09:** a handle is never shorter than {K_MAJOR} bars, because the right lip needs {K_MAJOR} "
        "bars to confirm.\n"
        "- **Cup trigger:** raised to the left lip A — so the buy clears the left rim's supply.\n"
        "- **Cup without handle:** triggers at max(A, C), the old high, not at C.\n"
        "- **DBOT:** O'Neil's W (prior uptrend, second low undercutting, OW-01/OW-02) replaces the "
        "textbook reversal.\n"
        "- **Triple bottom:** TL-LV added, and a length of up to 2 × the double's maximum — the spec gives "
        "none.\n"
        "- **HS-09, HS-10:** added — a false left shoulder and a steep neckline passed.\n"
        "- **TL-04:** the id is reused for the breakout-side containment rule; the spec's TL-04 is the "
        "slope measure.\n"
        "- **TR-02:** touches need not alternate between the lines.\n"
        "- **WG-04:** added — near-parallel channels passed WG-02.\n"
        "- **Flat base trigger:** includes today's high (the spec freezes it at yesterday).\n"
        "- **BO-02:** the completing patterns take VOL50 before completion, not before their start.\n"
        "- **BO-03:** tested only for the cup without handle, doubles, triples and head and shoulders.\n"
        "- **BO-04:** the breakout is searched from the last key point, not from completion.\n"
        "- **BO-05:** a pattern state only; no position is sold on it.\n"
        "- **BO-06:** the height is added to the planned entry, not to T.\n"
        "- **Pattern tracker:** not used; the detectors run fresh on each bar, so one pattern is not followed "
        "from day to day.",
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
        "exposure ran at 93.9% against `chart_pattern_legacy`'s 79.3%. A position "
        "cap, not the detector, decided much of what got traded.",
        "**The flat base can never break out on its own bar, so a backtest never buys it.** Its window "
        "includes today, so its trigger (the window high) is at least today's high, and no close can be "
        "{BO_BUFFER}% above it. Live, a flat base only ever shows as TRADE ON TRIGGER.",
        "**The high tight flag is skipped at every fill.** It has no measured height, so its target is "
        "exactly {MIN_R}R from the planned entry. Slippage makes the fill a touch higher, the re-test at "
        "the fill then finds less than {MIN_R}:1, and the order is dropped.",
        "**A cup's handle checks include the breakout bar.** CH-08 to CH-11 measure the handle from the bar "
        "after the right lip through today. On a breakout day a high close can tilt the handle's slope "
        "upward (CH-10) and its volume can lift the handle average (CH-11), so a cup can fail its checks on "
        "the very bar it breaks out — and a backtest buys only that bar.",
        "**A cup's trigger is not raised to the right lip.** T is the handle's high raised to the left "
        "lip A. When the right lip C sits above A (up to {PARAMS.right_lip[1]:g} × A), T can be below C, "
        "so the buy-stop can sit under the right rim.",
        "**A sloping neckline is read at today's value for past bars.** For a head and shoulders (and the "
        "breakout search of every completing pattern) each past close is compared with the trigger as of "
        "today. A neckline falls up to {HS_MAX_NECK_CHANGE}%, so an earlier close above today's (lower) "
        "neckline counts as an old breakout although it was below the line on its day.",
        "**One pattern is chosen before the breakout is checked.** The highest-priority pattern that is "
        "complete OR breaking out is chosen. If it is only complete while a lower-priority pattern breaks "
        "out on the same bar, there is no buy that day.",
        "**The near_highs screen is not applied.** The Strategies page names it as this strategy's "
        "screen, so the two compare like for like with `chart_pattern_legacy`, but the pre-filter here "
        "checks liquidity only: price need not be near its high or above the 200-day. The reversal "
        "patterns (TBOT, IHS) are limited only by their own prior-downtrend rule and gate G5.",
        "**Two volume yardsticks.** The detector's BO-02 measures the breakout bar against the 50-bar "
        "average before the pattern started (for a cup, before its left lip, which can be a year earlier); "
        "W2 measures it against the latest 50 days. A backtest buy needs both at {BO_VOL}x.",
        "**Earnings are not known in a backtest**, so gate G3 never blocks there; it acts on the live "
        "screen only.",
        "**Five rules cannot fire at the default parameters** (CH-09, HS-06, TR-04, TR-07, FL-04) because "
        "the {MIN_SWING_PCT}% minimum swing and the {TOL_PCT}% tolerance are large relative to what those "
        "rules ask for. They are implemented and tested, and the defaults are left as written; see "
        "core/pattern_spec.py.",
        "**Flags and the high tight flag find nothing in practice.** Over 283 "
        "liquid US names the pole rules rejected 255 of them (FP-01 172, "
        "FP-02 63): a {PARAMS.pole_gain}% rise inside {PARAMS.pole_days} days on "
        "{PARAMS.pole_rv}x volume is simply rare.",
        "**The flat base is the least selective pattern here**, firing on "
        "24% of random walks against the cup's 0%. It has no touch "
        "requirement and its volume rule is off.",
        "**There is no ceiling on a bottom's middle swing**, so two lows either side of a spike pass DB-03: "
        "before v1.3, AEVA screened as a double bottom with lows of 13.51 and 13.90 around a 28.42 peak. "
        "The W's depth cap (OW-01) now bounds DBOT, but a triple bottom still has no ceiling; gate G5's "
        "band keeps a far-off trigger out of the report. `PatternParams.db_max_peak` exists to test a cap.",
        "**Recent listings are judged on a short history.** A stock is eligible after "
        "{min_bars} bars (about a year). The detectors look back {PARAMS.lookback} bars, so a new "
        "listing's prior-trend rules (PT-01/PT-02) see a truncated window: that can only make a pattern "
        "harder to accept, never easier, but a base that began before the listing cannot be seen at all.",
        "**Detection costs ~40ms per symbol-day** against `chart_pattern_legacy`'s "
        "~1ms, because twelve detectors run where seven did and each refits "
        "swings. A backtest of it is slower in proportion.",
        "Several patterns usually match one chart. The traded one is the "
        "highest-priority live match; `pattern` names it and the setup "
        "columns show the rest.",
    )
    gate_docs = {
        "G1": "A bullish pattern is complete and waiting, or broke out on today's bar.\n\n"
              "- **Complete:** every check of the pattern passes (The patterns table) and it has not broken "
              "out. A double, triple, head and shoulders or cup without handle must also not be void "
              "(BO-03, BO-04).\n"
              "- **Broke out today:** BO-01 and BO-02 are met on today's close — at most "
              "{BREAKOUT_MAX_AGE} bars after the breakout bar, so the breakout bar only. The detector keeps "
              "reporting a breakout for {HORIZON} bars; from the next bar on it fails here, so a pullback "
              "into an old pivot is never bought.\n"
              "- **CUPNH:** counts only while TRADE_CUPNH is 1 (now {TRADE_CUPNH}).\n"
              "- **Which pattern:** when several pass, the first in the priority order CUP, HTF, IHS, CUPNH, "
              "TBOT, ATRI, FLAG, DBOT, SYMM, RECT, FWDG, FBASE — rarest on random walks first.\n"
              "- **When none passes:** the note names the first failed rule as CODE:RULE (e.g. CUP:CH-05), "
              "taking the patterns in setup-list order.\n\n"
              "A complete pattern is a live TRADE ON TRIGGER; only a breakout today can be TRADE - HIGH "
              "CONFIDENCE, the one tier a backtest buys.",
        "G2": "No confirmed topping pattern on the same chart.\n\n"
              "- **Looked for:** double top, head-and-shoulders top, rising wedge, descending triangle, in "
              "that order. Only the first that is live is considered.\n"
              "- **Confirmed, double top or H&S top:** a close below its trigger by {BO_BUFFER}% (no "
              "volume test) within the last {HORIZON} bars, and not failed since (BO-05).\n"
              "- **Confirmed, rising wedge or descending triangle:** today's close is {BO_BUFFER}% below "
              "the lower line.\n"
              "- **Complete but not broken down:** raises W1 instead.\n\n"
              "Long only, so a topping pattern is a veto, never a trade.",
        "G3": "No earnings date within {EARNINGS_DAYS} weekdays.\n\n"
              "- **Counted:** weekdays from today to the stored next earnings date. 0 to {EARNINGS_DAYS} "
              "fails, and so does a negative count (a stored date that has passed). No known date passes.\n"
              "- **In a backtest:** no point-in-time earnings dates are used, so this never blocks there.",
        "G4": "ATR14 is at most {MAX_ATR_PCT}% of the close.\n\n"
              "- **ATR14:** the 14-session average true range, the stock's typical daily move. A missing "
              "value passes.",
        "G5": "The close is between {MAX_BELOW_TRIGGER_PCT}% below and {MAX_CHASE_PCT}% above the chosen "
              "pattern's trigger T.\n\n"
              "- **Measured:** (close ÷ T − 1) × 100.\n"
              "- **More than {MAX_CHASE_PCT}% above:** the breakout happened without you.\n"
              "- **More than {MAX_BELOW_TRIGGER_PCT}% below:** not actionable — e.g. a double bottom whose "
              "middle peak sits far overhead.",
    }
    watch_docs = {
        "W1": "A topping pattern on the chart is complete but has not broken down.\n\n"
              "- **Which:** the first live topping pattern in G2's order. If it has broken down, G2 fails "
              "instead.\n"
              "- **Effect:** caps the decision at TRADE ON TRIGGER and takes 0.5 off setup quality. A "
              "backtest buys only TRADE - HIGH CONFIDENCE, so it does not buy.",
        "W2": "The close is above the trigger T on volume under {BO_VOL} times the 50-day average volume.\n\n"
              "- **The average:** the 50 sessions ending today.\n"
              "- **Effect:** caps the decision at WATCH and takes 1.0 off setup quality.\n"
              "- **Why it can fire on a breakout:** the detector's BO-02 uses a different 50-bar average, "
              "taken before the pattern started. A buy needs both.",
        "W3": "RSI14 is above {OVERBOUGHT_RSI}.\n\n"
              "- **Effect:** caps the decision at TRADE ON TRIGGER, so a backtest does not buy.",
    }
    pattern_title = "The patterns — detector checks"
    pattern_intro = (
        "Each pattern is a run of checks, listed below pattern by pattern in the order the code runs them; "
        "the first that fails is the rule a stock reports. The terms they use:\n\n"
        "- **Swing high / swing low:** a bar whose high (low) is the highest (lowest) of the k bars on each "
        "side. Minor scale k = {K_MINOR} (flags, short triangles); major scale k = {K_MAJOR} (cups, doubles, "
        "triples, head and shoulders, long triangles). A swing is known only k bars later. Highs and lows "
        "alternate (of two highs in a row the higher is kept), and a swing that moved less than "
        "max({MIN_SWING_PCT}%, {ATR_MULT} × ATR14 ÷ close) from the previous one is dropped.\n"
        "- **tol, the price tolerance:** max({TOL_PCT}%, {TOL_ATR_MULT} × ATR14 ÷ close), on today's "
        "bar. Two prices are equal within tol when their gap ÷ their average is at most tol.\n"
        "- **Prior trend (PT-01 / PT-02):** price at a point at least a given % above the lowest low "
        "(below the highest high) of the {PARAMS.prior_window} bars before it.\n"
        "- **Lines:** least-squares straight lines through swing highs (upper) and swing lows (lower). "
        "Slope is per bar, as a fraction of the line's value at the pattern's midpoint; a line is flat "
        "within ±{PARAMS.flat_slope}. A touch is a swing within tol of its line.\n"
        "- **VOL50:** the average volume of the 50 bars before the pattern's start (BO-02 says which bar).\n"
        "- **T, X, H:** each pattern's trigger, invalidation level and height (see Setups).\n"
        "- **Lookback:** the detectors read the last {PARAMS.lookback} bars."
    )
    pattern_docs = {
        # ---- cup (CUP; CUPNH runs CH-01 to CH-06 and CH-12)
        "CH-01": "Cup — prior uptrend: the left lip A is at least {PARAMS.cup_prior_move}% above the lowest "
                 "low of the {PARAMS.prior_window} bars before it.\n\n"
                 "- **A:** every major swing high in the lookback is tried. Where several cups pass, the one "
                 "with the highest A is kept.",
        "CH-02": "Cup depth: (A − B) ÷ A is {PARAMS.cup_depth[0]:g}% to {PARAMS.cup_depth[1]:g}%.\n\n"
                 "- **B, the cup low:** the lowest low from the bar after A through today. A lower low after "
                 "the right lip moves B past every lip, so the cup fails CH-03.",
        "CH-03": "Right lip: C is a major swing high after B, no later than yesterday, between "
                 "{PARAMS.right_lip[0]:g} × A and {PARAMS.right_lip[1]:g} × A.\n\n"
                 "- **Several qualify:** each is tried in time order; the first that passes every later "
                 "check is the lip.\n"
                 "- **Rim grade (not a rejection):** (C − A) ÷ A within {RIM_IDEAL_PCT}% is ideal, within "
                 "{RIM_OK_PCT}% acceptable, beyond that loose. Ideal adds {RIM_IDEAL_BONUS} to setup quality, "
                 "loose takes {RIM_LOOSE_PENALTY} off.",
        "CH-12": "Cup stays under its rim: no high between A and C is above max(A, C) × (1 + tol). A new "
                 "high in the middle is a failed breakout and a second decline, not one cup.",
        "CH-04": "Cup length: {PARAMS.cup_days[0]} to {PARAMS.cup_days[1]} bars from A to C (about 7 to 65 "
                 "weeks).",
        "CH-05": "Rounded, not a V: at least max({PARAMS.round_min_days}, {PARAMS.round_frac} × the cup's "
                 "bars, rounded down) bars from A to C have a low in the cup's bottom third — at or below "
                 "B + (max(A, C) − B) ÷ 3.",
        "CH-06": "Balanced sides: A to B and B to C each take at least {PARAMS.side_frac} of the cup's bars, "
                 "and B to C takes at least {CUP_RIGHT_LEFT_MIN} times as many bars as A to B.\n\n"
                 "- **Example:** 30 bars down and 13 up in a 43-bar cup passes the {PARAMS.side_frac} floor "
                 "(13 ≥ 10.75) but fails the ratio (13 < {CUP_RIGHT_LEFT_MIN} × 30): a fast V-shaped "
                 "recovery.",
        "CH-07": "Handle in the cup's upper half: the handle low D — the lowest low after C, today's "
                 "included — is at least B + {PARAMS.handle_half} × (A − B).",
        "CH-08": "Handle depth: (C − D) ÷ C is {PARAMS.handle_depth[0]:g}% to {PARAMS.handle_depth[1]:g}%.",
        "CH-09": "Handle length: {PARAMS.handle_days[0]} to {PARAMS.handle_days[1]} bars from C to today.\n\n"
                 "- **In practice at least {K_MAJOR}:** C must be a confirmed major swing, which takes "
                 "{K_MAJOR} bars, so a shorter handle is never seen.",
        "CH-10": "Handle drifts down or sideways: a least-squares line through the closes from the bar after "
                 "C through today has a slope of zero or less. Today's close is included (see Caveats).",
        "CH-11": "Handle volume dries up: average volume from the bar after C through today is at most "
                 "{PARAMS.handle_vol} × the 50-bar average before A. Today's volume is included.",
        # ---- O'Neil's W (DBOT)
        "DB-01 (W)": "W — prior uptrend into the high it corrects: the highest high of the "
                     "{PARAMS.prior_window} bars before the first low B is at least {PARAMS.db_prior_move}% "
                     "above the lowest low of the {PARAMS.prior_window} bars before that high.\n\n"
                     "- **Points:** three consecutive major swings — low B, high C, low D.\n"
                     "- **Which W:** of those that pass, the most recent.\n\n"
                     "A continuation base after an advance; two equal lows after a decline (the textbook "
                     "reversal) is not looked for.",
        "DB-02 (W)": "W — the second low undercuts the first: (B − D) ÷ B is {PARAMS.oneil_undercut[0]:g}% "
                     "to {W_UNDERCUT_MAX}%.",
        "OW-01": "W depth: from that prior high down to the lower of the two lows is {W_MIN_DEPTH}% to "
                 "{W_MAX_DEPTH}%.",
        "OW-02": "W length: at least {W_MIN_DAYS} bars from that prior high to D (about 7 weeks).",
        "DB-03": "W middle peak high enough: (C − the lower low) ÷ the lower low is at least "
                 "{PARAMS.db_min_peak}%. There is no upper limit.",
        "DB-04": "W lows far enough apart: {PARAMS.db_days[0]} to {PARAMS.db_days[1]} bars from B to D.",
        "DB-05": "Lighter volume at the second low: switched off.",
        # ---- triple bottom (TBOT)
        "DB-01 (triple)": "Triple — prior downtrend: the first low B1 is at least {PARAMS.db_prior_move}% "
                          "below the highest high of the {PARAMS.prior_window} bars before it.\n\n"
                          "- **Points:** five consecutive major swings — lows B1, B2, B3 with peaks P1, P2 "
                          "between them.\n"
                          "- **Which triple:** of those that pass, the most recent.",
        "DB-02 (triple)": "Triple — lows level: every pair of the three lows is equal within tol.",
        "TL-LV": "Triple — not stepping: when the lows rise each time (or fall each time), B1 to B3 moves "
                 "at most {TRIPLE_MAX_DRIFT}%. Lows that zig-zag are not tested. A rising floor is a range, "
                 "not three tests of one support.",
        "DB-03 (triple)": "Triple — peaks high enough: (T − the lowest low) ÷ the lowest low is at least "
                          "{PARAMS.db_min_peak}%, T being the higher of P1 and P2.",
        "DB-04 (triple)": "Triple length: {PARAMS.db_days[0]} to 2 × {PARAMS.db_days[1]} bars from B1 to "
                          "B3.",
        # ---- inverse head and shoulders (IHS); the top mirrors it
        "HS-01": "H&S — prior trend: for the inverse, the left shoulder LS is at least "
                 "{PARAMS.hs_prior_move}% below the highest high of the {PARAMS.prior_window} bars before "
                 "it.\n\n"
                 "- **Points:** five consecutive major swings — LS, N1, HD (the head), N2, RS; lows, highs, "
                 "lows for the inverse.\n"
                 "- **The top (a veto):** every check mirrored — a prior uptrend into LS, the head highest.\n"
                 "- **Which one:** of those that pass, the most recent.",
        "HS-09": "H&S — the left shoulder belongs to the trend being reversed: for the inverse, N1 (the "
                 "rally after LS) is no higher than the highest high of the {PARAMS.prior_window} bars "
                 "before LS. A low followed by a new high is part of the uptrend, not a left shoulder.",
        "HS-02": "H&S — head clearly lowest: HD is at least {PARAMS.hs_min_head}% below the lower "
                 "shoulder.",
        "HS-03": "H&S — shoulders level: LS and RS equal within {PARAMS.hs_shoulder_tol_mult} × tol.",
        "HS-04": "H&S — shoulders similar in time: (bars from HD to RS) ÷ (bars from LS to HD) is "
                 "{PARAMS.hs_time_ratio[0]:g} to {PARAMS.hs_time_ratio[1]:g}.",
        "HS-05": "H&S — neckline not steep: the line through N1 and N2 moves at most "
                 "{PARAMS.hs_max_neck_slope} of its midpoint value per bar.",
        "HS-10": "H&S — neckline drift: from N1 to N2 the neckline falls (inverse) or rises (top) by at most "
                 "{HS_MAX_NECK_CHANGE}% in total, however long the pattern.",
        "HS-06": "H&S — shoulders stand off the neckline: each shoulder is at least {PARAMS.hs_min_shoulder}% "
                 "beyond the neckline on its own date (below it, for the inverse). It rarely bites at the "
                 "default minimum swing (see Caveats).",
        "HS-07": "H&S — length: {PARAMS.hs_days[0]} to {PARAMS.hs_days[1]} bars from LS to RS.",
        "HS-08": "H&S — classic volume: switched off.",
        # ---- triangles, wedges, rectangles (ATRI, SYMM, FWDG, RECT)
        "TR-01": "Lines — window and scale: every confirmed swing {PARAMS.tr_days[0]} to {PARAMS.rc_days[1]} "
                 "bars before today is tried as the start S, with minor swings when S is under "
                 "{PARAMS.tr_scale_days} bars back and major swings otherwise.\n\n"
                 "- **Fit:** the upper line through every swing high from S to yesterday, the lower through "
                 "every swing low; at least 2 of each.\n"
                 "- **Which one:** of each kind that passes, the one with the most touches, then the "
                 "longest.",
        "TL-05": "Lines — kind, from the two slopes:\n\n"
                 "- **Rectangle (RECT):** both flat.\n"
                 "- **Ascending triangle (ATRI):** upper flat, lower rising.\n"
                 "- **Symmetrical triangle (SYMM):** upper falling, lower rising, neither slope more than "
                 "{PARAMS.sym_slope_ratio} times the other.\n"
                 "- **Falling wedge (FWDG):** both falling, the upper faster.\n"
                 "- **Topping (vetoes):** descending triangle (lower flat, upper falling); rising wedge "
                 "(both rising, the lower faster).\n\n"
                 "Any other pair — diverging lines, a lopsided symmetrical — is no pattern.",
        "TL-03": "Lines — price contained: no close from S to yesterday is beyond either line by more than "
                 "tol.",
        "TL-04": "Lines — breakout side clean: from S to the breakout line's last touch, no close is beyond "
                 "that line by more than {BO_BUFFER}%. Closes within k bars of one of its touches are "
                 "exempt.\n\n"
                 "- **Breakout line:** the upper one for ATRI, SYMM, FWDG and RECT; the lower one for the "
                 "topping kinds.\n"
                 "- **Why:** a close through the line that was touched again later was a breakout that "
                 "came back, so the line was not the boundary.",
        "TR-02": "Lines — touches: at least {PARAMS.tr_min_touches_side} swings on each line and "
                 "{PARAMS.tr_min_touches} in all. Rectangle (RC-02): {PARAMS.rc_min_touches_side} on each, "
                 "{PARAMS.rc_min_touches} in all. The touches need not alternate between the lines.",
        "RC-03": "Rectangle height: (upper − lower) ÷ lower at S is {PARAMS.rc_height[0]:g}% to "
                 "{PARAMS.rc_height[1]:g}%.",
        "RC-04": "Rectangle length: {PARAMS.rc_days[0]} to {PARAMS.rc_days[1]} bars from S to today. A "
                 "rectangle runs no further checks.",
        "TR-03": "Triangle/wedge — converging: the lines meet (the apex) after today.",
        "TR-04": "Triangle/wedge — length: {PARAMS.tr_days[0]} to {PARAMS.tr_days[1]} bars from S to "
                 "today.",
        "TR-05": "Triangle/wedge — apex zone: today is {PARAMS.tr_apex_zone[0]:g} to "
                 "{PARAMS.tr_apex_zone[1]:g} of the way from S to the apex, in bars.\n\n"
                 "- **Past the far end:** void.\n"
                 "- **Before the near end:** the lines have barely converged; not yet a pattern.",
        "WG-04": "Wedge — real convergence: the steeper line slopes at least {WEDGE_MIN_CONVERGE} times the "
                 "shallower one; nearer parallel is a channel.",
        "TR-06": "Triangle/wedge — volume declines: a straight line fitted to log(volume) from S through "
                 "today slopes down.",
        "TR-07": "Triangle/wedge — big enough: the height at S, upper − lower, is at least "
                 "{PARAMS.tr_min_height}% of today's close.",
        # ---- flat base (FBASE)
        "FB-02": "Flat base window: the longest run of N bars ending today, N from {PARAMS.fb_days[0]} to "
                 "{PARAMS.fb_days[1]}, whose (highest high − lowest low) ÷ highest high is at most "
                 "{PARAMS.fb_max_depth}%. Today's bar is inside the window, so its high is part of the "
                 "trigger (see Caveats).",
        "FB-01": "Flat base — prior advance: the window's first close is at least {PARAMS.fb_prior_move}% "
                 "above the lowest low of the {PARAMS.prior_window} bars before it.",
        "FB-03": "Flat base — long enough: at least {PARAMS.fb_days[0]} bars, which the window search "
                 "already guarantees.",
        "FB-04": "Flat base — near the highs: the window high is at least {PARAMS.fb_near_high} × the "
                 "52-week high.",
        "FB-05": "Flat base — volume dry-up: switched off.",
        # ---- flag or pennant (FLAG) and high tight flag (HTF)
        "FL-01": "Flag — pause length: the pole top P1 is {PARAMS.flag_days[0]} to {PARAMS.flag_days[1]} "
                 "bars before today (HTF-04: {PARAMS.htf_flag_days[0]} to {PARAMS.htf_flag_days[1]}), and "
                 "no high from P1 to yesterday is above it.\n\n"
                 "- **Several lengths fit:** the one with the biggest pole gain is used.",
        "FP-01": "Flag — pole gain: P1's high ÷ P0's low − 1 is at least {PARAMS.pole_gain}% (HTF-01: "
                 "{PARAMS.htf_gain}%).\n\n"
                 "- **P0:** the lowest low of the 2 × {PARAMS.pole_days} bars up to P1 (high tight flag: "
                 "{PARAMS.htf_pole_days[1]} bars).",
        "FP-02": "Flag — pole speed: at most {PARAMS.pole_days} bars from P0 to P1 (HTF-02: "
                 "{PARAMS.htf_pole_days[0]} to {PARAMS.htf_pole_days[1]}).",
        "HTF-03": "High tight flag — depth: (P1 − the lowest low since P1, today's included) ÷ P1 is at most "
                  "{PARAMS.htf_depth}%. The high tight flag runs no further checks.",
        "FP-03": "Flag — pole volume: average volume from P0 to P1 is at least {PARAMS.pole_rv} × the 50-bar "
                 "average before P0.",
        "FL-02": "Flag — shallow pause: (P1 − the lowest low since P1) ÷ (P1 − P0) is at most "
                 "{PARAMS.flag_retrace}%.",
        "FL-03": "Flag — volume declines: log(volume) from the bar after P1 through today slopes down.",
        "FL-04": "Flag — shape: lines through the minor swings from P1 to yesterday (at least 2 highs and 2 "
                 "lows) form a flag or a pennant.\n\n"
                 "- **Flag:** both slopes at most +{PARAMS.flat_slope} (falling or flat), neither more than "
                 "{PARAMS.flag_slope_ratio} times the other.\n"
                 "- **Pennant:** upper falling, lower rising, apex after today.\n\n"
                 "No touch count or containment test applies.",
        # ---- the topping patterns (vetoes: G2, W1)
        "DT-01–04": "Double top (a veto): three consecutive major swings — top B, trough C, top D.\n\n"
                    "- **DT-01:** B at least {PARAMS.db_prior_move}% above the lowest low of the "
                    "{PARAMS.prior_window} bars before it.\n"
                    "- **DT-02:** B and D equal within tol.\n"
                    "- **DT-03:** C at least {PARAMS.db_min_peak}% below the higher top.\n"
                    "- **DT-04:** {PARAMS.db_days[0]} to {PARAMS.db_days[1]} bars from B to D.\n"
                    "- **Levels:** T = C; void above the higher top × (1 + tol).",
        # ---- the life of every pattern
        "BO-01": "Breakout: today's close is above T × (1 + {BO_BUFFER}%) (topping patterns: below "
                 "T × (1 − {BO_BUFFER}%)).",
        "BO-02": "Breakout volume: today's volume is at least {BO_VOL} × VOL50. Topping patterns have no "
                 "volume test.\n\n"
                 "- **VOL50 is taken before:** the left lip A (CUP); the start S (ATRI, SYMM, FWDG, RECT); "
                 "the window start (FBASE); P0 (FLAG, HTF); the bar a pattern completed, {K_MAJOR} bars "
                 "after its last point (CUPNH, DBOT, TBOT, IHS).",
        "BO-03": "Void: a close below X after the last key point — for a cup without handle, double, triple "
                 "or head and shoulders only. The other patterns are detected afresh each bar and do not "
                 "test X; their own checks (the handle low, the lines, the window) end them instead.",
        "BO-04": "Expiry: a cup without handle, double, triple or head and shoulders is void when no "
                 "breakout comes within {MAX_WAIT} bars of completing — {K_MAJOR} bars after its last "
                 "point.\n\n"
                 "- **The others have no clock:** CH-09's {PARAMS.handle_days[1]}-bar handle, TR-05's apex "
                 "zone and FL-01's pause bound them; a rectangle or flat base never expires.\n"
                 "- **Breakout search (EARLY_BREAKOUT = {EARLY_BREAKOUT}):** starts the bar after the last "
                 "point, so a breakout during the {K_MAJOR} confirming bars counts — and is already old when "
                 "the pattern becomes visible.",
        "BO-05": "Failed: within {FAIL_DAYS} bars after a breakout, a close back below T × (1 − tol) "
                 "(topping: above T × (1 + tol)). A failed pattern is no longer live, which matters for the "
                 "topping vetoes. A pattern state only: no position is sold on it.",
    }
    setup_docs = {
        CUP: "Cup with handle: a rounded cup, then a short handle in its upper half, bought when price "
             "clears the handle's high.\n\n"
             "- **Checks:** CH-01 to CH-12 in the table above.\n"
             "- **Trigger T:** the handle's highest high (bar after C to yesterday), raised to the left lip "
             "A when lower, so the buy clears the left rim. It is not raised to C when C is the higher lip.\n"
             "- **Invalidation X:** the handle low D.\n"
             "- **Height H:** max(A, C) − B.\n"
             "- **Life:** detected afresh every bar while the handle is {PARAMS.handle_days[0]} to "
             "{PARAMS.handle_days[1]} bars old; no BO-04 clock.",
        CUPNH: "Cup without handle: the same cup, bought when price clears the old high before any "
               "handle forms.\n\n"
               "- **Checks:** CH-01 to CH-06 and CH-12; no handle checks.\n"
               "- **Trigger T:** max(A, C), the old high — not C, which may sit as low as "
               "{PARAMS.right_lip[0]:g} × A, under the left lip's supply.\n"
               "- **Invalidation X:** the cup low B.\n"
               "- **Height H:** max(A, C) − B.\n"
               "- **Life:** complete {K_MAJOR} bars after C; void after {MAX_WAIT} more bars without a "
               "breakout, or on a close below B.\n"
               "- **Switch:** traded only while TRADE_CUPNH = 1 (now {TRADE_CUPNH}). It fires at the rim, "
               "so its resting order can block the cup with a handle that forms later.",
        DBOT: "O'Neil's W: a continuation base with two lows, the second undercutting the first, "
              "bought on the break of the peak between them.\n\n"
              "- **Checks:** DB-01 (W), DB-02 (W), OW-01, OW-02, DB-03, DB-04 above.\n"
              "- **Trigger T:** the middle peak C.\n"
              "- **Invalidation X:** the lower low × (1 − tol).\n"
              "- **Height H:** C − the lower low.\n"
              "- **Life:** complete {K_MAJOR} bars after D; void after {MAX_WAIT} more bars without a "
              "breakout, or on a close below X.",
        TBOT: "Triple bottom: three level lows after a decline, bought on the break of the higher of the "
              "two peaks between them.\n\n"
              "- **Checks:** DB-01 to DB-04 (triple) and TL-LV above.\n"
              "- **Trigger T:** the higher of P1 and P2.\n"
              "- **Invalidation X:** the lowest low × (1 − tol).\n"
              "- **Height H:** T − the lowest low.\n"
              "- **Life:** complete {K_MAJOR} bars after B3; void after {MAX_WAIT} more bars without a "
              "breakout, or on a close below X.",
        IHS: "Inverse head and shoulders: three lows with the middle one lowest, bought on a close "
             "above the neckline.\n\n"
             "- **Checks:** HS-01 to HS-10 above.\n"
             "- **Trigger T:** the neckline through N1 and N2, extended to today — it moves each bar.\n"
             "- **Invalidation X:** the right shoulder's low; a close below it voids the pattern.\n"
             "- **Height H:** the neckline at the head's date − the head.\n"
             "- **Life:** complete {K_MAJOR} bars after RS; void after {MAX_WAIT} more bars without a "
             "breakout.",
        ATRI: "Ascending triangle: a flat upper line over a rising lower line, bought on a close above "
              "the upper line.\n\n"
              "- **Checks:** TR-01, TL-05, TL-03, TL-04, TR-02 to TR-07 above.\n"
              "- **Trigger T:** the upper line today.\n"
              "- **Invalidation X:** the lower line today.\n"
              "- **Height H:** upper − lower at the start S.",
        SYMM: "Symmetrical triangle: a falling upper and a rising lower line converging at similar "
              "rates, bought on a close above the upper line.\n\n"
              "- **Checks and levels:** as ATRI.\n"
              "- **Direction:** only the upward break is traded.",
        FWDG: "Falling wedge: two falling lines, the upper falling faster, bought on a close above the "
              "upper line.\n\n"
              "- **Checks:** as ATRI, plus WG-04.\n"
              "- **Levels:** T = the upper line today, X = the lower line today, H = the height at S.",
        RECT: "Rectangle: two flat lines, bought on a close above the upper one.\n\n"
              "- **Checks:** TR-01, TL-05, TL-03, TL-04, RC-02 (in TR-02), RC-03, RC-04 above.\n"
              "- **Levels:** T = the upper line today, X = the lower line today, H = the height at S.\n"
              "- **Life:** no expiry. Only the upward break is traded.",
        FBASE: "Flat base: a shallow sideways range near the highs after an advance, bought above its "
               "high.\n\n"
               "- **Checks:** FB-02, FB-01, FB-03, FB-04 above.\n"
               "- **Levels:** T = the window high (today's high included), X = the window low, H = T − X.\n"
               "- **In practice:** never breaks out on its own bar (see Caveats), so only a live TRADE ON "
               "TRIGGER.",
        FLAG: "Bull flag or pennant: a steep, fast pole, then a short shallow pause, bought on a close "
              "above the pause's upper line.\n\n"
              "- **Checks:** FL-01, FP-01, FP-02, FP-03, FL-02, FL-03, FL-04 above.\n"
              "- **Trigger T:** the pause's upper line today.\n"
              "- **Invalidation X:** the lowest low since P1.\n"
              "- **Height H:** the pole, P1 − P0.",
        HTF: "High tight flag: a pole that rises at least {PARAMS.htf_gain}% in {PARAMS.htf_pole_days[0]} to "
             "{PARAMS.htf_pole_days[1]} bars, then a {PARAMS.htf_flag_days[0]} to {PARAMS.htf_flag_days[1]}-bar "
             "flag no deeper than {PARAMS.htf_depth}%, bought above the flag's high.\n\n"
             "- **Checks:** FL-01 (HTF-04), FP-01 (HTF-01), FP-02 (HTF-02), HTF-03 above.\n"
             "- **Trigger T:** the highest high from P1 to yesterday — P1 itself.\n"
             "- **Invalidation X:** the flag low.\n"
             "- **Height:** none, so the target is {MIN_R}R (see Target).",
    }
    entry_rules = (
        "BO-01, BO-02 — the signal. A buy starts from a TRADE - HIGH CONFIDENCE signal on a session's "
        "close: the chosen pattern broke out on that bar, no watch flag is up, and the plan passes the stop "
        "and target tests. Nothing is bought on the signal bar itself.",
        "A buy-stop at the breakout close.\n\n"
        "- **Price:** max(T × (1 + {BO_BUFFER}%), the signal close), rounded up to the tick. On a breakout "
        "bar the close is already above T × (1 + {BO_BUFFER}%), so it is the close.\n"
        "- **Fills:** the first later session whose high reaches it, at that price — or at the open if the "
        "stock opens above it.\n"
        "- **Waits:** up to 10 business days, the backtest's limit for a resting order.\n"
        "- **Cancelled:** if a low reaches the stop before it fills.",
        "Checks at the fill. The order is skipped if:\n\n"
        "- the fill is more than {MAX_CHASE_PCT}% above T;\n"
        "- the stop is more than {MAX_RISK_PCT}% below the fill;\n"
        "- the target is less than {MIN_R} times the risk away, measured from the fill.\n\n"
        "A gap at the open raises the price paid without moving the stop or the target, and an order can "
        "wait for a free slot; neither may buy whatever the open is.",
        "One entry per pattern. A pattern is identified by its code and first key point (A, B, B1, LS, S "
        "or P0). Once bought it is never bought again, even after a stop-out. A symbol already held, or with "
        "an order resting, takes no new order.",
        "Live screen only: a complete pattern that has not broken out shows as TRADE ON TRIGGER, with a "
        "buy-stop at T × (1 + {BO_BUFFER}%) rounded up — the order to place by hand. The backtest places no "
        "such order; it buys breakout bars only.",
    )
    stop_rules = (
        "Where it goes: at the pattern's invalidation level X, held between two limits, rounded down to "
        "the tick.\n\n"
        "- **Not wider than:** {MAX_STOP_ATR} ATR below the entry — X can sit a full pattern height below "
        "T.\n"
        "- **Not tighter than:** max({MIN_STOP_ATR} ATR, {MIN_STOP_PCT}%) below the entry.\n"
        "- **X per pattern:** the handle low (CUP); the cup low (CUPNH); the lower low × (1 − tol) (DBOT, "
        "TBOT); the right shoulder (IHS); the lower line today (ATRI, SYMM, FWDG, RECT); the window low "
        "(FBASE); the lowest low since the pole top (FLAG, HTF).",
        "It defines the risk. Entry − stop is 1R; every result is counted in R.",
        "Too wide: a stop more than {MAX_RISK_PCT}% below the entry makes the plan WATCH, not a trade. It is "
        "tested on the signal close and again on the fill.",
        "How it sells: a standing sell order that fills during the session when the low touches it. If the "
        "stock opens below the stop it sells at that open, so a gap can cost more than 1R. When the stop and "
        "the target are both touched in one session, the stop is assumed first. It never moves, unless "
        "`--breakeven-r` is given.",
    )
    target_rules = (
        "BO-06 — a real sell order at the measured move: target = entry + H, the height added to the "
        "planned entry (the signal close), not to T. It sells the whole position when the high reaches it, "
        "at the target — or at the open if the stock opens above it. The chart's \"measured target\" line "
        "is T + H, a little lower.",
        "High tight flag: no height, so target = entry + {MIN_R} × the risk.",
        "The {MIN_R}:1 test: H ÷ the risk must be at least {MIN_R}, or the plan is WATCH. Tested on the "
        "signal close and again on the fill; never padded.",
    )
    exit_rules = (
        "Only the bracket: the stop or the target, whichever is touched first. No time stop, trend exit or "
        "failed-breakout exit (BO-05 marks a pattern failed but sells nothing). A position still open when "
        "a backtest ends is valued at the last close.",
        "Optional trade management, off in this strategy's own runs so its value is measured, not assumed: "
        "`--breakeven-r` (stop to entry plus costs once the high reaches that many R), `--time-stop-mult` "
        "(sold at the close after that multiple of the pattern's length — its first key point to the entry, "
        "in bars), `--time-stop-bars`, `--partial-at-target`, and `--exit-mode` for a trailing exit.",
        "Live: the screen does not manage positions. The plan's stop and target are the two orders to place.",
    )
    sizing_rules = (
        "Risk per trade: shares = the market's risk per trade (cfg.risk_pct, 1% of equity) ÷ (entry − "
        "stop), so a stop-out costs about the same whatever the stop's width.",
        "Caps: no position over cfg.max_position_pct (25%) of equity, and never more than the cash "
        "available — a short fill is bought smaller, not skipped.",
        "Slots: at most cfg.max_open_positions (10) at once. An order that triggers with every slot full "
        "keeps resting until one frees or it expires.",
        "Same-day ranking: when more orders fill than slots are free, the higher setup quality goes first.\n\n"
        "- **Quality:** 2.0 − 0.1 × the pattern's place in G1's priority order (0 for CUP, counting "
        "up, at most 10), taken for the first live pattern in setup-list order.\n"
        "- **Less:** 0.5 for W1, 1.0 for W2; never below 0.\n"
        "- **Cup rims:** +{RIM_IDEAL_BONUS} ideal, −{RIM_LOOSE_PENALTY} loose (CH-03).",
        "Live screen: a plan too large to buy one share at the account size is WATCH.",
    )
    filter_rules = (
        "Pre-filter: the 20-day average traded value (close × volume) must reach cfg.screener.min_dollar_volume, "
        "an ATR14 value must exist, and the stock needs {min_bars} bars of history. No price floor and no "
        "trend test: the near_highs screen's criteria are not applied (see Caveats).",
        "Market regime: on the live screen a risk-off market downgrades every decision one tier. A backtest "
        "applies no downgrade; `--market-filter` instead drops new signals and cancels resting orders while "
        "the market filter is risk-off.",
        "Signal-bar tests: a backtest buys only TRADE - HIGH CONFIDENCE, so any failed gate (G1–G5) or "
        "raised watch flag (W1–W3) on the breakout bar means no trade.",
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "The chosen pattern broke out on this bar (BO-01 and BO-02), every gate "
                                 "passes, no watch flag is up, the stop is within {MAX_RISK_PCT}% and the "
                                 "measured move is at least {MIN_R}R. The only tier a backtest buys.",
        "TRADE_ON_TRIGGER": "The chosen pattern is complete but has not broken out: place a buy-stop at "
                            "T x (1 + {BO_BUFFER}%). Also a breakout capped by W1 or W3, or a high-confidence "
                            "row downgraded by a risk-off market.",
        "WATCH_WAIT": "Close through the trigger on thin volume (W2), a stop more than {MAX_RISK_PCT}% away, "
                      "a measured move under {MIN_R}R, or a position too large for the account.",
        "AVOID": "A hard gate failed — including G1, no tradeable pattern — or the plan has no valid stop.",
    }
    regime_note = (
        "Live screen: when the market regime is risk-off, every decision is downgraded one tier (HIGH "
        "CONFIDENCE → ON TRIGGER → WATCH → AVOID) and the reason says 'market-regime downgrade applied'. A "
        "backtest never applies this; `--market-filter` blocks new buys instead."
    )
    param_docs = (
        ("Swing scales", "K_MAJOR",
         "Bars each side defining a confirmed swing point: {K_MINOR} for "
         "flags and short triangles, {K_MAJOR} for cups, doubles, triples, shoulders and long triangles. "
         "A swing at bar i is only known at bar i + k."),
        ("Minimum swing", "MIN_SWING_PCT",
         "Moves smaller than max({MIN_SWING_PCT}%, {ATR_MULT} x ATR/close) "
         "are wiggles and are dropped before any pattern is looked for."),
        ("Price tolerance", "TOL_PCT",
         "Two prices count as equal within max({TOL_PCT}%, {TOL_ATR_MULT} x "
         "ATR/close) — wider on a volatile stock, which a fixed percentage "
         "is not."),
        ("Prior-trend window", "PARAMS.prior_window",
         "PT-01/PT-02: bars before a pattern's first point searched for the low (or high) its prior trend "
         "is measured from."),
        ("Flat line", "PARAMS.flat_slope",
         "TL-05: a line whose slope per bar is within this fraction of its value is flat."),
        ("Cup depth", "PARAMS.cup_depth",
         "CH-02: the cup's fall from the left lip, in %."),
        ("Cup length", "PARAMS.cup_days",
         "CH-04: bars from the left lip to the right lip."),
        ("Handle depth", "PARAMS.handle_depth",
         "CH-08: the handle's fall from the right lip, in %."),
        ("Handle length", "PARAMS.handle_days",
         "CH-09: bars from the right lip to today."),
        ("Breakout buffer", "BO_BUFFER",
         "BO-01: a close must clear the trigger by this percentage "
         "({BO_BUFFER}%)."),
        ("Breakout volume", "BO_VOL",
         "BO-02: and do it on {BO_VOL}x the 50-bar average volume before the pattern."),
        ("Breakout expiry", "MAX_WAIT",
         "BO-04: bars after completion within which a double, triple, head and shoulders or cup without "
         "handle must break out."),
        ("Breakout age", "BREAKOUT_MAX_AGE",
         "Bars after its breakout bar on which a confirmed pattern is still an "
         "entry ({BREAKOUT_MAX_AGE}: the breakout bar only)."),
        ("Cup without handle", "TRADE_CUPNH",
         "1 trades CUPNH; 0 detects and draws it but never buys it."),
        ("Rim alignment", "RIM_IDEAL_PCT",
         "A cup's rims are graded, not judged: the right rim within {RIM_IDEAL_PCT}% of the left is "
         "ideal (+{RIM_IDEAL_BONUS} setup quality), within {RIM_OK_PCT}% acceptable (no change), beyond "
         "that loose (-{RIM_LOOSE_PENALTY}). No published percentage exists; these are starting points."),
        ("Cup under its rim", "CUP_UNDER_RIM",
         "CH-12 ({CUP_UNDER_RIM} = on): no high between a cup's lips may top the higher "
         "lip by more than the price tolerance, max({TOL_PCT}%, {TOL_ATR_MULT} x ATR/close)."),
        ("Cup symmetry", "CUP_RIGHT_LEFT_MIN",
         "CH-06: a cup's recovery (B to C) must take at least "
         "{CUP_RIGHT_LEFT_MIN}x as many bars as its decline (A to B)."),
        ("H&S left shoulder", "HS_ORIGIN",
         "HS-09 ({HS_ORIGIN} = on): the reaction after the left shoulder may not run past "
         "the point the reversed trend began from -- a low followed by a new high is part of the uptrend."),
        ("H&S neckline drift", "HS_MAX_NECK_CHANGE",
         "HS-10: the neckline may run against the pattern (an inverse's falling, a top's "
         "rising) by at most {HS_MAX_NECK_CHANGE}% from its left anchor to its right."),
        ("Early breakout", "EARLY_BREAKOUT",
         "BO-04 ({EARLY_BREAKOUT} = on): a pattern that completes once is confirmed {K_MAJOR} bars "
         "after its last point, but its breakout is searched from that point -- a close through T in "
         "between is the breakout, already old when the pattern can be seen."),
        ("Wedge convergence", "WEDGE_MIN_CONVERGE",
         "WG-04: a wedge's steeper line slopes at least {WEDGE_MIN_CONVERGE}x the "
         "shallower one; nearer parallel is a channel."),
        ("Breakout-side containment", "CONTAIN_BREAKOUT_SIDE",
         "TL-04 ({CONTAIN_BREAKOUT_SIDE} = on): no close before the breakout line's last "
         "touch beyond that line by more than the breakout buffer ({BO_BUFFER}%) -- price broke out and "
         "came back, so the line was not the boundary. Closes within k bars of a touch are exempt; TL-03's "
         "wider tolerance still applies."),
        ("Triple drift", "TRIPLE_MAX_DRIFT",
         "TL-LV: a triple bottom's stepping lows may move at most {TRIPLE_MAX_DRIFT}% "
         "first to third."),
        ("W shape", "W_MIN_DEPTH",
         "OW-01/OW-02: the W is {W_MIN_DEPTH}-{W_MAX_DEPTH}% deep from the high it corrects and at least "
         "{W_MIN_DAYS} bars long; the second low undercuts the first by up to {W_UNDERCUT_MAX}%."),
        ("Actionable band", "MAX_CHASE_PCT",
         "Gate G5 wants the close between {MAX_BELOW_TRIGGER_PCT}% below the "
         "trigger and {MAX_CHASE_PCT}% above it; the fill must be within {MAX_CHASE_PCT}% above it."),
        ("Earnings window", "EARNINGS_DAYS",
         "Gate G3: weekdays to the next earnings date that block a trade (live only)."),
        ("Volatility ceiling", "MAX_ATR_PCT",
         "Gate G4: ATR14 as a % of the close."),
        ("Overbought", "OVERBOUGHT_RSI",
         "Flag W3: RSI14 above this caps the decision at TRADE ON TRIGGER."),
        ("Stop width", "MAX_STOP_ATR",
         "The stop sits at the pattern's invalidation level but never "
         "wider than {MAX_STOP_ATR} ATR nor tighter than "
         "max({MIN_STOP_ATR} ATR, {MIN_STOP_PCT}%) below the entry."),
        ("Maximum risk", "MAX_RISK_PCT",
         "A stop more than {MAX_RISK_PCT}% below the entry (or the fill) is WATCH, not a trade."),
        ("Minimum reward", "MIN_R",
         "A measured move projecting under {MIN_R}R (at the signal or at the fill) is not a trade."),
        ("Minimum price", "cfg.screener.min_price",
         "Not applied by this strategy, live or in a backtest: its pre-filter checks liquidity only "
         "(base.tradable_point_in_time)."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume",
         "Pre-filter: the 20-day average of close x volume must reach this."),
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
            if code == CUPNH and not TRADE_CUPNH:
                result.setups[code] = False   # switched off: its resting order would block the handle's
                continue
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
        meta = {"base_id": f"{ctx.extras.get('pattern')}:{anchor}"} if anchor else {}
        if anchor:
            # the pattern's first key point: a time stop given as a multiple of the pattern's duration
            # (--time-stop-mult) counts the bars from here to the entry. Read only when that flag is on.
            meta["setup_start"] = anchor
        # The checks made on the signal bar, held against the price actually paid. An order that
        # triggers while every slot is full keeps resting, and used to fill at whatever the open was
        # once a slot freed up: AUBANK.NS (ascending triangle, trigger 715.30) was bought 8 sessions
        # later at 770.70, 7.7% past the trigger, with 0.14R left to the target.
        trigger = ctx.extras.get("trigger")
        if trigger:
            meta.update(max_fill=float(trigger) * (1 + MAX_CHASE_PCT / 100), min_structural_r=MIN_R,
                        max_risk_pct=MAX_RISK_PCT / 100)
        return meta

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
                   "G3": "No earnings within {EARNINGS_DAYS} days", "G4": "Volatility sane", "G5": "Close near the trigger"}

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
        # a trigger read off a sloping line (a neckline, a triangle's side) is that line at the signal bar:
        # drawn across the whole pattern it would cross the line, so it is a short tick at the bar instead
        sloped = any(abs(ln["p1"] - ln["p0"]) > 1e-9 for ln in geo.get("lines") or [])
        out.append({"shape": "level", **({"bars": 5} if sloped else span), "to": d, "price": float(e["trigger"]),
                    "role": "stop" if bear else "pivot",
                    "label": f"{'breakdown' if bear else 'trigger'} {e['trigger']:.2f} — confirms the {name.lower()}"})
        if e.get("invalidation"):
            out.append({"shape": "level", **({"bars": 5} if sloped else span), "to": d, "price": float(e["invalidation"]),
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
