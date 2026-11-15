"""RSI bullish divergence -- price makes a lower swing low while RSI(14) makes a higher one.

A widespread rule with no single source. The catalogue grades it E (tested and failed): it is here so the
failure is measured on this data, not because it is expected to work. On daily bars:

  * a swing low is a bar whose low is the lowest of SWING_K bars either side, so it is confirmed SWING_K
    sessions later; only confirmed swing lows are used;
  * within the last DIV_LOOK sessions, B is the most recent confirmed swing low and A the most recent one at
    least MIN_SEP sessions before B;
  * price makes a lower low (low B < low A), RSI a higher one (RSI at B > RSI at A), RSI at A at most OVERSOLD;
  * B is confirmed today: a buy-stop at today's high, the stop at low B.

The swing-low search mirrors core/divergence.py's `bearish` (which finds swing highs); it is written here
because that module is the chart's conflict check, not a trade rule.
"""

import numpy as np

from ..core.context import StockContext
from ..marketdata import corporate_actions
from .base import StrategyResult
from .swing_base import PASS_RULE, SwingSetupStrategy

SWING_K = 3              # a swing low is the lowest low of this many bars either side
DIV_LOOK = 40            # both swing lows lie within this many sessions, today included
MIN_SEP = 5              # A is at least this many sessions before B
OVERSOLD = 35            # G2: RSI(14) at A at most this
MIN_STOP_PCT = 1.0       # a stop closer than this % below the entry is not bought
MAX_STOP_PCT = 15.0      # nor one further than this %
NOMINAL_TARGET_R = 2     # the plan's target, in R
HOLD_BARS = 10           # backtest_args: sold at the close of this session after the entry

S1 = "S1"


def swing_lows(low: np.ndarray, lo: int) -> list[int]:
    """Confirmed swing lows at indices >= lo: low[i] is the lowest of low[i-SWING_K : i+SWING_K+1], and
    i + SWING_K is no later than the last bar."""
    n = len(low)
    return [i for i in range(max(SWING_K, lo), n - SWING_K)
            if low[i] == low[i - SWING_K:i + SWING_K + 1].min()]


