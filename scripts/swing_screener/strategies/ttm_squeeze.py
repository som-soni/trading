"""TTM squeeze -- John Carter's squeeze fire (Mastering the Trade, 2005).

Carter's squeeze is on while the Bollinger bands sit inside the Keltner channel: volatility so compressed
that two standard deviations span less than one and a half average ranges. It "fires" on the first bar
the bands move back outside the channel, and he trades in the direction of his momentum histogram. The
long half, daily-bar version:

  * the close is above the 200-day;
  * G2: the squeeze was on for at least MIN_SQUEEZE_BARS consecutive sessions ending yesterday;
  * S1: today it is off, and the momentum histogram is above zero and rising;
  * buy that close; the stop is STOP_ATR ATR14 under it; the stop trails TRAIL_ATR ATR14 under the highest
    close with a HOLD_BARS-session time limit (`backtest_args`).
"""

import numpy as np

from ..core.context import StockContext
from ..marketdata import corporate_actions
from .base import StrategyResult
from .swing_base import PASS_RULE, SwingSetupStrategy

LEN = 20                 # the bands', the channel's and the histogram's length, in sessions
BB_SD = 2                # Bollinger bands: the 20-day average ± this many 20-day standard deviations of the close
KC_ATR = 1.5             # Keltner channel: the 20-day average ± this many 20-day ATRs
MIN_SQUEEZE_BARS = 5     # G2: the squeeze was on for at least this many consecutive sessions ending yesterday
STOP_ATR = 2             # the stop: this many ATR14 under the entry
MIN_STOP_PCT = 1.0       # a stop closer than this % below the entry is not bought
MAX_STOP_PCT = 15.0      # nor one further than this %
NOMINAL_TARGET_R = 2     # the plan's target, for the R column only (the backtest runs --no-target)
TRAIL_ATR = 2            # backtest_args: the stop trails this many ATR14 under the highest close
HOLD_BARS = 10           # backtest_args: sold at the close of this session after the entry

S1 = "S1"


def _windows(a: np.ndarray, n: int) -> np.ndarray:
    return np.lib.stride_tricks.sliding_window_view(a, n)


def _linreg_last(y: np.ndarray) -> np.ndarray:
    """Each row's least-squares line, evaluated at the row's last point."""
    n = y.shape[-1]
    i = np.arange(n) - (n - 1) / 2
    ybar = y.mean(axis=-1)
    slope = ((y - ybar[..., None]) * i).sum(axis=-1) / (i * i).sum()
    return ybar + slope * (n - 1) / 2


