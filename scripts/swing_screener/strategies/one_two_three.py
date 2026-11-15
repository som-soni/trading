"""1-2-3 reversal -- Victor Sperandeo's trend-change pattern (Trader Vic: Methods of a Wall Street Master, 1991).

A downtrend has changed when (1) it makes a low, (2) the rally from it makes a high, (3) the pullback holds
above the low, and price then breaks above point 2. On daily bars:

  * point 1: the lowest low of the LOOK sessions before today, which is also the lowest low of the
    DOWNTREND_BARS sessions ending at it, with the 200-day at point 1 falling (below its value
    DOWNTREND_SLOPE_BARS sessions earlier, the same lag as the enriched `sma200_21d_ago`);
  * point 2: the highest high after point 1, at least P12_MIN_BARS sessions after it;
  * point 3: the lowest low after point 2, at least P23_MIN_BARS sessions after it and before today; above
    point 1 and retracing at least RETRACE_MIN of the 1-to-2 rally;
  * today's close is still under point 2: a buy-stop at point 2's high, stop at point 3's low, target the
    measured move point 2 + (point 2 − point 1).
"""

from ..core.context import StockContext
from ..marketdata import corporate_actions
from .base import StrategyResult
from .swing_base import PASS_RULE, SwingSetupStrategy

LOOK = 60                # point 1: the lowest low of this many sessions before today
DOWNTREND_BARS = 120     # G1: point 1 is also the lowest low of this many sessions ending at it
P12_MIN_BARS = 3         # point 2 is at least this many sessions after point 1
P23_MIN_BARS = 2         # point 3 is at least this many sessions after point 2
DOWNTREND_SLOPE_BARS = 21  # G1: the 200-day at point 1 is below its value this many sessions earlier
RETRACE_MIN = 0.3        # G2: point 3 retraces at least this fraction of the 1-to-2 rally
MIN_STOP_PCT = 1.0       # a stop closer than this % below the entry is not bought
MAX_STOP_PCT = 15.0      # nor one further than this %
NOMINAL_TARGET_R = 2     # the target when the measured move is not above the entry
HOLD_BARS = 20           # backtest_args: sold at the close of this session after the entry

S1 = "S1"


