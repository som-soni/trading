"""Turtle Soup Plus One -- Raschke & Connors's fade of a failed 20-day breakdown (Street Smarts, 1995).

The Turtles sold a new 20-day low. Raschke and Connors's observation was that most such breaks fail, and
that a failed break is a better trade than the break itself. Turtle Soup buys back through the old low
the same session; daily bars cannot see that order of events, so this is the book's "Plus One" version,
which is daily-bar native:

  * day 1 makes a new 20-day low, below the lowest low of the LOOKBACK sessions before it;
  * the previous 20-day low was made at least MIN_PRIOR_AGE sessions before day 1;
  * day 1 closes at or below that previous low;
  * day 2: a buy-stop at the previous 20-day low, that session only; the stop is day 1's low.

The book trails and takes partial profits within a few days. Here: no target, a trailing stop TRAIL_ATR
ATRs under the highest close, and a time limit of HOLD_BARS sessions (`backtest_args`).
"""

from ..core.context import StockContext
from ..marketdata import corporate_actions
from .base import StrategyResult
from .swing_base import PASS_RULE, SwingSetupStrategy

LOOKBACK = 20            # G1: day 1's low is below the lowest low of this many sessions before it
MIN_PRIOR_AGE = 4        # G2: that earlier low was made at least this many sessions before day 1
MIN_STOP_PCT = 1.0       # a stop closer than this % below the entry is not bought
MAX_STOP_PCT = 12.0      # nor one further than this %
NOMINAL_TARGET_R = 2     # the plan's target, for the R column only (the backtest runs --no-target)
TRAIL_ATR = 2            # backtest_args: the stop trails this many ATR14 under the highest close
HOLD_BARS = 6            # backtest_args: sold at the close of this session after the entry

S1 = "S1"


