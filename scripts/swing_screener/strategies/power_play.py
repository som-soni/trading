"""Power play -- Mark Minervini's explosive-advance-then-tight-flag setup (Trade Like a Stock Market Wizard,
2013).

Minervini's one exception to his trend template: a stock that roughly doubles in about eight weeks, then
rests sideways for a few weeks without giving back much, may be bought on the break of that rest even
before a long-term base exists. Daily-bar version:

  * G1 the advance: the peak stands at least ADVANCE_MIN_PCT % above the lowest low of the ADVANCE_BARS
    sessions before it;
  * G2 the flag: the peak is the highest high of the FLAG_MAX_BARS sessions before today, at least
    FLAG_MIN_BARS sessions have passed since it, and nothing since has traded more than MAX_DEPTH_PCT %
    under it;
  * S1: today still closes at or under the peak;
  * a buy-stop at the peak for EXPIRY sessions; the stop is the flag's lowest low; sold on a close below
    the 21-day EMA (`backtest_args`).

The detector, `flag_after_advance`, is shared with the high tight flag (strategies/high_tight_flag.py),
which is the same shape at Bulkowski's thresholds.
"""

import numpy as np

from ..core.context import StockContext
from ..marketdata import corporate_actions
from .base import StrategyResult
from .swing_base import PASS_RULE, SwingSetupStrategy

ADVANCE_BARS = 40        # G1: the advance is measured from the lowest low of this many sessions before the peak …
ADVANCE_MIN_PCT = 100    # … and must be at least this % (a doubling)
FLAG_MIN_BARS = 10       # G2: at least this many sessions after the peak, today included …
FLAG_MAX_BARS = 30       # … the peak being the highest high of this many sessions before today
MAX_DEPTH_PCT = 20       # G2: the flag's lowest low at most this % under the peak
MIN_STOP_PCT = 2.0       # a stop closer than this % below the entry is not bought
MAX_STOP_PCT = 20.0      # nor one further than this %
NOMINAL_TARGET_R = 3     # the plan's target, for the R column only (the backtest runs --no-target)

S1 = "S1"


def flag_after_advance(high: np.ndarray, low: np.ndarray, close: np.ndarray, advance_bars: int,
                       advance_min_pct: float, flag_min_bars: int, flag_max_bars: int,
                       max_depth_pct: float) -> dict | None:
    """A flag after a sharp advance, read on the last element (today). None with too little history.

    The peak is the highest high of the `flag_max_bars` sessions before today (today excluded; the latest
    such session on a tie). The flag is every session after the peak through today. The advance runs from
    the lowest low of the `advance_bars` sessions ending the session before the peak, up to the peak.
    Returns the measures and three verdicts: `advance_ok`, `flag_ok` (length and depth) and
    `under_pivot` (today's close at or under the peak, so the breakout is still ahead).
    """
    n = len(high)
    if n < flag_max_bars + advance_bars + 1:
        return None
    win = high[n - 1 - flag_max_bars:n - 1]
    k = len(win) - 1 - int(np.argmax(win[::-1]))         # the latest occurrence of the window's maximum
    p = n - 1 - flag_max_bars + k                         # the peak's index
    peak = float(high[p])
    flag_bars = n - 1 - p
    flag_low = float(low[p + 1:].min())
    depth = (peak - flag_low) / peak * 100
    base_low = float(low[p - advance_bars:p].min())
    advance = (peak / base_low - 1) * 100 if base_low > 0 else float("nan")
    return {
        "peak": peak, "flag_bars": flag_bars, "flag_low": flag_low, "depth_pct": depth,
        "advance_low": base_low, "advance_pct": advance,
        "advance_ok": bool(advance >= advance_min_pct),
        "flag_ok": bool(flag_bars >= flag_min_bars and depth <= max_depth_pct),
        "under_pivot": bool(float(close[-1]) <= peak),
    }


