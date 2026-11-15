"""Elder triple screen -- Alexander Elder's weekly tide, daily wave, buy-stop entry (Trading for a Living, 1993).

Three screens, each on a shorter timeframe than the last:

  * the tide (weekly): the 13-week EMA of weekly closes is rising;
  * the wave (daily): the 2-day EMA of the Force Index ((close − previous close) × volume) is below zero --
    a pullback inside the weekly uptrend;
  * the entry: a buy-stop at today's high for the next session; a fresh signal the next day moves it to that
    day's high, which is Elder's trailing buy-stop.

The stop is the lower of today's and yesterday's lows; the exit the shared bracket with a nominal target of
NOMINAL_TARGET_R and a HOLD_BARS-session time limit (`backtest_args`).
"""

import numpy as np

from ..core.context import StockContext
from ..marketdata import corporate_actions
from .base import StrategyResult
from .swing_base import PASS_RULE, SwingSetupStrategy

WEEKLY_EMA = 13          # G1: span of the weekly-close EMA that must be rising
FORCE_EMA = 2            # S1: span of the daily Force Index EMA that must be below zero
FORCE_TAIL = 60          # daily sessions the Force Index EMA is computed over (it settles within a few)
MIN_STOP_PCT = 1.0       # a stop closer than this % below the entry is not bought
MAX_STOP_PCT = 10.0      # nor one further than this %
NOMINAL_TARGET_R = 2     # the plan's target, in R
HOLD_BARS = 15           # backtest_args: sold at the close of this session after the entry

S1 = "S1"


def _ema(x: np.ndarray, span: int) -> np.ndarray:
    a = 2.0 / (span + 1)
    out = np.empty_like(x)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


