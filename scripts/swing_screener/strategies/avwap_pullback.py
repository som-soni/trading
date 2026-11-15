"""Anchored-VWAP pullback -- Brian Shannon's first test of an anchored VWAP from above
(Maximum Trading Gains with Anchored VWAP, 2023).

The volume-weighted average price from a meaningful low is the average cost of everyone who bought since
then. In an uptrend, a pullback to it is a test of whether those buyers defend their cost. On daily bars:

  * the close is above the 200-day (the screen's A1) and the 50-day is above the 200-day;
  * the anchor is the session of the lowest low of the ANCHOR_BARS sessions before today, at least
    MIN_ANCHOR_AGE sessions old;
  * AVWAP from the anchor through today = cumsum(typical price × volume) / cumsum(volume);
  * today's low comes within TOUCH_PCT % of the AVWAP (or below it), today closes above it, and each of the
    PRIOR_ABOVE sessions before today closed above its own AVWAP value: a first test from above;
  * a buy-stop at today's high; the stop the lower of today's low and STOP_BELOW_PCT % under the AVWAP;
    a trailing stop of TRAIL_ATR ATRs, no target.
"""

import numpy as np

from ..core.context import StockContext
from ..marketdata import corporate_actions
from .base import StrategyResult
from .swing_base import PASS_RULE, SwingSetupStrategy

ANCHOR_BARS = 126        # the anchor: the lowest low of this many sessions before today
MIN_ANCHOR_AGE = 20      # G3: the anchor is at least this many sessions before today
TOUCH_PCT = 1.0          # S1: today's low at most this % above the AVWAP (or below it)
PRIOR_ABOVE = 10         # S1: each of this many sessions before today closed above its AVWAP
STOP_BELOW_PCT = 2.0     # stop: at most today's low, and at most this % under the AVWAP
MIN_STOP_PCT = 1.0       # a stop closer than this % below the entry is not bought
MAX_STOP_PCT = 12.0      # nor one further than this %
NOMINAL_TARGET_R = 2     # the plan's target, for the R column only (the backtest runs --no-target)
TRAIL_ATR = 3            # backtest_args: the stop trails this many ATR14 under the highest close

S1 = "S1"


