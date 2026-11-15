"""Wyckoff spring -- a brief break under a trading range's support that is bought back
(Richard Wyckoff's method as set out by Hank Pruden, The Three Skills of Top Trading, 2007).

In Wyckoff's accumulation, the last shakeout before markup is the spring: price dips under the range's
support, finds no supply, and closes back inside. On daily bars:

  * the range: the RANGE_BARS sessions ending SPRING_BARS sessions before today, no taller than
    RANGE_MAX_PCT % (low to high); support its lowest low, resistance its highest high;
  * the spring: a session among the last SPRING_BARS (today included) with a low under support by at most
    MAX_PENETRATION_PCT %, and today closes back above support;
  * a buy-stop at today's high; the stop the spring's low; the target resistance.
"""

from ..core.context import StockContext
from ..marketdata import corporate_actions
from .base import StrategyResult
from .swing_base import PASS_RULE, SwingSetupStrategy

RANGE_BARS = 60              # the range: this many sessions ending SPRING_BARS sessions before today
SPRING_BARS = 3              # the spring is one of this many sessions, today included
RANGE_MAX_PCT = 25.0         # G1: the range's height, (max high − min low) ÷ min low, at most this %
MAX_PENETRATION_PCT = 5.0    # S1: the spring's low at most this % under support
SPRING_VOL_MAX = 1.5         # W1: flagged when the spring's volume exceeds this × its 50-day average
MIN_STOP_PCT = 1.0           # a stop closer than this % below the entry is not bought
MAX_STOP_PCT = 12.0          # nor one further than this %
NOMINAL_TARGET_R = 2         # the target when resistance is not above the entry
HOLD_BARS = 30               # backtest_args: sold at the close of this session after the entry

S1 = "S1"
W1 = "W1"