class FlagAfterAdvance(SwingSetupStrategy):
    """Shared detect for a flag after an advance; the subclass module supplies the five constants."""

    def detect(self, ctx: StockContext, result: StrategyResult) -> None:
        d, e = ctx.daily, ctx.extras
        k = self._k
        n = k("FLAG_MAX_BARS") + k("ADVANCE_BARS") + 1
        f = flag_after_advance(d["high"].astype(float).to_numpy()[-n:], d["low"].astype(float).to_numpy()[-n:],
                               d["close"].astype(float).to_numpy()[-n:], k("ADVANCE_BARS"), k("ADVANCE_MIN_PCT"),
                               k("FLAG_MIN_BARS"), k("FLAG_MAX_BARS"), k("MAX_DEPTH_PCT"))
        if f is None:
            result.fail("G1", "insufficient history")
            return
        e.update(advance_pct=f["advance_pct"], flag_bars=f["flag_bars"], depth_pct=f["depth_pct"],
                 peak=f["peak"], flag_low=f["flag_low"], level_entry=f["peak"], level_stop=f["flag_low"])
        if f["advance_ok"]:
            result.ok("G1", f"advance {f['advance_pct']:.0f}% into the peak {f['peak']:.2f}")
        else:
            result.fail("G1", f"advance only {f['advance_pct']:.0f}% (< {k('ADVANCE_MIN_PCT')}%)")
        if f["flag_ok"]:
            result.ok("G2", f"flag {f['flag_bars']} sessions, {f['depth_pct']:.1f}% deep")
        else:
            result.fail("G2", f"flag {f['flag_bars']} sessions, {f['depth_pct']:.1f}% deep (needs "
                              f"{k('FLAG_MIN_BARS')}+ sessions, at most {k('MAX_DEPTH_PCT')}%)")
        result.setups[self.setup_codes[0]] = f["under_pivot"]