class AvwapPullbackStrategy(SwingSetupStrategy):
    key = "avwap_pullback"
    name = "Anchored-VWAP pullback"
    description = ("Shannon's anchored VWAP: in an uptrend, the first pullback to the volume-weighted average "
                   "price from the six-month low is bought through the test day's high.")
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "v1: an anchored-VWAP first test on daily bars -- the anchor the lowest low of {ANCHOR_BARS} sessions "
         "(at least {MIN_ANCHOR_AGE} old), a low within {TOUCH_PCT}% of the AVWAP after {PRIOR_ABOVE} closes "
         "above it, a buy-stop at the test day's high, a {TRAIL_ATR}-ATR trailing stop and no target."),
    )
    behaviour = "trend_momentum"
    style = "pullback"
    gate_codes = ("G1", "G2", "G3")
    screen_key = "above_200"
    screen_gates = {"G1": "A1"}
    setup_codes = (S1,)
    setup_names = {S1: "First test of the anchored VWAP"}
    gate_titles = {"G1": "Above the 200-day", "G2": "50-day above the 200-day",
                   "G3": "Anchor {MIN_ANCHOR_AGE}+ sessions old"}
    order = ""
    expiry_bdays = 2
    plan_code = "AV"
    extra_columns = ("avwap", "anchor_low", "anchor_age", "low_vs_avwap_pct", "level_entry", "level_stop")
    extra_numeric_columns = extra_columns

    thesis = (
        "The volume-weighted average price from a meaningful low is the average cost of everyone who has bought "
        "since. While price holds above it those buyers are in profit; a pullback to it tests whether they defend "
        "their cost, and in an uptrend the first such test is the one most often defended. Brian Shannon, "
        "*Maximum Trading Gains with Anchored VWAP* (2023). The catalogue grades it D (practitioner method, no "
        "published test), credibility 1."
    )
    how_it_works = (
        "**The trend (G1, G2).** The close is above the 200-day average (G1, the Above the 200-day screen's rule) "
        "and the 50-day average is above the 200-day (G2).",
        "**The anchor (G3).** The session of the lowest low of the {ANCHOR_BARS} sessions before today; it must be "
        "at least {MIN_ANCHOR_AGE} sessions before today (G3), so the AVWAP has history behind it.",
        "**The AVWAP.** From the anchor session through today: the running sum of typical price × volume over the "
        "running sum of volume, typical price = (high + low + close) ÷ 3.",
        "**The first test (S1).** Today's low is no more than {TOUCH_PCT}% above today's AVWAP (or below it), "
        "today closes above the AVWAP, and each of the {PRIOR_ABOVE} sessions before today closed above its own "
        "AVWAP value (the same anchor): the first test from above.",
        "**The order.** A buy-stop at today's high for {expiry_bdays} sessions.",
        "**Stop and exit.** The stop is the lower of today's low and {STOP_BELOW_PCT}% under today's AVWAP. No "
        "target: the stop trails {TRAIL_ATR} ATR14 under the highest close.",
    )
    caveats = (
        "**A mechanical anchor.** Shannon chooses anchors by judgment -- an earnings gap, a major pivot, the start "
        "of a move; the lowest low of six months is a mechanical stand-in and may not be the level traders watch.",
        "**Daily bars.** Shannon reads the test intraday and on several anchors at once; one daily anchor is used.",
        "**The exit is a stand-in.** Shannon manages discretionarily; the {TRAIL_ATR}-ATR trail is this "
        "backtest's.",
        "**Survivorship.** The universe is today's stock lists; uptrends that ended in a delisting are missing.",
        "**Run it with its exit flags** (`backtest_args`); the default bracket would sell at the nominal target.",
        corporate_actions.CAVEAT_TRADED,
    )
    status = ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (pullback group, grade D, "
              "credibility 1); optimise-stage runs queued in both markets. " + PASS_RULE)
    gate_docs = {
        "G1": ("Above the 200-day.\n\n- **Test:** the Above the 200-day screen's rule: today's close is above the "
               "200-day average.\n- **Fails:** at or below it."),
        "G2": ("The 50-day is above the 200-day.\n\n- **Test:** today's 50-day average is above today's 200-day.\n"
               "- **Fails:** at or below it, or undefined."),
        "G3": ("The anchor has history.\n\n- **Test:** the lowest low of the {ANCHOR_BARS} sessions before today "
               "was made at least {MIN_ANCHOR_AGE} sessions before today.\n- **Fails:** it is more recent, or too "
               "little history."),
    }
    watch_docs: dict = {}
    setup_docs = {
        S1: ("The first test of the anchored VWAP.\n\n- **Test:** today's low ≤ AVWAP × (1 + {TOUCH_PCT}%), "
             "today's close > AVWAP, and each of the {PRIOR_ABOVE} sessions before today closed above its own "
             "AVWAP value.\n- **Signal:** a buy-stop at today's high for {expiry_bdays} sessions."),
    }
    entry_rules = (
        "Signal. G1, G2, G3 and S1 on today's close, with a stop between {MIN_STOP_PCT}% and {MAX_STOP_PCT}% below "
        "the entry, graded TRADE - HIGH CONFIDENCE.",
        "Order. A buy-stop at today's high for {expiry_bdays} sessions (backtest: fills when a session's high "
        "reaches it, at the open if it gaps above; cancelled if the stop is hit first).",
        "One position per stock.",
    )
    stop_rules = (
        "Where it goes. The lower of today's low and AVWAP × (1 − {STOP_BELOW_PCT}%), rounded down to the tick. "
        "It defines 1R.",
        "It trails: from the session after the entry it rises to {TRAIL_ATR} ATR14 under the highest close since "
        "the entry, never down.",
    )
    target_rules = ("No target. The plan's target is entry + {NOMINAL_TARGET_R} R for the R column only; the "
                    "backtest runs with `--no-target`.",)
    exit_rules = (
        "Each session after the entry (backtest, `--exit-mode trail_atr --atr-mult {TRAIL_ATR} --no-target`):",
        "1. The stop, at its price or at the open if the stock gaps under it. Nothing else.",
    )
    param_docs = (
        ("Anchor window", "ANCHOR_BARS", "The anchor is the lowest low of this many sessions before today."),
        ("Anchor age", "MIN_ANCHOR_AGE", "G3: sessions, at least, between the anchor and today."),
        ("Touch", "TOUCH_PCT", "S1: today's low at most this % above the AVWAP."),
        ("Closes above", "PRIOR_ABOVE", "S1: sessions before today that each closed above their AVWAP."),
        ("Stop under AVWAP", "STOP_BELOW_PCT", "The stop is at most this % under today's AVWAP."),
        ("Minimum stop", "MIN_STOP_PCT", "A stop closer than this % below the entry is not bought."),
        ("Maximum stop", "MAX_STOP_PCT", "A stop further than this % below the entry is not bought."),
        ("Trail", "TRAIL_ATR", "ATR14 multiples the stop trails under the highest close (--atr-mult)."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × R, for the R column only."),
        ("Order expiry", "expiry_bdays", "Sessions the buy-stop rests."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume", "The 20-day average of close × volume, at least."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
    )
    backtest_args = (f"--exit-mode trail_atr --atr-mult {TRAIL_ATR} --no-target "
                     "--rank-by setup_momentum --min-fill 0.5")

    def detect(self, ctx: StockContext, result: StrategyResult) -> None:
        d, e = ctx.daily, ctx.extras
        last = d.iloc[-1]
        s50, s200 = float(last["sma50"]), float(last["sma200"])
        if s50 > s200:
            result.ok("G2", f"50-day {s50:.2f} above 200-day {s200:.2f}")
        else:
            result.fail("G2", "50-day not above the 200-day")
        if len(d) < ANCHOR_BARS + 1:
            result.fail("G3", "insufficient history")
            return
        tail = d.iloc[-ANCHOR_BARS - 1:]
        lows = tail["low"].to_numpy(float)
        k = int(lows[:-1].argmin())
        age = ANCHOR_BARS - k                      # sessions before today
        highs = tail["high"].to_numpy(float)[k:]
        closes = tail["close"].to_numpy(float)[k:]
        vols = tail["volume"].to_numpy(float)[k:]
        typ = (highs + lows[k:] + closes) / 3
        cv = np.cumsum(vols)
        with np.errstate(invalid="ignore", divide="ignore"):
            avwap = np.cumsum(typ * vols) / cv
        av, today_low, close, today_high = float(avwap[-1]), float(lows[-1]), float(closes[-1]), float(highs[-1])
        stop = min(today_low, av * (1 - STOP_BELOW_PCT / 100))
        e.update(avwap=av, anchor_low=float(lows[k]), anchor_age=age,
                 low_vs_avwap_pct=(today_low / av - 1) * 100 if av == av and av > 0 else float("nan"),
                 level_entry=today_high, level_stop=stop)
        if age >= MIN_ANCHOR_AGE:
            result.ok("G3", f"anchor {lows[k]:.2f}, {age} sessions old")
        else:
            result.fail("G3", f"anchor only {age} sessions old (< {MIN_ANCHOR_AGE})")
        if not (av == av) or len(avwap) < PRIOR_ABOVE + 1:
            result.setups[S1] = False
            return
        prior_above = bool((closes[-PRIOR_ABOVE - 1:-1] > avwap[-PRIOR_ABOVE - 1:-1]).all())
        result.setups[S1] = bool(today_low <= av * (1 + TOUCH_PCT / 100) and close > av and prior_above)

    def levels(self, ctx, result, cfg):
        e = ctx.extras
        return e["level_entry"], e["level_stop"], None, (
            f"first test of the AVWAP {e['avwap']:.2f} from the {e['anchor_low']:.2f} low; buy through today's high")
