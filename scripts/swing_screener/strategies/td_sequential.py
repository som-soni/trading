"""TD Sequential -- Tom DeMark's exhaustion count (The New Science of Technical Analysis, 1994).

The long half on daily bars:

  * buy setup: SETUP_COUNT consecutive closes each below the close LOOKBACK sessions earlier, preceded by a
    price flip (the close before bar 1 above the close LOOKBACK before it);
  * S1, a perfected setup completing today: the low of bar 8 or 9 at or below the lows of bars 6 and 7
    (PERFECT_LATE_BAR, SETUP_COUNT; PERFECT_REF_A, PERFECT_REF_B);
  * S2, a countdown completing today: after the most recent completed setup (bar 9 within COUNTDOWN_WINDOW
    sessions before today), sessions from the bar after bar 9 whose close is at or below the low CD_LOOKBACK
    sessions earlier are counted (not necessarily consecutive); the COUNTDOWN-th count is today, with a low at
    or below the close of countdown bar 8; a close above the setup's highest high cancels it;
  * buy the close; the stop the lowest low of the span minus that bar's true range (DeMark's stop); the
    shared bracket with a nominal target and a HOLD_BARS-session limit.
"""

import numpy as np

from ..core.context import StockContext
from ..marketdata import corporate_actions
from .base import StrategyResult
from .swing_base import PASS_RULE, SwingSetupStrategy

SETUP_COUNT = 9          # bars in a buy setup
LOOKBACK = 4             # each setup close below the close this many sessions earlier
COUNTDOWN = 13           # countdown bars to completion
CD_LOOKBACK = 2          # a countdown close at or below the low this many sessions earlier
COUNTDOWN_WINDOW = 60    # S2: bar 9 of the setup is at most this many sessions before today
SCAN_BARS = 80           # sessions searched for the setup and countdown (bounds the scan)
PERFECT_REF_A = 6        # S1: the low of bar PERFECT_LATE_BAR or SETUP_COUNT at or below the lows of
PERFECT_REF_B = 7        #     setup bars PERFECT_REF_A and PERFECT_REF_B
PERFECT_LATE_BAR = 8
CD_REF_BAR = 8           # S2: the last countdown bar's low at or below this countdown bar's close
MIN_STOP_PCT = 1.0       # a stop closer than this % below the entry is not bought
MAX_STOP_PCT = 15.0      # nor one further than this %
NOMINAL_TARGET_R = 2     # the plan's target, in R
HOLD_BARS = 12           # backtest_args: sold at the close of this session after the entry

S1 = "S1"
S2 = "S2"


def _setup_ends(close: np.ndarray) -> np.ndarray:
    """Indices j where a buy setup's bar 9 falls: SETUP_COUNT closes below the close LOOKBACK earlier ending at j,
    the close before bar 1 above the close LOOKBACK before it (the price flip)."""
    n = len(close)
    below = np.zeros(n, bool)
    above = np.zeros(n, bool)
    below[LOOKBACK:] = close[LOOKBACK:] < close[:-LOOKBACK]
    above[LOOKBACK:] = close[LOOKBACK:] > close[:-LOOKBACK]
    run = np.zeros(n, int)
    for i in range(n):
        run[i] = run[i - 1] + 1 if below[i] and i > 0 else (1 if below[i] else 0)
    ends = []
    for j in range(SETUP_COUNT + LOOKBACK, n):
        b0 = j - SETUP_COUNT          # the bar before bar 1
        if run[j] == SETUP_COUNT and above[b0]:
            ends.append(j)
    return np.array(ends, int)


def _true_range(high, low, close, i) -> float:
    pc = close[i - 1] if i > 0 else close[i]
    return float(max(high[i], pc) - min(low[i], pc))


