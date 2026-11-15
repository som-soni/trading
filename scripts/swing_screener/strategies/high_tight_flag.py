"""High tight flag -- O'Neil's and Bulkowski's best-performing chart pattern (O'Neil, How to Make Money in
Stocks; Bulkowski, Encyclopedia of Chart Patterns, 2005).

A stock that rises 90% or more in about two months, then drifts sideways for three to five weeks without
giving back more than about a quarter, is bought on the break of the flag's high. The shape is the power
play's (strategies/power_play.py, whose detector `flag_after_advance` this module reuses) at Bulkowski's
thresholds, with O'Neil's money management:

  * G1 the advance: the peak at least ADVANCE_MIN_PCT % above the lowest low of the ADVANCE_BARS sessions
    before it;
  * G2 the flag: FLAG_MIN_BARS or more sessions since the peak (the peak being the highest high of the
    FLAG_MAX_BARS sessions before today), its lowest low at most MAX_DEPTH_PCT % under the peak;
  * S1: today still closes at or under the peak;
  * a buy-stop at the peak for `expiry_bdays` sessions; the stop is the flag low or LOSS_CUT_PCT % under the
    entry, whichever is higher; the target PROFIT_TAKE_PCT % above the entry (the default bracket).
"""

from ..marketdata import corporate_actions
from .power_play import FlagAfterAdvance
from .swing_base import PASS_RULE
from .trend_pullback import round_tick

ADVANCE_BARS = 40        # G1: the advance is measured from the lowest low of this many sessions before the peak …
ADVANCE_MIN_PCT = 90     # … and must be at least this % (Bulkowski's)
FLAG_MIN_BARS = 15       # G2: at least this many sessions after the peak, today included (three weeks) …
FLAG_MAX_BARS = 25       # … the peak being the highest high of this many sessions before today (five weeks)
MAX_DEPTH_PCT = 25       # G2: the flag's lowest low at most this % under the peak
LOSS_CUT_PCT = 8         # O'Neil's loss cut: the stop is never more than this % under the entry
PROFIT_TAKE_PCT = 20     # O'Neil's profit take: the target is this % above the entry
MIN_STOP_PCT = 2.0       # a stop closer than this % below the entry is not bought
MAX_STOP_PCT = 8.0       # nor one further than this %
NOMINAL_TARGET_R = 2.5   # the plan's target when none is named (unused: the target is PROFIT_TAKE_PCT)

S1 = "S1"


