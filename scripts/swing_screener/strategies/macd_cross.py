"""MACD crossover -- a NEGATIVE CONTROL: the MACD line crossing above its signal line.

Gerald Appel's MACD (1979) is the difference of a fast and a slow exponential average of closes; its
signal line is an exponential average of that difference. Buying the bullish cross is among the most
taught chart rules and among the most tested, and on individual stocks it has not survived costs. It is
in the catalogue on purpose, as a control expected to fail: with the same cash, slots, costs and ranking
as every catalogue setup, it shows what "no edge" looks like here.

  * MACD = EMA(FAST) - EMA(SLOW) of closes; signal = EMA(SIGNAL) of MACD, from the last MACD_TAIL bars;
  * today MACD is above the signal, having been at or below it yesterday: buy the close;
  * the stop is STOP_ATR x ATR14 below; sold on a close below the 21-day EMA, the stand-in for the
    bearish cross, which is not an available exit.
"""

import numpy as np

from ..core.context import StockContext
from ..marketdata import corporate_actions
from .base import StrategyResult
from .swing_base import PASS_RULE, SwingSetupStrategy

FAST = 12                # MACD's fast EMA span, sessions
SLOW = 26                # MACD's slow EMA span
SIGNAL = 9               # the signal line's EMA span, of MACD
MACD_TAIL = 300          # closes the EMAs are computed from (long enough for the seed to wash out)
STOP_ATR = 2             # the stop, this many ATR14 below the entry
MIN_STOP_PCT = 1.0       # a stop closer than this % below the entry is not bought
MAX_STOP_PCT = 15.0      # nor one further than this %
NOMINAL_TARGET_R = 2     # the plan's target, for the R column only (the backtest runs --no-target)

S1 = "S1"


def _ema(x: np.ndarray, span: int) -> np.ndarray:
    """Exponential average, alpha = 2 / (span + 1), seeded on the first value (pandas adjust=False)."""
    a = 2.0 / (span + 1)
    out = np.empty_like(x)
    acc = x[0]
    for i, v in enumerate(x):
        acc = acc + a * (v - acc)
        out[i] = acc
    return out