class WyckoffSpringStrategy(SwingSetupStrategy):
    key = "wyckoff_spring"
    name = "Wyckoff spring"
    description = ("Wyckoff's spring: a brief dip under a trading range's support that closes back inside, "
                   "bought through the day's high with the target at the top of the range.")
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "v1: the spring on daily bars -- a {RANGE_BARS}-session range no taller than {RANGE_MAX_PCT}%, a low "
         "under its support by at most {MAX_PENETRATION_PCT}% within {SPRING_BARS} sessions, a close back above; "
         "a buy-stop at today's high, stop at the spring low, target the range top, {HOLD_BARS}-session limit."),
    )
    behaviour = "mean_reversion"
    style = "reversal"
    gate_codes = ("G1",)
    screen_key = "above_200"
    screen_gates: dict = {}
    watch_codes = (W1,)
    setup_codes = (S1,)
    setup_names = {S1: "Spring under range support"}
    gate_titles = {"G1": "A trading range"}
    order = ""
    expiry_bdays = 2
    plan_code = "WS"
    extra_columns = ("support", "resistance", "range_pct", "spring_low", "penetration_pct", "spring_vol_vs_avg",
                     "level_entry", "level_stop", "level_target")
    extra_numeric_columns = extra_columns

    thesis = (
        "In a trading range after a decline, large buyers accumulate quietly. Before the markup they, or the "
        "market, test supply by pushing price under support; when few sellers appear and price closes back "
        "inside, the range's supply is exhausted and the path of least resistance is up, towards the top of the "
        "range. Richard Wyckoff's method as set out by Hank Pruden, *The Three Skills of Top Trading* (2007). The "
        "catalogue grades it D (a practitioner method, no published test), credibility 1."
    )
    how_it_works = (
        "**Universe.** Every liquid stock. A spring forms in a range, usually after a decline, so the Above the "
        "200-day screen supplies the universe only, with no gate taken from it.",
        "**The range (G1).** The {RANGE_BARS} sessions ending {SPRING_BARS} sessions before today. Its height, "
        "(highest high − lowest low) ÷ lowest low, is at most {RANGE_MAX_PCT}%: a range, not a trend. Support is "
        "its lowest low, resistance its highest high.",
        "**The spring (S1).** Among the last {SPRING_BARS} sessions, today included, the one with the lowest low "
        "is under support by at most {MAX_PENETRATION_PCT}%, and today closes back above support.",
        "**Volume (W1, a flag only).** Wyckoff prefers a quiet spring; W1 notes a spring session whose volume is "
        "above {SPRING_VOL_MAX} × its 50-day average. It never blocks the trade.",
        "**The order.** A buy-stop at today's high for {expiry_bdays} sessions.",
        "**Stop and exit.** The stop is the spring's low. The target is resistance (entry + {NOMINAL_TARGET_R} R "
        "if that is not above the entry); the position is sold at the close of session {HOLD_BARS} after the "
        "entry if neither was hit.",
    )
    caveats = (
        "**No phase analysis.** Wyckoff and Pruden read the whole accumulation -- selling climax, automatic rally, "
        "secondary tests -- before calling a spring; here the range is a fixed window and its height cap stands in "
        "for that reading.",
        "**The target is a stand-in.** Pruden projects targets from a point-and-figure count; the range top is the "
        "first objective, used here as the only one.",
        "**Survivorship.** The universe is today's stock lists; breakdowns that kept going into a delisting are "
        "missing, which flatters a buy-the-failed-break rule.",
        "**Run it with its flags** (`backtest_args`).",
        corporate_actions.CAVEAT_TRADED,
    )
    status = ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (reversal group, grade D, "
              "credibility 1); optimise-stage runs queued in both markets. " + PASS_RULE)
    gate_docs = {
        "G1": ("A trading range.\n\n- **Test:** over the {RANGE_BARS} sessions ending {SPRING_BARS} sessions "
               "before today, (highest high − lowest low) ÷ lowest low is at most {RANGE_MAX_PCT}%.\n- **Fails:** "
               "the range is taller (a trend), or too little history."),
    }
    watch_docs = {
        W1: ("A loud spring.\n\n- **Test:** the spring session's volume is above {SPRING_VOL_MAX} × its 50-day "
             "average volume.\n- **Effect:** noted only; Wyckoff prefers a spring on light volume."),
    }
    setup_docs = {
        S1: ("Spring under range support.\n\n- **Test:** the lowest low of the last {SPRING_BARS} sessions (today "
             "included) is under support by at most {MAX_PENETRATION_PCT}%, and today's close is above support.\n"
             "- **Signal:** a buy-stop at today's high for {expiry_bdays} sessions; the stop is the spring's low."),
    }
    entry_rules = (
        "Signal. G1 and S1 on today's close, with a stop between {MIN_STOP_PCT}% and {MAX_STOP_PCT}% below the "
        "entry, graded TRADE - HIGH CONFIDENCE.",
        "Order. A buy-stop at today's high for {expiry_bdays} sessions (backtest: fills when a session's high "
        "reaches it, at the open if it gaps above; cancelled if the stop is hit first).",
        "One position per stock.",
    )
    stop_rules = ("Where it goes. The spring's low, rounded down to the tick. It defines 1R; it does not move.",)
    target_rules = ("Resistance, the range's highest high; entry + {NOMINAL_TARGET_R} R when that is not above the "
                    "entry.",)
    exit_rules = (
        "Each session after the entry (backtest, the default bracket with `--time-stop-bars {HOLD_BARS}`):",
        "1. The stop, at its price or at the open if the stock gaps under it.",
        "2. The target, at its price or at the open if the stock gaps over it.",
        "3. The time limit: sold at the close of session {HOLD_BARS} after the entry.",
    )
    param_docs = (
        ("Range length", "RANGE_BARS", "G1: sessions in the range."),
        ("Spring window", "SPRING_BARS", "S1: the spring is one of this many sessions, today included; the range "
                                         "ends just before them."),
        ("Range height", "RANGE_MAX_PCT", "G1: the range's height, at most this %."),
        ("Penetration", "MAX_PENETRATION_PCT", "S1: the spring's low at most this % under support."),
        ("Loud spring", "SPRING_VOL_MAX", "W1: spring volume above this × its 50-day average is flagged."),
        ("Minimum stop", "MIN_STOP_PCT", "A stop closer than this % below the entry is not bought."),
        ("Maximum stop", "MAX_STOP_PCT", "A stop further than this % below the entry is not bought."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × R when resistance is not above the entry."),
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
        n = RANGE_BARS + SPRING_BARS
        if len(d) < n:
            result.fail("G1", "insufficient history")
            return
        tail = d.iloc[-n:]
        lows = tail["low"].to_numpy(float)
        highs = tail["high"].to_numpy(float)
        support, resistance = float(lows[:RANGE_BARS].min()), float(highs[:RANGE_BARS].max())
        height = (resistance / support - 1) * 100 if support > 0 else float("inf")
        k = RANGE_BARS + int(lows[RANGE_BARS:].argmin())
        spring_low = float(lows[k])
        pen = (1 - spring_low / support) * 100 if support > 0 else float("nan")
        vol, vavg = float(tail["volume"].iloc[k]), float(tail["vol_sma50"].iloc[k])
        vratio = vol / vavg if vavg and vavg == vavg else float("nan")
        close = float(tail["close"].iloc[-1])
        e.update(support=support, resistance=resistance, range_pct=height, spring_low=spring_low,
                 penetration_pct=pen, spring_vol_vs_avg=vratio, level_entry=float(highs[-1]),
                 level_stop=spring_low, level_target=resistance)
        if height <= RANGE_MAX_PCT:
            result.ok("G1", f"range {support:.2f}-{resistance:.2f} ({height:.1f}%)")
        else:
            result.fail("G1", f"range {height:.1f}% tall (> {RANGE_MAX_PCT}%)")
        spring = spring_low < support and pen <= MAX_PENETRATION_PCT and close > support
        result.setups[S1] = bool(spring)
        if spring and vratio > SPRING_VOL_MAX:
            result.watch_flags[W1] = True
            result.watch_notes[W1] = f"spring volume {vratio:.1f}× its 50-day average"

    def levels(self, ctx, result, cfg):
        e = ctx.extras
        return e["level_entry"], e["level_stop"], e["level_target"], (
            f"spring to {e['spring_low']:.2f} under support {e['support']:.2f}; target the range top "
            f"{e['resistance']:.2f}")