class TurtleSoupStrategy(SwingSetupStrategy):
    key = "turtle_soup"
    name = "Turtle Soup Plus One"
    description = ("Raschke & Connors's fade of a failed breakdown: a new 20-day low that closes under the "
                   "previous one is bought back the next session through that old low.")
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "v1: Turtle Soup Plus One as Street Smarts states it on daily bars -- a new {LOOKBACK}-day low, the "
         "previous one at least {MIN_PRIOR_AGE} sessions older, a close at or under it, then a next-session "
         "buy-stop at the old low with the stop at day 1's low. Trailing exit, {HOLD_BARS}-session limit."),
    )
    behaviour = "mean_reversion"
    style = "fade"
    gate_codes = ("G1", "G2")
    screen_key = "above_200"
    screen_gates: dict = {}
    setup_codes = (S1,)
    setup_names = {S1: "Turtle Soup Plus One"}
    gate_titles = {"G1": "New {LOOKBACK}-day low", "G2": "Previous low {MIN_PRIOR_AGE}+ sessions old"}
    order = ""
    expiry_bdays = 1
    plan_code = "TS"
    extra_columns = ("prior_low", "prior_low_age", "close_vs_prior_pct", "level_entry", "level_stop")
    extra_numeric_columns = extra_columns

    thesis = (
        "A breakdown to a new 20-day low draws in breakout sellers and trips the stops of longs; when there is no "
        "real supply behind it, price comes straight back through the old low and those sellers must cover. "
        "Raschke & Connors, *Street Smarts* (1995), built Turtle Soup to profit from exactly the failures that "
        "make channel breakouts lose. The catalogue grades it D (no published test beyond the book's examples), "
        "credibility 2. It is here as a diversifier to the breakout family: it should pay when breakouts fail."
    )
    how_it_works = (
        "**Universe.** Every liquid stock. The book trades it with no trend filter, so none is added; the Above "
        "the 200-day screen supplies the universe only, with no gate taken from it.",
        "**Day 1 (G1, G2).** Today's low is below the lowest low of the {LOOKBACK} sessions before it (G1), and "
        "that earlier low was made at least {MIN_PRIOR_AGE} sessions before today (G2): a fresh break of an "
        "established low, not a slide that keeps making new lows every day.",
        "**The Plus One condition (S1).** Today closes at or below the earlier {LOOKBACK}-day low: the break held "
        "into the close.",
        "**Day 2 (the order).** A buy-stop at the earlier {LOOKBACK}-day low, for the next session only. It fills "
        "only if price comes back through the old low; a gap above it fills at the open.",
        "**Stop and exit.** The stop is day 1's low. No target: the stop trails {TRAIL_ATR} ATR14 under the "
        "highest close, and the position is sold at the close of session {HOLD_BARS} after the entry.",
    )
    caveats = (
        "**Plus One, not the same-day trade.** The original buys back through the old low on the day of the break; "
        "daily bars cannot tell whether the session's low came before its high, so the book's own next-day "
        "variant is tested instead.",
        "**The book's exits are discretionary.** Raschke trails and takes partial profits within two to six "
        "sessions; the trailing stop and the {HOLD_BARS}-session limit are this backtest's stand-ins.",
        "**The stop is day 1's low.** The book puts it under the lower of the two days' lows; the order is placed "
        "before day 2's low exists, so day 1's is used.",
        "**Survivorship.** The universe is today's stock lists; stocks that broke down and kept going into a "
        "delisting are missing, which flatters a buy-the-failed-break strategy more than most.",
        "**Run it with its exit flags** (`backtest_args`); the default bracket would sell at the nominal target.",
        corporate_actions.CAVEAT_TRADED,
    )
    status = ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (fade group, grade D, credibility "
              "2); optimise-stage runs queued in both markets. " + PASS_RULE)
    gate_docs = {
        "G1": ("A new {LOOKBACK}-day low.\n\n- **Test:** today's low is below the lowest low of the {LOOKBACK} "
               "sessions before today.\n- **Fails:** no new low, or too little history."),
        "G2": ("The earlier low is established.\n\n- **Test:** the lowest low of those {LOOKBACK} sessions was made "
               "at least {MIN_PRIOR_AGE} sessions before today.\n- **Fails:** it is more recent, so the stock is "
               "sliding rather than breaking a low."),
    }
    watch_docs: dict = {}
    setup_docs = {
        S1: ("Turtle Soup Plus One.\n\n- **Test:** today closes at or below the earlier {LOOKBACK}-day low.\n"
             "- **Signal:** a buy-stop at that earlier low for the next session; the stop is today's low."),
    }
    entry_rules = (
        "Signal. G1, G2 and S1 on today's close, with a stop between {MIN_STOP_PCT}% and {MAX_STOP_PCT}% below the "
        "entry, graded TRADE - HIGH CONFIDENCE.",
        "Order. A buy-stop at the earlier {LOOKBACK}-day low for the next session only (backtest: fills when that "
        "session's high reaches it, at the open if it gaps above).",
        "One position per stock.",
    )
    stop_rules = (
        "Where it goes. Today's (day 1's) low, rounded down to the tick. It defines 1R.",
        "It trails: from the session after the entry it rises to {TRAIL_ATR} ATR14 under the highest close since "
        "the entry, never down.",
    )
    target_rules = ("No target. The plan's target is entry + {NOMINAL_TARGET_R} R for the R column only; the "
                    "backtest runs with `--no-target`.",)
    exit_rules = (
        "Each session after the entry (backtest, `--exit-mode trail_atr --atr-mult {TRAIL_ATR} --no-target "
        "--time-stop-bars {HOLD_BARS}`):",
        "1. The stop, at its price or at the open if the stock gaps under it.",
        "2. The time limit: sold at the close of session {HOLD_BARS} after the entry.",
    )
    param_docs = (
        ("Channel", "LOOKBACK", "G1: sessions whose lowest low today must undercut."),
        ("Age of the earlier low", "MIN_PRIOR_AGE", "G2: sessions, at least, since that low was made."),
        ("Minimum stop", "MIN_STOP_PCT", "A stop closer than this % below the entry is not bought."),
        ("Maximum stop", "MAX_STOP_PCT", "A stop further than this % below the entry is not bought."),
        ("Trail", "TRAIL_ATR", "ATR14 multiples the stop trails under the highest close (--atr-mult)."),
        ("Hold", "HOLD_BARS", "Sessions after the entry before the position is sold (--time-stop-bars)."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × R, for the R column only."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume", "The 20-day average of close × volume, at least."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
    )
    backtest_args = (f"--exit-mode trail_atr --atr-mult {TRAIL_ATR} --no-target --time-stop-bars {HOLD_BARS} "
                     "--rank-by setup_momentum --min-fill 0.5")

    def detect(self, ctx: StockContext, result: StrategyResult) -> None:
        d, e = ctx.daily, ctx.extras
        if len(d) < LOOKBACK + 2:
            result.fail("G1", "insufficient history")
            return
        lows = d["low"].astype(float).to_numpy()
        prior = lows[-LOOKBACK - 1:-1]
        k = int(prior.argmin())
        prior_low, age = float(prior[k]), LOOKBACK - k      # sessions before today
        today_low, close = float(lows[-1]), float(d["close"].iloc[-1])
        e.update(prior_low=prior_low, prior_low_age=age, close_vs_prior_pct=(close / prior_low - 1) * 100,
                 level_entry=prior_low, level_stop=today_low)
        if today_low < prior_low:
            result.ok("G1", f"low {today_low:.2f} under the {LOOKBACK}-day low {prior_low:.2f}")
        else:
            result.fail("G1", "no new low")
        if age >= MIN_PRIOR_AGE:
            result.ok("G2", f"earlier low {age} sessions old")
        else:
            result.fail("G2", f"earlier low only {age} sessions old (< {MIN_PRIOR_AGE})")
        result.setups[S1] = bool(close <= prior_low)

    def levels(self, ctx, result, cfg):
        e = ctx.extras
        return e["prior_low"], e["level_stop"], None, (
            f"failed break of the {LOOKBACK}-day low {e['prior_low']:.2f}; buy back through it")