class MacdCrossStrategy(SwingSetupStrategy):
    key = "macd_cross"
    name = "MACD crossover (negative control)"
    description = ("A negative control, expected to fail: buy when MACD crosses above its signal line, sell on a "
                   "close below the 21-day EMA. It calibrates what \"no edge\" looks like here.")
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "v1: Appel's MACD ({FAST}, {SLOW}, {SIGNAL}) bullish cross as a negative control -- buy the close of the "
         "cross, a {STOP_ATR} ATR14 stop, sold on a close below the 21-day EMA."),
    )
    behaviour = "trend_momentum"
    style = "trend"
    gate_codes: tuple = ()
    screen_key = "above_200"
    screen_gates: dict = {}
    setup_codes = (S1,)
    setup_names = {S1: "MACD bullish cross"}
    gate_titles: dict = {}
    order = "close"
    expiry_bdays = None
    plan_code = "MC"
    extra_columns = ("macd", "macd_signal", "macd_hist", "level_entry", "level_stop")
    extra_numeric_columns = extra_columns

    thesis = (
        "None claimed: this is a negative control, expected to fail. Gerald Appel's MACD (1979) crossing above "
        "its signal line is one of the most taught buy signals; tests of it on individual stocks find no edge "
        "that survives costs. The catalogue grades it E (tested and failed), credibility 1. It runs with the same "
        "cash, slots, costs and ranking as every catalogue setup, so its result shows what \"no edge\" looks like "
        "with these mechanics -- a setup that cannot clearly beat it has not shown an edge either."
    )
    how_it_works = (
        "**A negative control.** It is expected to fail, and is here to calibrate the catalogue: read a real "
        "setup's result against this one.",
        "**Universe.** Every liquid stock. The rule has no trend filter, so the Above the 200-day screen supplies "
        "the universe only, with no gate taken from it.",
        "**MACD.** The {FAST}-session exponential average of closes minus the {SLOW}-session one; the signal "
        "line is the {SIGNAL}-session exponential average of MACD. Both are computed from the last {MACD_TAIL} "
        "closes, enough for the starting value to wash out.",
        "**The cross (S1).** Today MACD is above its signal line, and yesterday it was at or below it. Bought at "
        "today's close.",
        "**Stop and exit.** The stop is {STOP_ATR} ATR14 below the entry. The rule sells on the bearish cross, "
        "which is not an available exit; a close below the 21-day EMA is its stand-in. No target.",
    )
    caveats = (
        "**Expected to fail.** It is a calibration run, not a candidate; a pass would be a surprise worth checking.",
        "**The exit is a stand-in.** The bearish MACD cross is not an available exit, so the position is sold on "
        "a close below the 21-day EMA, which is roughly as quick but not the same rule.",
        "**The stop is not in the rule.** The {STOP_ATR} ATR14 stop exists so the position can be sized by risk "
        "like every other catalogue setup.",
        "**Survivorship.** The universe is today's stock lists, which flatters any long rule.",
        "**Run it with its exit flags** (`backtest_args`); the default bracket would sell at the nominal target.",
        corporate_actions.CAVEAT_TRADED,
    )
    status = ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (trend group, grade E, credibility "
              "1) as a negative control, expected to fail; optimise-stage runs queued in both markets. " + PASS_RULE)
    gate_docs: dict = {}
    watch_docs: dict = {}
    setup_docs = {
        S1: ("MACD bullish cross.\n\n- **Test:** today MACD ({FAST}/{SLOW}) is above its {SIGNAL}-session signal "
             "line, and yesterday it was at or below it.\n- **Signal:** buy today's close; stop {STOP_ATR} ATR14 "
             "below."),
    }
    entry_rules = (
        "Signal. S1 on today's close, with the stop between {MIN_STOP_PCT}% and {MAX_STOP_PCT}% below the entry, "
        "graded TRADE - HIGH CONFIDENCE.",
        "Order. Bought at the signal session's close.",
        "One position per stock.",
    )
    stop_rules = ("Where it goes. Entry − {STOP_ATR} × ATR14, rounded down to the tick. It defines 1R and does "
                  "not move.",)
    target_rules = ("No target. The plan's target is entry + {NOMINAL_TARGET_R} R for the R column only; the "
                    "backtest runs with `--no-target`.",)
    exit_rules = (
        "Each session after the entry (backtest, `--exit-mode ma --ma-col ema21 --no-target`):",
        "1. The stop, at its price or at the open if the stock gaps under it.",
        "2. A close below the 21-day EMA: sold (the stand-in for the bearish cross).",
    )
    param_docs = (
        ("Fast EMA", "FAST", "MACD's fast exponential average, sessions."),
        ("Slow EMA", "SLOW", "MACD's slow exponential average, sessions."),
        ("Signal EMA", "SIGNAL", "The signal line's exponential average of MACD, sessions."),
        ("History used", "MACD_TAIL", "Closes the averages are computed from."),
        ("Stop", "STOP_ATR", "ATR14 multiples below the entry."),
        ("Minimum stop", "MIN_STOP_PCT", "A stop closer than this % below the entry is not bought."),
        ("Maximum stop", "MAX_STOP_PCT", "A stop further than this % below the entry is not bought."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × R, for the R column only."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume", "The 20-day average of close × volume, at least."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
    )
    backtest_args = "--exit-mode ma --ma-col ema21 --no-target --rank-by setup_momentum --min-fill 0.5"

    def detect(self, ctx: StockContext, result: StrategyResult) -> None:
        d, e = ctx.daily, ctx.extras
        closes = d["close"].to_numpy()[-MACD_TAIL:].astype(float)
        if len(closes) < SLOW + SIGNAL or np.isnan(closes).any():
            return
        macd = _ema(closes, FAST) - _ema(closes, SLOW)
        sig = _ema(macd, SIGNAL)
        close, atr = float(closes[-1]), float(d["atr14"].iloc[-1])
        e.update(macd=macd[-1], macd_signal=sig[-1], macd_hist=macd[-1] - sig[-1],
                 level_entry=close, level_stop=close - STOP_ATR * atr)
        result.setups[S1] = bool(macd[-1] > sig[-1] and macd[-2] <= sig[-2])

    def levels(self, ctx, result, cfg):
        e = ctx.extras
        return e["level_entry"], e["level_stop"], None, (
            f"MACD {e['macd']:.3f} crossed above its signal {e['macd_signal']:.3f}")