class TdSequentialStrategy(SwingSetupStrategy):
    key = "td_sequential"
    name = "TD Sequential"
    description = ("DeMark's exhaustion count, long side: a perfected buy setup or a completed buy "
                   "countdown, bought at the close with DeMark's stop under the low.")
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "v1: TD Sequential's buy side on daily bars -- a perfected {SETUP_COUNT}-bar setup (S1) or a "
         "{COUNTDOWN}-bar countdown (S2) completing today, bought at the close; stop the span's lowest low minus "
         "its true range, a {NOMINAL_TARGET_R} R target and a {HOLD_BARS}-session limit."),
    )
    behaviour = "mean_reversion"
    style = "reversal"
    gate_codes: tuple = ()
    screen_key = "above_200"
    screen_gates: dict = {}
    setup_codes = (S1, S2)
    setup_names = {S1: "Perfected buy setup", S2: "Buy countdown"}
    gate_titles: dict = {}
    order = "close"
    expiry_bdays = None
    plan_code = "TD"
    extra_columns = ("setup_low", "countdown_count", "level_entry", "level_stop")
    extra_numeric_columns = extra_columns

    thesis = (
        "A decline that has closed below the close {LOOKBACK} sessions earlier {SETUP_COUNT} times running has used "
        "up its near-term sellers; a decline that goes on to a {COUNTDOWN}-bar countdown is exhausted. DeMark's count times the end "
        "of a move rather than following it. Tom DeMark, *The New Science of Technical Analysis* (1994). The "
        "catalogue grades it D (widely used, no published test of the rules as stated), credibility 1."
    )
    how_it_works = (
        "**Universe.** Every liquid stock. TD Sequential uses no trend filter, so the Above the 200-day screen "
        "supplies the universe only, with no gate taken from it. There are no gates: the count is the setup.",
        "**Buy setup.** {SETUP_COUNT} consecutive closes, each below the close {LOOKBACK} sessions earlier, "
        "preceded by a price flip: the close before the first bar was above the close {LOOKBACK} sessions before it.",
        "**S1, a perfected setup today.** Bar {SETUP_COUNT} is today, and the low of bar {PERFECT_LATE_BAR} or bar "
        "{SETUP_COUNT} is at or below the lows of bars {PERFECT_REF_A} and {PERFECT_REF_B}.",
        "**S2, a countdown today.** Take the most recent setup whose bar {SETUP_COUNT} lies within the "
        "{COUNTDOWN_WINDOW} sessions before today. From the bar after it, count each session whose close is at or "
        "below the low {CD_LOOKBACK} sessions earlier (not necessarily consecutive). S2 fires when the "
        "{COUNTDOWN}th count is today and today's low is at or below the close of countdown bar {CD_REF_BAR}. Any "
        "close after bar {SETUP_COUNT} above the setup's highest high cancels the countdown. The search looks at "
        "the last {SCAN_BARS} sessions only.",
        "**Buy.** At today's close.",
        "**Stop and exit.** The stop is the lowest low of the setup (S1) or of the setup through today (S2), "
        "minus that bar's true range -- DeMark's stop. The target is entry + {NOMINAL_TARGET_R} R; the position "
        "is sold at the close of session {HOLD_BARS} after the entry if neither was hit.",
    )
    caveats = (
        "**No deferred final count.** DeMark defers a {COUNTDOWN}th count whose low is above bar {CD_REF_BAR}'s close to the next qualifying "
        "bar; here such a count simply does not fire, as the spec decided.",
        "**No recycling.** DeMark restarts or recycles a countdown when a new setup appears during it; here the "
        "countdown belongs to the most recent completed setup before today, and its own cancellation rule is the "
        "only one applied.",
        "**The exit is a stand-in.** DeMark exits on the opposite count or a stop; the {NOMINAL_TARGET_R} R target "
        "and the {HOLD_BARS}-session limit are this backtest's.",
        "**Survivorship.** The universe is today's stock lists; declines that kept going into a delisting are "
        "missing, which flatters an exhaustion-buying rule.",
        "**Run it with its flags** (`backtest_args`).",
        corporate_actions.CAVEAT_TRADED,
    )
    status = ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (reversal group, grade D, "
              "credibility 1); optimise-stage runs queued in both markets. " + PASS_RULE)
    gate_docs: dict = {}
    watch_docs: dict = {}
    setup_docs = {
        S1: ("Perfected buy setup.\n\n- **Test:** a buy setup's bar {SETUP_COUNT} is today, and min(low of bars "
             "{PERFECT_LATE_BAR} and {SETUP_COUNT}) ≤ min(low of bars {PERFECT_REF_A} and {PERFECT_REF_B}).\n- **Signal:** buy today's close; the stop is the "
             "setup's lowest low minus that bar's true range."),
        S2: ("Buy countdown {COUNTDOWN}.\n\n- **Test:** the {COUNTDOWN}th countdown bar (close ≤ low "
             "{CD_LOOKBACK} sessions earlier) after the most recent setup is today, today's low ≤ countdown bar "
             "{CD_REF_BAR}'s close, the setup ended within {COUNTDOWN_WINDOW} sessions, and no close since it "
             "exceeded its highest high.\n- **Signal:** buy today's close; the stop is the lowest low from the "
             "setup's first bar through today minus that bar's true range."),
    }
    entry_rules = (
        "Signal. S1 or S2 on today's close, with a stop between {MIN_STOP_PCT}% and {MAX_STOP_PCT}% below the "
        "entry, graded TRADE - HIGH CONFIDENCE.",
        "Order. Bought at today's close.",
        "One position per stock.",
    )
    stop_rules = ("Where it goes. The span's lowest low minus that bar's true range, rounded down to the tick "
                  "(S1's span when both fire). It defines 1R; it does not move.",)
    target_rules = ("Entry + {NOMINAL_TARGET_R} R.",)
    exit_rules = (
        "Each session after the entry (backtest, the default bracket with `--time-stop-bars {HOLD_BARS}`):",
        "1. The stop, at its price or at the open if the stock gaps under it.",
        "2. The target, at its price or at the open if the stock gaps over it.",
        "3. The time limit: sold at the close of session {HOLD_BARS} after the entry.",
    )
    param_docs = (
        ("Setup length", "SETUP_COUNT", "Consecutive qualifying closes in a buy setup."),
        ("Setup comparison", "LOOKBACK", "Each setup close is below the close this many sessions earlier."),
        ("Countdown length", "COUNTDOWN", "S2: countdown bars to completion."),
        ("Countdown comparison", "CD_LOOKBACK", "S2: a countdown close is at or below the low this many sessions "
                                                "earlier."),
        ("Countdown window", "COUNTDOWN_WINDOW", "S2: the setup ended at most this many sessions before today."),
        ("Scan length", "SCAN_BARS", "Sessions searched for the setup and the countdown."),
        ("Perfection bar A", "PERFECT_REF_A", "S1: a setup bar whose low must be reached."),
        ("Perfection bar B", "PERFECT_REF_B", "S1: the other setup bar whose low must be reached."),
        ("Perfecting bar", "PERFECT_LATE_BAR", "S1: this setup bar or the last one must reach those lows."),
        ("Countdown reference", "CD_REF_BAR", "S2: the last countdown bar's low is at or below this countdown bar's close."),
        ("Minimum stop", "MIN_STOP_PCT", "A stop closer than this % below the entry is not bought."),
        ("Maximum stop", "MAX_STOP_PCT", "A stop further than this % below the entry is not bought."),
        ("Target", "NOMINAL_TARGET_R", "Target = entry + this × R."),
        ("Hold", "HOLD_BARS", "Sessions after the entry before the position is sold (--time-stop-bars)."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume", "The 20-day average of close × volume, at least."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
    )
    backtest_args = f"--time-stop-bars {HOLD_BARS} --rank-by setup_momentum --min-fill 0.5"

    def detect(self, ctx: StockContext, result: StrategyResult) -> None:
        d, e = ctx.daily, ctx.extras
        if len(d) < SCAN_BARS:
            return
        tail = d.iloc[-SCAN_BARS:]
        close = tail["close"].to_numpy(float)
        high = tail["high"].to_numpy(float)
        low = tail["low"].to_numpy(float)
        today = SCAN_BARS - 1
        ends = _setup_ends(close)
        e.update(level_entry=float(close[-1]))
        stop_s1 = stop_s2 = None
        # S1: a perfected setup completing today (bar k of the setup is index today - SETUP_COUNT + k)
        if len(ends) and ends[-1] == today:
            b = lambda k: today - SETUP_COUNT + k       # noqa: E731
            late = min(low[b(PERFECT_LATE_BAR)], low[b(SETUP_COUNT)])
            if late <= min(low[b(PERFECT_REF_A)], low[b(PERFECT_REF_B)]):
                span = slice(today - SETUP_COUNT + 1, today + 1)
                i = span.start + int(low[span].argmin())
                stop_s1 = float(low[i]) - _true_range(high, low, close, i)
                result.setups[S1] = True
                e.update(setup_low=float(low[i]))
        # S2: the countdown of the most recent setup completed before today
        prior = ends[(ends < today) & (ends >= today - COUNTDOWN_WINDOW)]
        if len(prior):
            j = int(prior[-1])
            setup_high = float(high[j - SETUP_COUNT + 1:j + 1].max())
            if not (close[j + 1:] > setup_high).any():
                cds = [i for i in range(j + 1, today + 1)
                       if i >= CD_LOOKBACK and close[i] <= low[i - CD_LOOKBACK]]
                e.update(countdown_count=len(cds))
                if len(cds) == COUNTDOWN and cds[-1] == today and low[today] <= close[cds[CD_REF_BAR - 1]]:
                    start = j - SETUP_COUNT + 1
                    i = start + int(low[start:today + 1].argmin())
                    stop_s2 = float(low[i]) - _true_range(high, low, close, i)
                    result.setups[S2] = True
                    e.setdefault("setup_low", float(low[i]))
        stop = stop_s1 if stop_s1 is not None else stop_s2
        if stop is not None:
            e.update(level_stop=stop)

    def levels(self, ctx, result, cfg):
        e = ctx.extras
        what = "perfected buy setup" if result.setups.get(S1) else f"buy countdown {COUNTDOWN}"
        return e["level_entry"], e["level_stop"], None, f"{what}; buy the close, DeMark's stop"