class ElderTripleScreenStrategy(SwingSetupStrategy):
    key = "elder_triple_screen"
    name = "Elder triple screen"
    description = ("Elder's three screens: a rising 13-week EMA (the tide), a negative 2-day Force Index (the "
                   "wave against it), and a buy-stop at the day's high (the entry).")
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "v1: the triple screen as Trading for a Living states it on daily bars -- a rising {WEEKLY_EMA}-week EMA, "
         "a {FORCE_EMA}-day Force Index EMA below zero, a one-session buy-stop at today's high, the stop under the "
         "lower of two days' lows; a {NOMINAL_TARGET_R} R target and a {HOLD_BARS}-session limit."),
    )
    behaviour = "trend_momentum"
    style = "pullback"
    gate_codes = ("G1",)
    screen_key = "above_200"
    screen_gates: dict = {}
    setup_codes = (S1,)
    setup_names = {S1: "Force Index pullback in a weekly uptrend"}
    gate_titles = {"G1": "{WEEKLY_EMA}-week EMA rising"}
    order = ""
    expiry_bdays = 1
    plan_code = "ET"
    extra_columns = ("weekly_ema", "weekly_ema_prev", "force_ema", "level_entry", "level_stop")
    extra_numeric_columns = extra_columns

    thesis = (
        "Trade with the weekly trend and enter on a daily move against it. A rising weekly average says buyers are "
        "in control; a negative Force Index on the daily chart says the latest few days were a pullback, so a buy "
        "there gets a better price than chasing. The buy-stop above the day's high waits for the pullback to end. "
        "Alexander Elder, *Trading for a Living* (1993). The catalogue grades it D (a textbook method, no "
        "published test), credibility 1."
    )
    how_it_works = (
        "**Universe.** Every liquid stock. Elder uses no 200-day rule, so none is added; the Above the 200-day "
        "screen supplies the universe only, with no gate taken from it.",
        "**First screen, the tide (G1).** The {WEEKLY_EMA}-week exponential average of weekly closes is above its "
        "value a week earlier.",
        "**Second screen, the wave (S1).** The Force Index is (close − previous close) × volume; its "
        "{FORCE_EMA}-day exponential average is below zero today: a pullback inside the weekly uptrend.",
        "**Third screen, the entry.** A buy-stop at today's high for the next session only. If it does not fill "
        "and the wave is still negative, the next day's signal places it at that day's high -- Elder's buy-stop "
        "trailed down day by day.",
        "**Stop and exit.** The stop is the lower of today's and yesterday's lows. The target is entry + "
        "{NOMINAL_TARGET_R} R; the position is sold at the close of session {HOLD_BARS} after the entry if "
        "neither stop nor target was hit.",
    )
    caveats = (
        "**The current week is partial.** The weekly EMA's latest value uses the current week up to today, so "
        "mid-week the tide reads a week that is not finished; Elder reads completed weeks, or the live week as "
        "it develops. The previous value is last week's.",
        "**One oscillator of several.** Elder offers Force Index, Elder-ray, stochastics or Williams %R for the "
        "second screen; Force Index EMA(2) is the one tested.",
        "**The exit is a stand-in.** Elder's exits are discretionary (channel targets, a SafeZone stop); the "
        "{NOMINAL_TARGET_R} R target and the {HOLD_BARS}-session limit are this backtest's.",
        "**Survivorship.** The universe is today's stock lists; weekly uptrends that ended in a delisting are "
        "missing.",
        "**Run it with its flags** (`backtest_args`).",
        corporate_actions.CAVEAT_TRADED,
    )
    status = ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (pullback group, grade D, "
              "credibility 1); optimise-stage runs queued in both markets. " + PASS_RULE)
    gate_docs = {
        "G1": ("The weekly tide is up.\n\n- **Test:** the {WEEKLY_EMA}-week EMA of weekly closes (the current, "
               "possibly partial, week as its latest row) is above its value the week before.\n- **Fails:** flat "
               "or falling, or fewer than {WEEKLY_EMA} weeks of history."),
    }
    watch_docs: dict = {}
    setup_docs = {
        S1: ("The daily wave is down.\n\n- **Test:** the {FORCE_EMA}-day EMA of the Force Index, (close − previous "
             "close) × volume, computed over the last {FORCE_TAIL} sessions, is below zero today.\n- **Signal:** a "
             "buy-stop at today's high for the next session; the stop is the lower of today's and yesterday's "
             "lows."),
    }
    entry_rules = (
        "Signal. G1 and S1 on today's close, with a stop between {MIN_STOP_PCT}% and {MAX_STOP_PCT}% below the "
        "entry, graded TRADE - HIGH CONFIDENCE.",
        "Order. A buy-stop at today's high for the next session only (backtest: fills when that session's high "
        "reaches it, at the open if it gaps above; cancelled if the stop is hit first).",
        "One position per stock.",
    )
    stop_rules = ("Where it goes. The lower of today's and yesterday's lows, rounded down to the tick. It defines "
                  "1R; it does not move.",)
    target_rules = ("Entry + {NOMINAL_TARGET_R} R.",)
    exit_rules = (
        "Each session after the entry (backtest, the default bracket with `--time-stop-bars {HOLD_BARS}`):",
        "1. The stop, at its price or at the open if the stock gaps under it.",
        "2. The target, at its price or at the open if the stock gaps over it.",
        "3. The time limit: sold at the close of session {HOLD_BARS} after the entry.",
    )
    param_docs = (
        ("Weekly EMA", "WEEKLY_EMA", "G1: span, in weeks, of the EMA of weekly closes."),
        ("Force Index EMA", "FORCE_EMA", "S1: span, in sessions, of the Force Index EMA."),
        ("Force Index window", "FORCE_TAIL", "S1: sessions the Force Index EMA is computed over."),
        ("Minimum stop", "MIN_STOP_PCT", "A stop closer than this % below the entry is not bought."),
        ("Maximum stop", "MAX_STOP_PCT", "A stop further than this % below the entry is not bought."),
        ("Target", "NOMINAL_TARGET_R", "Target = entry + this × R."),
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
        wk = ctx.weekly["close"].to_numpy(float) if ctx.weekly is not None else np.array([])
        wk = wk[~np.isnan(wk)]
        if len(wk) < WEEKLY_EMA + 1 or len(d) < FORCE_TAIL + 1:
            result.fail("G1", "insufficient history")
            return
        wema = _ema(wk, WEEKLY_EMA)
        tail = d.iloc[-FORCE_TAIL - 1:]
        closes = tail["close"].to_numpy(float)
        force = np.diff(closes) * tail["volume"].to_numpy(float)[1:]
        fema = float(_ema(np.nan_to_num(force), FORCE_EMA)[-1])
        lows = tail["low"].to_numpy(float)
        stop = float(min(lows[-1], lows[-2]))
        e.update(weekly_ema=float(wema[-1]), weekly_ema_prev=float(wema[-2]), force_ema=fema,
                 level_entry=float(tail["high"].iloc[-1]), level_stop=stop)
        if wema[-1] > wema[-2]:
            result.ok("G1", f"{WEEKLY_EMA}-week EMA {wema[-1]:.2f} > {wema[-2]:.2f}")
        else:
            result.fail("G1", f"{WEEKLY_EMA}-week EMA not rising")
        result.setups[S1] = bool(fema < 0)

    def levels(self, ctx, result, cfg):
        e = ctx.extras
        return e["level_entry"], e["level_stop"], None, (
            f"weekly tide up, Force Index EMA {e['force_ema']:.3g} below zero; buy through today's high")