class RsiDivergenceStrategy(SwingSetupStrategy):
    key = "rsi_divergence"
    name = "RSI bullish divergence"
    description = ("A lower swing low in price with a higher RSI(14) low from oversold, bought through the high "
                   "of the day the second low is confirmed. Graded E: expected to fail.")
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "v1: bullish RSI divergence on daily bars -- two confirmed swing lows ({SWING_K} bars either side) "
         "within {DIV_LOOK} sessions and {MIN_SEP}+ apart, price lower, RSI(14) higher from at most {OVERSOLD}; "
         "a buy-stop at the confirmation day's high, stop at the second low, {HOLD_BARS}-session limit."),
    )
    behaviour = "mean_reversion"
    style = "reversal"
    gate_codes = ("G1", "G2")
    screen_key = "above_200"
    screen_gates: dict = {}
    setup_codes = (S1,)
    setup_names = {S1: "Bullish RSI divergence confirmed"}
    gate_titles = {"G1": "Price lower low", "G2": "RSI higher low from oversold"}
    order = ""
    expiry_bdays = 3
    plan_code = "RD"
    extra_columns = ("low_a", "low_b", "rsi_a", "rsi_b", "bars_a_to_b", "level_entry", "level_stop")
    extra_numeric_columns = extra_columns

    thesis = (
        "When price makes a lower low but momentum does not, the selling that drove the second low was weaker "
        "than the first; the rule reads that as a decline losing force and buys the turn. It is one of the most "
        "widely taught signals and has no single source. The catalogue grades it E -- tested and failed in "
        "published work -- with credibility 1. It is run so that the failure is measured here; it is expected to "
        "fail."
    )
    how_it_works = (
        "**Universe.** Every liquid stock. The rule has no trend filter, so the Above the 200-day screen supplies "
        "the universe only, with no gate taken from it.",
        "**Swing lows.** A bar whose low is the lowest of the {SWING_K} bars either side. It is known only "
        "{SWING_K} sessions later, so only confirmed swing lows are used.",
        "**The pair.** Within the last {DIV_LOOK} sessions, B is the most recent confirmed swing low and A the "
        "most recent one at least {MIN_SEP} sessions before B.",
        "**The divergence (G1, G2).** Low B is below low A (G1: a lower low in price); RSI(14) at B is above RSI "
        "at A, and RSI at A is at most {OVERSOLD} (G2: a higher low in momentum, from oversold).",
        "**The signal (S1).** B was confirmed today: today is exactly {SWING_K} sessions after B.",
        "**The order.** A buy-stop at today's high for {expiry_bdays} sessions.",
        "**Stop and exit.** The stop is low B. The target is entry + {NOMINAL_TARGET_R} R; the position is sold "
        "at the close of session {HOLD_BARS} after the entry if neither was hit.",
    )
    caveats = (
        "**Expected to fail.** Graded E in the catalogue: published tests of divergence rules find no edge after "
        "costs. A pass here would need explaining before it was believed.",
        "**One definition of many.** Swing width, look-back, the oversold level and the entry vary by author; this "
        "is one reasonable set fixed before any run, not a search for the best one.",
        "**The exit is a stand-in.** The rule has no standard exit; the {NOMINAL_TARGET_R} R target and the "
        "{HOLD_BARS}-session limit are this backtest's.",
        "**Survivorship.** The universe is today's stock lists; declines that kept going into a delisting are "
        "missing, which flatters a bottom-buying rule.",
        "**Run it with its flags** (`backtest_args`).",
        corporate_actions.CAVEAT_TRADED,
    )
    status = ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (reversal group, grade E -- "
              "tested and failed in published work, so expected to fail here -- credibility 1); optimise-stage "
              "runs queued in both markets. " + PASS_RULE)
    gate_docs = {
        "G1": ("Price makes a lower low.\n\n- **Test:** two confirmed swing lows A and B exist (within {DIV_LOOK} "
               "sessions, at least {MIN_SEP} apart) and low B is below low A.\n- **Fails:** fewer than two such "
               "swing lows, or B at or above A."),
        "G2": ("RSI makes a higher low from oversold.\n\n- **Test:** RSI(14) at B is above RSI(14) at A, and RSI at "
               "A is at most {OVERSOLD}.\n- **Fails:** RSI at B at or below A, or A not oversold."),
    }
    watch_docs: dict = {}
    setup_docs = {
        S1: ("Bullish RSI divergence confirmed.\n\n- **Test:** swing low B was confirmed today (today is {SWING_K} "
             "sessions after B).\n- **Signal:** a buy-stop at today's high for {expiry_bdays} sessions; the stop "
             "is low B."),
    }
    entry_rules = (
        "Signal. G1, G2 and S1 on today's close, with a stop between {MIN_STOP_PCT}% and {MAX_STOP_PCT}% below the "
        "entry, graded TRADE - HIGH CONFIDENCE.",
        "Order. A buy-stop at today's high for {expiry_bdays} sessions (backtest: fills when a session's high "
        "reaches it, at the open if it gaps above; cancelled if the stop is hit first).",
        "One position per stock.",
    )
    stop_rules = ("Where it goes. Low B, rounded down to the tick. It defines 1R; it does not move.",)
    target_rules = ("Entry + {NOMINAL_TARGET_R} R.",)
    exit_rules = (
        "Each session after the entry (backtest, the default bracket with `--time-stop-bars {HOLD_BARS}`):",
        "1. The stop, at its price or at the open if the stock gaps under it.",
        "2. The target, at its price or at the open if the stock gaps over it.",
        "3. The time limit: sold at the close of session {HOLD_BARS} after the entry.",
    )
    param_docs = (
        ("Swing width", "SWING_K", "A swing low is the lowest low of this many bars either side."),
        ("Look-back", "DIV_LOOK", "Both swing lows lie within this many sessions, today included."),
        ("Separation", "MIN_SEP", "A is at least this many sessions before B."),
        ("Oversold", "OVERSOLD", "G2: RSI(14) at A at most this."),
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
        n = DIV_LOOK + SWING_K
        if len(d) < n:
            result.fail("G1", "insufficient history")
            return
        tail = d.iloc[-n:]
        low = tail["low"].to_numpy(float)
        rsi = tail["rsi14"].to_numpy(float)
        today = n - 1
        lows = swing_lows(low, n - DIV_LOOK)
        e.update(level_entry=float(tail["high"].iloc[-1]))
        if not lows:
            result.fail("G1", "no confirmed swing low")
            return
        b = lows[-1]
        older = [i for i in lows if i <= b - MIN_SEP]
        e.update(low_b=float(low[b]), rsi_b=float(rsi[b]), level_stop=float(low[b]))
        if not older:
            result.fail("G1", f"no earlier swing low {MIN_SEP}+ sessions before the last")
            return
        a = older[-1]
        e.update(low_a=float(low[a]), rsi_a=float(rsi[a]), bars_a_to_b=b - a)
        if low[b] < low[a]:
            result.ok("G1", f"low {low[b]:.2f} under {low[a]:.2f}")
        else:
            result.fail("G1", f"low {low[b]:.2f} not under {low[a]:.2f}")
        if rsi[b] > rsi[a] and rsi[a] <= OVERSOLD:
            result.ok("G2", f"RSI {rsi[b]:.1f} over {rsi[a]:.1f} (from <= {OVERSOLD})")
        elif not rsi[b] > rsi[a]:
            result.fail("G2", f"RSI {rsi[b]:.1f} not over {rsi[a]:.1f}")
        else:
            result.fail("G2", f"RSI at A {rsi[a]:.1f} (> {OVERSOLD})")
        result.setups[S1] = bool(b == today - SWING_K)

    def levels(self, ctx, result, cfg):
        e = ctx.extras
        return e["level_entry"], e["level_stop"], None, (
            f"lower low {e['low_b']:.2f} with RSI {e['rsi_b']:.1f} over {e['rsi_a']:.1f}; buy through today's high")
