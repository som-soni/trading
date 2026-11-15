"""Golden cross -- a NEGATIVE CONTROL: the 50-day average crossing above the 200-day.

The most quoted signal in financial media, and one that published tests have repeatedly found to carry
no edge on individual stocks once costs and the lag are counted. It is in the catalogue on purpose, as a
control expected to fail: it shows what "no edge" looks like with this backtester's mechanics (the cash,
slots, costs and ranking every catalogue setup shares), so a real setup's result can be read against it.

  * today the 50-day simple average closes above the 200-day, having been at or below it yesterday;
  * buy that close, with a wide catastrophe/sizing stop STOP_PCT % below;
  * sell on a close below the 200-day average -- the stand-in for the death cross, which is not an
    available exit.
"""

from ..core.context import StockContext
from ..marketdata import corporate_actions
from .base import StrategyResult
from .swing_base import PASS_RULE, SwingSetupStrategy

STOP_PCT = 15.0          # the catastrophe/sizing stop, % below the entry
MIN_STOP_PCT = 1.0       # a stop closer than this % below the entry is not bought
MAX_STOP_PCT = 20.0      # nor one further than this %
NOMINAL_TARGET_R = 2     # the plan's target, for the R column only (the backtest runs --no-target)

S1 = "S1"


class GoldenCrossStrategy(SwingSetupStrategy):
    key = "golden_cross"
    name = "Golden cross (negative control)"
    description = ("A negative control, expected to fail: buy when the 50-day average crosses above the 200-day, "
                   "sell on a close below the 200-day. It calibrates what \"no edge\" looks like here.")
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "v1: the golden cross as a negative control -- buy the close of the session the 50-day average crosses "
         "above the 200-day, a {STOP_PCT}% catastrophe stop, sold on a close below the 200-day."),
    )
    behaviour = "trend_momentum"
    style = "trend"
    horizon = "positional"
    gate_codes: tuple = ()
    screen_key = "above_200"
    screen_gates: dict = {}
    setup_codes = (S1,)
    setup_names = {S1: "Golden cross"}
    gate_titles: dict = {}
    order = "close"
    expiry_bdays = None
    plan_code = "GC"
    extra_columns = ("sma50", "sma200", "close_vs_sma200_pct", "level_entry", "level_stop")
    extra_numeric_columns = extra_columns

    thesis = (
        "None claimed: this is a negative control, expected to fail. The golden cross is the most widely quoted "
        "moving-average signal, with no single author; published tests of it on individual stocks find no "
        "reliable edge after costs and the lag of two slow averages. The catalogue grades it E (tested and "
        "failed), credibility 1. It runs with the same cash, slots, costs and ranking as every catalogue setup, "
        "so its result shows what \"no edge\" looks like with these mechanics -- a setup that cannot clearly beat "
        "it has not shown an edge either."
    )
    how_it_works = (
        "**A negative control.** It is expected to fail, and is here to calibrate the catalogue: read a real "
        "setup's result against this one.",
        "**Universe.** Every liquid stock. The rule is its own trend filter, so the Above the 200-day screen "
        "supplies the universe only, with no gate taken from it.",
        "**The cross (S1).** Today the 50-day simple average is above the 200-day, and yesterday it was at or "
        "below it. Bought at today's close.",
        "**Stop.** A catastrophe and sizing stop {STOP_PCT}% below the entry; the published rule has none.",
        "**Exit.** The rule sells on the death cross (the 50-day back under the 200-day), which is not an "
        "available exit; a close below the 200-day average is its stand-in. No target.",
    )
    caveats = (
        "**Expected to fail.** It is a calibration run, not a candidate; a pass would be a surprise worth checking.",
        "**The exit is a stand-in.** The death cross is not an available exit, so the position is sold on a "
        "close below the 200-day average. That exits sooner than the death cross (price leaves the 200-day long "
        "before the 50-day does), and a cross made while the close is still under the 200-day sells the next "
        "session.",
        "**The stop is not in the rule.** The {STOP_PCT}% stop exists so the position can be sized by risk like "
        "every other catalogue setup.",
        "**Survivorship.** The universe is today's stock lists, which flatters any long rule.",
        "**Run it with its exit flags** (`backtest_args`); the default bracket would sell at the nominal target.",
        corporate_actions.CAVEAT_TRADED,
    )
    status = ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (trend group, grade E, credibility "
              "1) as a negative control, expected to fail; optimise-stage runs queued in both markets. " + PASS_RULE)
    gate_docs: dict = {}
    watch_docs: dict = {}
    setup_docs = {
        S1: ("Golden cross.\n\n- **Test:** today's 50-day simple average is above today's 200-day, and yesterday's "
             "50-day was at or below yesterday's 200-day.\n- **Signal:** buy today's close; stop {STOP_PCT}% below."),
    }
    entry_rules = (
        "Signal. S1 on today's close, with the stop between {MIN_STOP_PCT}% and {MAX_STOP_PCT}% below the entry, "
        "graded TRADE - HIGH CONFIDENCE.",
        "Order. Bought at the signal session's close.",
        "One position per stock.",
    )
    stop_rules = ("Where it goes. {STOP_PCT}% below the entry, rounded down to the tick. It defines 1R and does "
                  "not move.",)
    target_rules = ("No target. The plan's target is entry + {NOMINAL_TARGET_R} R for the R column only; the "
                    "backtest runs with `--no-target`.",)
    exit_rules = (
        "Each session after the entry (backtest, `--exit-mode ma --ma-col sma200 --no-target`):",
        "1. The stop, at its price or at the open if the stock gaps under it.",
        "2. A close below the 200-day simple average: sold (the stand-in for the death cross).",
    )
    param_docs = (
        ("Stop", "STOP_PCT", "The catastrophe/sizing stop, % below the entry."),
        ("Minimum stop", "MIN_STOP_PCT", "A stop closer than this % below the entry is not bought."),
        ("Maximum stop", "MAX_STOP_PCT", "A stop further than this % below the entry is not bought."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × R, for the R column only."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume", "The 20-day average of close × volume, at least."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
    )
    backtest_args = "--exit-mode ma --ma-col sma200 --no-target --rank-by setup_momentum --min-fill 0.5"

    def detect(self, ctx: StockContext, result: StrategyResult) -> None:
        d, e = ctx.daily, ctx.extras
        if len(d) < 2:
            return
        f = d["sma50"].to_numpy()[-2:].astype(float)
        s = d["sma200"].to_numpy()[-2:].astype(float)
        close = float(d["close"].iloc[-1])
        e.update(sma50=f[-1], sma200=s[-1], close_vs_sma200_pct=(close / s[-1] - 1) * 100 if s[-1] > 0 else float("nan"),
                 level_entry=close, level_stop=close * (1 - STOP_PCT / 100))
        result.setups[S1] = bool(f[-1] > s[-1] and f[-2] <= s[-2])   # NaN compares False

    def levels(self, ctx, result, cfg):
        e = ctx.extras
        return e["level_entry"], e["level_stop"], None, (
            f"50-day {e['sma50']:.2f} crossed above the 200-day {e['sma200']:.2f}")