class HighTightFlagStrategy(FlagAfterAdvance):
    key = "high_tight_flag"
    name = "High tight flag"
    description = ("O'Neil's and Bulkowski's high tight flag: a 90%+ run in about eight weeks, a 3-5 week flag no "
                   "more than 25% deep, bought on the break of the flag's high with an 8% stop and a 20% target.")
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "v1: the high tight flag at Bulkowski's thresholds -- an advance of {ADVANCE_MIN_PCT}%+ off the low of "
         "the {ADVANCE_BARS} sessions before the peak, a flag of {FLAG_MIN_BARS} to {FLAG_MAX_BARS} sessions no "
         "more than {MAX_DEPTH_PCT}% deep, a buy-stop at the peak for {expiry_bdays} sessions; O'Neil's "
         "{LOSS_CUT_PCT}% loss cut and {PROFIT_TAKE_PCT}% profit take."),
    )
    behaviour = "trend_momentum"
    style = "breakout"
    gate_codes = ("G1", "G2")
    screen_key = "above_200"
    screen_gates: dict = {}
    setup_codes = (S1,)
    setup_names = {S1: "High tight flag"}
    gate_titles = {"G1": "Advance {ADVANCE_MIN_PCT}%+", "G2": "Tight flag"}
    order = ""
    expiry_bdays = 5
    plan_code = "HTF"
    extra_columns = ("advance_pct", "flag_bars", "depth_pct", "peak", "flag_low", "level_entry", "level_stop",
                     "level_target")
    extra_numeric_columns = extra_columns

    thesis = (
        "A stock that nearly doubles in two months and then holds almost all of the gain through a few weeks of "
        "sideways drift is being accumulated, not distributed; the break of the flag tends to start another leg. "
        "William O'Neil, *How to Make Money in Stocks*, names the high tight flag the rarest and strongest base; "
        "Thomas Bulkowski, *Encyclopedia of Chart Patterns* (2005), measured it as the best-performing of all "
        "the chart patterns he catalogued. The catalogue grades it B (a large published pattern study), "
        "credibility 2."
    )
    how_it_works = (
        "**Universe.** Every liquid stock. Neither source adds a trend filter beyond the advance itself, so none "
        "is added; the Above the 200-day screen supplies the universe only, with no gate taken from it.",
        "**The advance (G1).** The peak is the highest high of the {FLAG_MAX_BARS} sessions before today. It "
        "stands at least {ADVANCE_MIN_PCT}% above the lowest low of the {ADVANCE_BARS} sessions before the peak.",
        "**The flag (G2).** At least {FLAG_MIN_BARS} sessions have passed since the peak, today included, and the "
        "lowest low since the peak is no more than {MAX_DEPTH_PCT}% under it.",
        "**Still under the pivot (S1).** Today closes at or under the peak: the breakout has not happened yet.",
        "**The order.** A buy-stop at the peak for the next {expiry_bdays} sessions. It fills when a session "
        "trades through it, at the open if one gaps above; an order whose stop is hit first is cancelled.",
        "**Stop and target (O'Neil's money management).** The stop is the flag's lowest low or {LOSS_CUT_PCT}% "
        "under the entry, whichever is higher. The target is {PROFIT_TAKE_PCT}% above the entry. Whichever is "
        "reached first ends the trade.",
    )
    caveats = (
        "**Bulkowski's numbers are measured from the breakout to the ultimate high**, with hindsight; a fixed "
        "{PROFIT_TAKE_PCT}% target and a {LOSS_CUT_PCT}% stop capture a different, tradable quantity.",
        "**O'Neil would hold a winner longer.** He sells most winners at 20-25% but holds a stock that runs that "
        "far within three weeks of its breakout; that exception is not modelled.",
        "**The flag's tightness is depth only.** The sources also look for volume drying up in the flag and "
        "expanding on the break; neither is checked.",
        "**Rare.** A 90% run in eight weeks is uncommon among liquid stocks, so expect few trades a year, and a "
        "flag low more than {MAX_STOP_PCT}% under the peak leaves the {LOSS_CUT_PCT}% cut as the stop.",
        corporate_actions.CAVEAT_TRADED,
    )
    status = ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (breakout group, grade B, "
              "credibility 2); optimise-stage runs queued in both markets. " + PASS_RULE)
    gate_docs = {
        "G1": ("The advance.\n\n- **Test:** the peak (the highest high of the {FLAG_MAX_BARS} sessions before "
               "today) is at least {ADVANCE_MIN_PCT}% above the lowest low of the {ADVANCE_BARS} sessions before "
               "the peak.\n- **Fails:** a smaller advance, or too little history."),
        "G2": ("The flag.\n\n- **Test:** at least {FLAG_MIN_BARS} sessions since the peak, today included, and "
               "the lowest low since the peak at most {MAX_DEPTH_PCT}% under it.\n- **Fails:** too young a flag, "
               "or too deep a pullback."),
    }
    watch_docs: dict = {}
    setup_docs = {
        S1: ("High tight flag.\n\n- **Test:** today's close is at or under the peak.\n- **Signal:** a buy-stop at "
             "the peak for {expiry_bdays} sessions; stop at the higher of the flag low and {LOSS_CUT_PCT}% under "
             "the entry, target {PROFIT_TAKE_PCT}% above it."),
    }
    entry_rules = (
        "Signal. G1, G2 and S1 on today's close, with a stop between {MIN_STOP_PCT}% and {MAX_STOP_PCT}% below the "
        "entry, graded TRADE - HIGH CONFIDENCE.",
        "Order. A buy-stop at the peak for {expiry_bdays} sessions (backtest: fills when a session's high reaches "
        "it, at the open if it gaps above).",
        "One position per stock.",
    )
    stop_rules = ("Where it goes. The higher of the flag's lowest low (rounded down to the tick) and the entry × "
                  "(1 − {LOSS_CUT_PCT}%) (rounded up to the tick, so it stays within {LOSS_CUT_PCT}%). It defines "
                  "1R and does not move.",)
    target_rules = ("The entry × (1 + {PROFIT_TAKE_PCT}%): sold there (the default bracket).",)
    exit_rules = (
        "Each session after the entry (backtest, the default bracket):",
        "1. The stop, at its price or at the open if the stock gaps under it.",
        "2. The target, at its price or at the open if the stock gaps above it.",
    )
    param_docs = (
        ("Advance window", "ADVANCE_BARS", "G1: sessions before the peak whose lowest low starts the advance."),
        ("Advance", "ADVANCE_MIN_PCT", "G1: the peak's gain over that low, %, at least."),
        ("Flag minimum", "FLAG_MIN_BARS", "G2: sessions since the peak, today included, at least."),
        ("Flag window", "FLAG_MAX_BARS", "Sessions before today among which the peak is the highest high."),
        ("Flag depth", "MAX_DEPTH_PCT", "G2: the flag's lowest low under the peak, %, at most."),
        ("Order life", "expiry_bdays", "Sessions the buy-stop at the peak stays open."),
        ("Loss cut", "LOSS_CUT_PCT", "The stop is never more than this % under the entry."),
        ("Profit take", "PROFIT_TAKE_PCT", "The target, % above the entry."),
        ("Minimum stop", "MIN_STOP_PCT", "A stop closer than this % below the entry is not bought."),
        ("Maximum stop", "MAX_STOP_PCT", "A stop further than this % below the entry is not bought."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × R when none is named (not used here)."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume", "The 20-day average of close × volume, at least."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
    )
    backtest_args = "--rank-by setup_momentum --min-fill 0.5"

    def detect(self, ctx, result):
        super().detect(ctx, result)
        e = ctx.extras
        if "peak" in e:
            entry = e["peak"]
            e["level_stop"] = max(e["flag_low"], entry * (1 - LOSS_CUT_PCT / 100))
            e["level_target"] = entry * (1 + PROFIT_TAKE_PCT / 100)

    def levels(self, ctx, result, cfg):
        e = ctx.extras
        # the loss cut rounds UP to the tick, so the tick rounding cannot push it past MAX_STOP_PCT
        cut = round_tick(e["peak"] * (1 - LOSS_CUT_PCT / 100), cfg.tick_size, "up")
        e["level_stop"] = max(e["flag_low"], cut)
        return e["peak"], e["level_stop"], e["level_target"], (
            f"{e['advance_pct']:.0f}% advance, {e['flag_bars']}-session flag; buy the break of {e['peak']:.2f}")