class TtmSqueezeStrategy(SwingSetupStrategy):
    key = "ttm_squeeze"
    name = "TTM squeeze"
    description = ("Carter's squeeze fire: after the Bollinger bands have sat inside the Keltner channel, buy "
                   "the close of the first session they move outside it with momentum up.")
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "v1: the long half of Carter's TTM squeeze above the 200-day -- Bollinger bands ({BB_SD} SD) inside a "
         "{KC_ATR}-ATR Keltner channel for {MIN_SQUEEZE_BARS}+ sessions, then the first session outside with "
         "the momentum histogram above zero and rising, bought at the close; stop {STOP_ATR} ATR14 under, "
         "trailing {TRAIL_ATR} ATR14, sold at the close of session {HOLD_BARS}."),
    )
    behaviour = "trend_momentum"
    style = "squeeze"
    gate_codes = ("G1", "G2")
    screen_key = "above_200"
    screen_gates = {"G1": "A1"}
    setup_codes = (S1,)
    setup_names = {S1: "Squeeze fires long"}
    gate_titles = {"G1": "Above the 200-day", "G2": "Squeeze on {MIN_SQUEEZE_BARS}+ sessions"}
    order = "close"
    plan_code = "TTM"
    extra_columns = ("squeeze_bars", "bb_kc_ratio", "momentum", "momentum_prev", "level_entry", "level_stop")
    extra_numeric_columns = extra_columns

    thesis = (
        "When volatility compresses so far that the Bollinger bands fit inside the Keltner channel, the market "
        "is storing energy; the release, as the bands push back outside, tends to start a move worth trading, "
        "and a momentum reading tells its direction. John Carter, *Mastering the Trade* (2005), made the TTM "
        "squeeze a staple of retail charting. The catalogue grades it D (the book's examples; no published "
        "test), credibility 1."
    )
    how_it_works = (
        "**The squeeze.** The Bollinger bands are the {LEN}-day simple average of the close ± {BB_SD} {LEN}-day "
        "standard deviations; the Keltner channel is the same average ± {KC_ATR} × the {LEN}-day ATR, here the "
        "simple mean of the true range over {LEN} sessions (not Wilder's smoothing). They share a middle, so the "
        "squeeze is on when {BB_SD} standard deviations are less than {KC_ATR} ATRs.",
        "**Universe and trend (G1).** Every liquid stock whose close is above its 200-day average. Carter trades "
        "the fire in either direction; this is the long half only, inside the long-term uptrend, so the Above "
        "the 200-day screen's A1 is a hard gate.",
        "**Compression (G2).** The squeeze was on for at least {MIN_SQUEEZE_BARS} consecutive sessions ending "
        "yesterday.",
        "**The fire (S1).** Today the squeeze is off, and Carter's momentum histogram is above zero and above "
        "yesterday's value. The histogram: each session, the close minus the average of (the midpoint of the "
        "{LEN}-day highest high and lowest low) and the {LEN}-day average; then the value, at its last point, of "
        "the least-squares line through the last {LEN} of those.",
        "**Buy, stop, exit.** Buy today's close; the stop is {STOP_ATR} ATR14 under it. No target: the stop "
        "trails {TRAIL_ATR} ATR14 under the highest close, and the position is sold at the close of session "
        "{HOLD_BARS} after the entry.",
    )
    caveats = (
        "**Long half only.** Carter shorts a fire with falling momentum as readily; only the long side is tested, "
        "inside the 200-day uptrend.",
        "**The exit is a stand-in.** Carter sells when the histogram prints two falling bars in a row; the "
        "{TRAIL_ATR}-ATR trailing stop and the {HOLD_BARS}-session limit are this backtest's version.",
        "**ATR definition.** The channel's {LEN}-day ATR is a simple mean of the true range; charting packages "
        "vary (some use Wilder's smoothing, some the high − low range), which moves the edge of the squeeze a "
        "little. The bands use the sample standard deviation.",
        "**Run it with its exit flags** (`backtest_args`); the default bracket would sell at the nominal target.",
        corporate_actions.CAVEAT_TRADED,
    )
    status = ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (squeeze group, grade D, "
              "credibility 1); optimise-stage runs queued in both markets. " + PASS_RULE)
    gate_docs = {
        "G1": ("The close is above the 200-day simple average (the Above the 200-day screen's A1).\n\n"
               "- **Fails:** a close at or below it, or no 200-day yet."),
        "G2": ("The squeeze was on.\n\n- **Test:** on each of the {MIN_SQUEEZE_BARS} sessions ending yesterday, "
               "{BB_SD} × the {LEN}-day standard deviation of the close was less than {KC_ATR} × the {LEN}-day "
               "ATR (the bands inside the channel).\n- **Fails:** a shorter squeeze, none, or too little history."),
    }
    watch_docs: dict = {}
    setup_docs = {
        S1: ("The squeeze fires long.\n\n- **Test:** today the bands are back outside the channel ({BB_SD} SD at "
             "or above {KC_ATR} ATR), and the momentum histogram is above zero and above yesterday's value.\n"
             "- **Signal:** buy today's close; the stop is {STOP_ATR} ATR14 under it."),
    }
    entry_rules = (
        "Signal. G1, G2 and S1 on today's close, with a stop between {MIN_STOP_PCT}% and {MAX_STOP_PCT}% below the "
        "entry, graded TRADE - HIGH CONFIDENCE.",
        "Order. Bought at today's close.",
        "One position per stock.",
    )
    stop_rules = (
        "Where it goes. The entry − {STOP_ATR} × ATR14, rounded down to the tick. It defines 1R.",
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
        ("Length", "LEN", "Sessions for the average, the standard deviation, the ATR and the histogram."),
        ("Band width", "BB_SD", "Standard deviations of the close either side of the average (Bollinger)."),
        ("Channel width", "KC_ATR", "ATRs either side of the average (Keltner)."),
        ("Squeeze length", "MIN_SQUEEZE_BARS", "G2: consecutive squeeze sessions, at least, ending yesterday."),
        ("Stop distance", "STOP_ATR", "ATR14 multiples between the entry and the initial stop."),
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
        n = 2 * LEN + MIN_SQUEEZE_BARS + 1          # enough for the ATR and the histogram on the bars we read
        if len(d) < n:
            result.fail("G2", "insufficient history")
            return
        hi = d["high"].astype(float).to_numpy()[-n:]
        lo = d["low"].astype(float).to_numpy()[-n:]
        cl = d["close"].astype(float).to_numpy()[-n:]
        sd = d["close_sd20"].astype(float).to_numpy()[-n:]
        tr = np.maximum(hi[1:], cl[:-1]) - np.minimum(lo[1:], cl[:-1])     # aligned to bars 1..n-1
        atr20 = _windows(tr, LEN).mean(axis=1)                              # aligned to bars LEN..n-1
        m = len(atr20)                                                      # every bar with an ATR (the run is counted up to m − 1)
        ratio = (BB_SD * sd[-m:]) / (KC_ATR * atr20[-m:])
        on = ratio < 1
        run = 0
        for v in on[-2::-1]:
            if not v:
                break
            run += 1
        # the histogram on today and yesterday
        hh = _windows(hi, LEN).max(axis=1)
        ll = _windows(lo, LEN).min(axis=1)
        sma = _windows(cl, LEN).mean(axis=1)
        x = cl[LEN - 1:] - ((hh + ll) / 2 + sma) / 2                        # aligned to bars LEN-1..n-1
        mom = _linreg_last(_windows(x[-LEN - 1:], LEN))                     # yesterday, today
        atr14 = float(d["atr14"].iloc[-1])
        e.update(squeeze_bars=run, bb_kc_ratio=float(ratio[-1]), momentum=float(mom[-1]),
                 momentum_prev=float(mom[-2]), level_entry=float(cl[-1]), level_stop=float(cl[-1]) - STOP_ATR * atr14)
        if run >= MIN_SQUEEZE_BARS:
            result.ok("G2", f"squeeze on {run} sessions to yesterday")
        else:
            result.fail("G2", f"squeeze on only {run} sessions to yesterday (< {MIN_SQUEEZE_BARS})")
        result.setups[S1] = bool(not on[-1] and mom[-1] > 0 and mom[-1] > mom[-2])

    def levels(self, ctx, result, cfg):
        e = ctx.extras
        return e["level_entry"], e["level_stop"], None, (
            f"squeeze fired after {e['squeeze_bars']} sessions, momentum {e['momentum']:.2f} rising")