class OneTwoThreeStrategy(SwingSetupStrategy):
    key = "one_two_three"
    name = "1-2-3 reversal"
    description = ("Sperandeo's trend change: a low after a decline, a rally, a higher low, then a buy-stop at "
                   "the rally's high with the stop under the higher low.")
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "v1: the 1-2-3 bottom on daily bars -- point 1 the {LOOK}-session low and the {DOWNTREND_BARS}-session "
         "low under a falling 200-day, point 2 the high after it, point 3 a higher low retracing at least "
         "{RETRACE_MIN} of the rally; a buy-stop at point 2, stop at point 3, measured-move target, "
         "{HOLD_BARS}-session limit."),
    )
    behaviour = "mean_reversion"
    style = "reversal"
    gate_codes = ("G1", "G2")
    screen_key = "above_200"
    screen_gates: dict = {}
    setup_codes = (S1,)
    setup_names = {S1: "1-2-3 bottom, break pending"}
    gate_titles = {"G1": "Point 1 ends a downtrend", "G2": "Point 3 a higher low"}
    order = ""
    expiry_bdays = 5
    plan_code = "OT"
    extra_columns = ("p1_low", "p2_high", "p3_low", "retrace", "level_entry", "level_stop", "level_target")
    extra_numeric_columns = extra_columns

    thesis = (
        "A downtrend is a series of lower highs and lower lows. When a rally from the low is followed by a pullback "
        "that holds above that low, and price then takes out the rally's high, the series is broken: sellers no "
        "longer push price to new lows and buyers have absorbed the decline. Victor Sperandeo, *Trader Vic: "
        "Methods of a Wall Street Master* (1991). The catalogue grades it D (a textbook rule, no published test), "
        "credibility 1."
    )
    how_it_works = (
        "**Universe.** Every liquid stock. The rule trades out of downtrends, so the Above the 200-day screen "
        "supplies the universe only, with no gate taken from it.",
        "**Point 1 (G1).** The lowest low of the {LOOK} sessions before today. It must also be the lowest low of "
        "the {DOWNTREND_BARS} sessions ending at it (a real low after a decline), and the 200-day average at point "
        "1 must be below its value {DOWNTREND_SLOPE_BARS} sessions earlier (a downtrend).",
        "**Point 2.** The highest high after point 1, at least {P12_MIN_BARS} sessions after it, through yesterday.",
        "**Point 3 (G2).** The lowest low after point 2, at least {P23_MIN_BARS} sessions after it, through "
        "yesterday. It must be above point 1 (a higher low) and retrace at least {RETRACE_MIN} of the 1-to-2 rally.",
        "**The signal (S1).** Today's close is still below point 2: the break has not happened yet.",
        "**The order.** A buy-stop at point 2's high for {expiry_bdays} sessions.",
        "**Stop and exit.** The stop is point 3's low. The target is the measured move, point 2 + (point 2 − point "
        "1); entry + {NOMINAL_TARGET_R} R if that is not above the entry. The position is sold at the close of "
        "session {HOLD_BARS} after the entry if neither was hit.",
    )
    caveats = (
        "**Mechanical points.** Sperandeo draws the points and the trendline by eye, and adds a trendline break as "
        "the first of his three conditions; here the points are fixed windows and the trendline is not drawn.",
        "**The 200-day slope.** The downtrend test reads the 200-day's slope over {DOWNTREND_SLOPE_BARS} sessions at point 1; the "
        "book reads the trend from the chart.",
        "**The exit is a stand-in.** The book does not fix an exit; the measured move and the {HOLD_BARS}-session "
        "limit are this backtest's.",
        "**Survivorship.** The universe is today's stock lists; declines that kept going into a delisting are "
        "missing, which flatters a bottom-buying rule.",
        "**Run it with its flags** (`backtest_args`).",
        corporate_actions.CAVEAT_TRADED,
    )
    status = ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (reversal group, grade D, "
              "credibility 1); optimise-stage runs queued in both markets. " + PASS_RULE)
    gate_docs = {
        "G1": ("Point 1 ends a downtrend.\n\n- **Test:** point 1 (the lowest low of the {LOOK} sessions before "
               "today) is the lowest low of the {DOWNTREND_BARS} sessions ending at it, and the 200-day at point 1 "
               "is below its value {DOWNTREND_SLOPE_BARS} sessions earlier.\n- **Fails:** an older, lower low exists, the 200-day was "
               "not falling, or too little history."),
        "G2": ("Point 3 is a higher low.\n\n- **Test:** points 2 and 3 exist ({P12_MIN_BARS}+ sessions after point "
               "1 and {P23_MIN_BARS}+ after point 2, before today), point 3 is above point 1, and (point 2 − point "
               "3) ÷ (point 2 − point 1) is at least {RETRACE_MIN}.\n- **Fails:** no room for the points, point 3 "
               "at or under point 1, or too shallow a pullback."),
    }
    watch_docs: dict = {}
    setup_docs = {
        S1: ("1-2-3 bottom, break pending.\n\n- **Test:** today's close is below point 2's high.\n- **Signal:** a "
             "buy-stop at point 2's high for {expiry_bdays} sessions; the stop is point 3's low."),
    }
    entry_rules = (
        "Signal. G1, G2 and S1 on today's close, with a stop between {MIN_STOP_PCT}% and {MAX_STOP_PCT}% below the "
        "entry, graded TRADE - HIGH CONFIDENCE.",
        "Order. A buy-stop at point 2's high for {expiry_bdays} sessions (backtest: fills when a session's high "
        "reaches it, at the open if it gaps above; cancelled if the stop is hit first).",
        "One position per stock.",
    )
    stop_rules = ("Where it goes. Point 3's low, rounded down to the tick. It defines 1R; it does not move.",)
    target_rules = ("The measured move: point 2 + (point 2 − point 1); entry + {NOMINAL_TARGET_R} R when that is "
                    "not above the entry.",)
    exit_rules = (
        "Each session after the entry (backtest, the default bracket with `--time-stop-bars {HOLD_BARS}`):",
        "1. The stop, at its price or at the open if the stock gaps under it.",
        "2. The target, at its price or at the open if the stock gaps over it.",
        "3. The time limit: sold at the close of session {HOLD_BARS} after the entry.",
    )
    param_docs = (
        ("Point 1 window", "LOOK", "Point 1 is the lowest low of this many sessions before today."),
        ("Downtrend window", "DOWNTREND_BARS", "G1: point 1 is also the lowest low of this many sessions."),
        ("Rally length", "P12_MIN_BARS", "Point 2 is at least this many sessions after point 1."),
        ("Pullback length", "P23_MIN_BARS", "Point 3 is at least this many sessions after point 2."),
        ("200-day slope", "DOWNTREND_SLOPE_BARS", "G1: sessions back the 200-day at point 1 must be below."),
        ("Retracement", "RETRACE_MIN", "G2: point 3 retraces at least this fraction of the 1-to-2 rally."),
        ("Minimum stop", "MIN_STOP_PCT", "A stop closer than this % below the entry is not bought."),
        ("Maximum stop", "MAX_STOP_PCT", "A stop further than this % below the entry is not bought."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × R when the measured move is not above it."),
        ("Hold", "HOLD_BARS", "Sessions after the entry before the position is sold (--time-stop-bars)."),
        ("Order expiry", "expiry_bdays", "Sessions the buy-stop rests."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume", "The 20-day average of close × volume, at least."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
    )
    backtest_args = f"--time-stop-bars {HOLD_BARS} --rank-by setup_momentum --min-fill 0.5"

    def detect(self, ctx: StockContext, result: StrategyResult) -> None:
        d, e = ctx.daily, ctx.extras
        n = LOOK + DOWNTREND_BARS + 1
        if len(d) < n:
            result.fail("G1", "insufficient history")
            return
        tail = d.iloc[-n:]
        lows = tail["low"].to_numpy(float)
        highs = tail["high"].to_numpy(float)
        today = n - 1
        w0 = today - LOOK
        p1 = w0 + int(lows[w0:today].argmin())
        s200 = float(tail["sma200"].iloc[p1])
        s200_ago = float(tail["sma200"].iloc[p1 - DOWNTREND_SLOPE_BARS])
        lowest = lows[p1] <= lows[p1 - DOWNTREND_BARS + 1:p1 + 1].min()
        if lowest and s200 < s200_ago:
            result.ok("G1", f"point 1 {lows[p1]:.2f}, the {DOWNTREND_BARS}-session low, 200-day falling")
        elif not lowest:
            result.fail("G1", f"point 1 {lows[p1]:.2f} is not the {DOWNTREND_BARS}-session low")
        else:
            result.fail("G1", "200-day not falling at point 1")
        e.update(p1_low=float(lows[p1]))
        a2 = p1 + P12_MIN_BARS
        if a2 >= today:
            result.fail("G2", "no room for point 2")
            return
        p2 = a2 + int(highs[a2:today].argmax())
        a3 = p2 + P23_MIN_BARS
        if a3 >= today:
            result.fail("G2", "no room for point 3")
            e.update(p2_high=float(highs[p2]))
            return
        p3 = a3 + int(lows[a3:today].argmin())
        h2, l1, l3 = float(highs[p2]), float(lows[p1]), float(lows[p3])
        rally = h2 - l1
        retrace = (h2 - l3) / rally if rally > 0 else float("nan")
        e.update(p2_high=h2, p3_low=l3, retrace=retrace, level_entry=h2, level_stop=l3,
                 level_target=h2 + rally)
        if l3 > l1 and retrace >= RETRACE_MIN:
            result.ok("G2", f"point 3 {l3:.2f} above point 1 {l1:.2f}, retraces {retrace:.2f}")
        elif l3 <= l1:
            result.fail("G2", f"point 3 {l3:.2f} not above point 1 {l1:.2f}")
        else:
            result.fail("G2", f"retrace {retrace:.2f} (< {RETRACE_MIN})")
        result.setups[S1] = bool(float(tail["close"].iloc[-1]) < h2)

    def levels(self, ctx, result, cfg):
        e = ctx.extras
        return e["level_entry"], e["level_stop"], e["level_target"], (
            f"1-2-3 bottom {e['p1_low']:.2f} / {e['p2_high']:.2f} / {e['p3_low']:.2f}; buy through point 2")