class PowerPlayStrategy(FlagAfterAdvance):
    key = "power_play"
    name = "Power play"
    description = ("Minervini's power play: a stock that doubled in about eight weeks and then rests in a tight "
                   "flag is bought on the break of the flag's high.")
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "v1: Minervini's power play on daily bars -- an advance of {ADVANCE_MIN_PCT}%+ off the low of the "
         "{ADVANCE_BARS} sessions before the peak, a flag of {FLAG_MIN_BARS} to {FLAG_MAX_BARS} sessions no more "
         "than {MAX_DEPTH_PCT}% deep, a buy-stop at the peak for {expiry_bdays} sessions, stop at the flag low, "
         "sold on a close below the 21-day EMA."),
    )
    behaviour = "trend_momentum"
    style = "burst"
    gate_codes = ("G1", "G2")
    screen_key = "above_200"
    screen_gates: dict = {}
    setup_codes = (S1,)
    setup_names = {S1: "Power play"}
    gate_titles = {"G1": "Advance {ADVANCE_MIN_PCT}%+", "G2": "Tight flag"}
    order = ""
    expiry_bdays = 5
    plan_code = "PP"
    extra_columns = ("advance_pct", "flag_bars", "depth_pct", "peak", "flag_low", "level_entry", "level_stop")
    extra_numeric_columns = extra_columns

    thesis = (
        "A stock that doubles in a couple of months usually has a reason -- a new product, a re-rating -- that "
        "draws institutions in over weeks, not days. When such a stock then rests sideways without giving much "
        "back, the holders are not selling, and the break of the rest tends to start the next leg. Mark "
        "Minervini, *Trade Like a Stock Market Wizard* (2013), calls it the power play, the one setup he buys "
        "without his trend template. The catalogue grades it D (the book's examples; no published test), "
        "credibility 1."
    )
    how_it_works = (
        "**Universe.** Every liquid stock. Minervini buys a power play without his trend template, so no trend "
        "gate is added; the Above the 200-day screen supplies the universe only, with no gate taken from it.",
        "**The advance (G1).** The peak is the highest high of the {FLAG_MAX_BARS} sessions before today. It "
        "stands at least {ADVANCE_MIN_PCT}% above the lowest low of the {ADVANCE_BARS} sessions before the peak.",
        "**The flag (G2).** At least {FLAG_MIN_BARS} sessions have passed since the peak, today included, and the "
        "lowest low since the peak is no more than {MAX_DEPTH_PCT}% under it.",
        "**Still under the pivot (S1).** Today closes at or under the peak: the breakout has not happened yet.",
        "**The order.** A buy-stop at the peak for the next {expiry_bdays} sessions. It fills when a session "
        "trades through it, at the open if one gaps above; an order whose stop is hit first is cancelled.",
        "**Stop and exit.** The stop is the flag's lowest low. No target: the position is sold on a close below "
        "the 21-day exponential average, or at the stop.",
    )
    caveats = (
        "**Thresholds are a reading of the book.** Minervini describes the power play loosely (about a doubling in "
        "eight weeks, a 3-6 week rest, a 20-25% correction at most); {ADVANCE_BARS} sessions, {ADVANCE_MIN_PCT}%, "
        "{FLAG_MIN_BARS}-{FLAG_MAX_BARS} sessions and {MAX_DEPTH_PCT}% are this version's fixed numbers.",
        "**The exit is a stand-in.** Minervini sells into strength and moves the stop up by judgement; a close "
        "below the 21-day EMA is this backtest's version.",
        "**No volume or tightness test.** The book wants volume to dry up in the flag and expand on the break; "
        "neither is checked.",
        "**Rare.** A doubling in eight weeks is uncommon among liquid stocks, so expect few trades a year.",
        "**Run it with its exit flags** (`backtest_args`); the default bracket would sell at the nominal target.",
        corporate_actions.CAVEAT_TRADED,
    )
    status = ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (burst group, grade D, "
              "credibility 1); optimise-stage runs queued in both markets. " + PASS_RULE)
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
        S1: ("Power play.\n\n- **Test:** today's close is at or under the peak.\n- **Signal:** a buy-stop at the "
             "peak for {expiry_bdays} sessions; the stop is the flag's lowest low."),
    }
    entry_rules = (
        "Signal. G1, G2 and S1 on today's close, with a stop between {MIN_STOP_PCT}% and {MAX_STOP_PCT}% below the "
        "entry, graded TRADE - HIGH CONFIDENCE.",
        "Order. A buy-stop at the peak for {expiry_bdays} sessions (backtest: fills when a session's high reaches "
        "it, at the open if it gaps above).",
        "One position per stock.",
    )
    stop_rules = ("Where it goes. The flag's lowest low, rounded down to the tick. It defines 1R and does not "
                  "move.",)
    target_rules = ("No target. The plan's target is entry + {NOMINAL_TARGET_R} R for the R column only; the "
                    "backtest runs with `--no-target`.",)
    exit_rules = (
        "Each session after the entry (backtest, `--exit-mode ma --ma-col ema21 --no-target`):",
        "1. The stop, at its price or at the open if the stock gaps under it.",
        "2. A close below the 21-day exponential average: sold at that close.",
    )
    param_docs = (
        ("Advance window", "ADVANCE_BARS", "G1: sessions before the peak whose lowest low starts the advance."),
        ("Advance", "ADVANCE_MIN_PCT", "G1: the peak's gain over that low, %, at least."),
        ("Flag minimum", "FLAG_MIN_BARS", "G2: sessions since the peak, today included, at least."),
        ("Flag window", "FLAG_MAX_BARS", "Sessions before today among which the peak is the highest high."),
        ("Flag depth", "MAX_DEPTH_PCT", "G2: the flag's lowest low under the peak, %, at most."),
        ("Order life", "expiry_bdays", "Sessions the buy-stop at the peak stays open."),
        ("Minimum stop", "MIN_STOP_PCT", "A stop closer than this % below the entry is not bought."),
        ("Maximum stop", "MAX_STOP_PCT", "A stop further than this % below the entry is not bought."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × R, for the R column only."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume", "The 20-day average of close × volume, at least."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
    )
    backtest_args = "--exit-mode ma --ma-col ema21 --no-target --rank-by setup_momentum --min-fill 0.5"

    def levels(self, ctx, result, cfg):
        e = ctx.extras
        return e["peak"], e["flag_low"], None, (
            f"{e['advance_pct']:.0f}% advance, {e['flag_bars']}-session flag; buy the break of {e['peak']:.2f}")
