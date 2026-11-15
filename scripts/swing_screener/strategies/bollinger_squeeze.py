"""Bollinger squeeze -- John Bollinger's "Squeeze" (Bollinger on Bollinger Bands, 2001).

Bollinger's BandWidth -- the distance between the bands as a fraction of the middle band -- falls when
volatility contracts, and a six-month low in BandWidth (the Squeeze) tends to precede a volatility
expansion. The long half, daily-bar version:

  * the close is above the 200-day;
  * G2: BandWidth made its lowest of SQUEEZE_LOOKBACK sessions on some session within the SQUEEZE_RECENT
    sessions before today;
  * S1: today closes above the upper band and yesterday did not -- the expansion breakout;
  * buy that close; the stop is the lower band; sold on a close below the middle band (`backtest_args`).
"""

import numpy as np

from ..core.context import StockContext
from ..marketdata import corporate_actions
from .base import StrategyResult
from .swing_base import PASS_RULE, SwingSetupStrategy

BB_SD = 2                # the bands sit this many 20-day standard deviations either side of the 20-day average
SQUEEZE_LOOKBACK = 125   # G2: BandWidth at its lowest of this many sessions (about six months) …
SQUEEZE_RECENT = 5       # … on some session within this many sessions before today
MIN_STOP_PCT = 1.0       # a stop closer than this % below the entry is not bought
MAX_STOP_PCT = 15.0      # nor one further than this %
NOMINAL_TARGET_R = 2     # the plan's target, for the R column only (the backtest runs --no-target)

S1 = "S1"
W1 = "W1"


class BollingerSqueezeStrategy(SwingSetupStrategy):
    key = "bollinger_squeeze"
    name = "Bollinger squeeze"
    description = ("Bollinger's Squeeze: after BandWidth falls to a six-month low, buy the first close above the "
                   "upper band; sell on a close below the middle band.")
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "v1: the long half of Bollinger's Squeeze above the 200-day -- BandWidth at its lowest of "
         "{SQUEEZE_LOOKBACK} sessions within the {SQUEEZE_RECENT} before today, then the first close above the "
         "upper band, bought at the close; stop at the lower band, sold on a close below the 20-day average."),
    )
    behaviour = "trend_momentum"
    style = "squeeze"
    gate_codes = ("G1", "G2")
    screen_key = "above_200"
    screen_gates = {"G1": "A1"}
    watch_codes = (W1,)
    setup_codes = (S1,)
    setup_names = {S1: "Squeeze breakout"}
    gate_titles = {"G1": "Above the 200-day", "G2": "Recent squeeze"}
    order = "close"
    plan_code = "BB"
    extra_columns = ("bandwidth", "squeeze_low_bw", "squeeze_age", "upper_band", "vol_vs_avg", "level_entry",
                     "level_stop")
    extra_numeric_columns = extra_columns

    thesis = (
        "Volatility is cyclical: periods of low volatility are followed by high volatility. When the Bollinger "
        "bands narrow to their tightest in six months, a large move is likely to follow, and the first close "
        "outside the bands points its direction. John Bollinger, *Bollinger on Bollinger Bands* (2001), names "
        "this the Squeeze. The catalogue grades it D (the book's examples; no published test of the rule as a "
        "system), credibility 1."
    )
    how_it_works = (
        "**The bands.** The middle band is the 20-day simple average of the close; the upper and lower bands sit "
        "{BB_SD} 20-day standard deviations of the close above and below it. BandWidth = (upper − lower) ÷ "
        "middle.",
        "**Universe and trend (G1).** Every liquid stock whose close is above its 200-day average. Bollinger "
        "trades the Squeeze in either direction; this is the long half only, and a long-only breakout needs the "
        "long-term uptrend behind it, so the Above the 200-day screen's A1 is a hard gate.",
        "**The squeeze (G2).** On some session within the {SQUEEZE_RECENT} sessions before today, BandWidth was "
        "the lowest of the {SQUEEZE_LOOKBACK} sessions ending that session.",
        "**The breakout (S1).** Today closes above the upper band and yesterday closed at or under its upper "
        "band. Buy at today's close.",
        "**Volume (W1).** Bollinger wants volume to confirm the break; today's volume under its 50-day average is "
        "flagged, never blocking.",
        "**Stop and exit.** The stop is the lower band at today's close. No target: the position is sold on a "
        "close below the middle band (the 20-day average), or at the stop.",
    )
    caveats = (
        "**Long half only.** Bollinger trades a downside break of the Squeeze as readily as an upside one; only "
        "the upside is tested, inside the 200-day uptrend.",
        "**The head fake is not modelled.** Bollinger warns that the first break out of a Squeeze often fails "
        "and reverses into the real move; the rule buys the first break and lets the stop take the failures.",
        "**The exit is a stand-in.** Bollinger leaves the exit to the trader (a parabolic stop, a tag of the "
        "opposite band); a close below the middle band is this backtest's version.",
        "**Standard deviation.** The bands use the sample standard deviation of the last 20 closes; Bollinger's "
        "uses the population one, a band about 2.5% wider. The difference rarely changes which day breaks out.",
        "**Run it with its exit flags** (`backtest_args`); the default bracket would sell at the nominal target.",
        corporate_actions.CAVEAT_TRADED,
    )
    status = ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (squeeze group, grade D, "
              "credibility 1); optimise-stage runs queued in both markets. " + PASS_RULE)
    gate_docs = {
        "G1": ("The close is above the 200-day simple average (the Above the 200-day screen's A1).\n\n"
               "- **Fails:** a close at or below it, or no 200-day yet."),
        "G2": ("A recent squeeze.\n\n- **Test:** on at least one of the {SQUEEZE_RECENT} sessions before today, "
               "BandWidth was at or below every BandWidth of the {SQUEEZE_LOOKBACK} sessions ending that session."
               "\n- **Fails:** no six-month low in BandWidth that recently, or too little history."),
    }
    watch_docs = {
        W1: ("Unconfirmed by volume.\n\n- **Test:** today's volume is under its 50-day average.\n\nNoted, never "
             "blocking: Bollinger asks for volume confirmation but gives no threshold."),
    }
    setup_docs = {
        S1: ("Squeeze breakout.\n\n- **Test:** today's close is above the upper band and yesterday's close was at "
             "or under yesterday's upper band.\n- **Signal:** buy today's close; the stop is today's lower band."),
    }
    entry_rules = (
        "Signal. G1, G2 and S1 on today's close, with a stop between {MIN_STOP_PCT}% and {MAX_STOP_PCT}% below the "
        "entry, graded TRADE - HIGH CONFIDENCE.",
        "Order. Bought at today's close.",
        "One position per stock.",
    )
    stop_rules = ("Where it goes. The lower band at today's close (the 20-day average − {BB_SD} standard "
                  "deviations), rounded down to the tick. It defines 1R and does not move.",)
    target_rules = ("No target. The plan's target is entry + {NOMINAL_TARGET_R} R for the R column only; the "
                    "backtest runs with `--no-target`.",)
    exit_rules = (
        "Each session after the entry (backtest, `--exit-mode ma --ma-col sma20 --no-target`):",
        "1. The stop, at its price or at the open if the stock gaps under it.",
        "2. A close below the 20-day simple average (the middle band): sold at that close.",
    )
    param_docs = (
        ("Band width", "BB_SD", "Standard deviations of the close between the middle band and each outer band."),
        ("Squeeze lookback", "SQUEEZE_LOOKBACK", "G2: sessions whose lowest BandWidth marks a squeeze."),
        ("Squeeze recency", "SQUEEZE_RECENT", "G2: sessions before today within which the squeeze must fall."),
        ("Minimum stop", "MIN_STOP_PCT", "A stop closer than this % below the entry is not bought."),
        ("Maximum stop", "MAX_STOP_PCT", "A stop further than this % below the entry is not bought."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × R, for the R column only."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume", "The 20-day average of close × volume, at least."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
    )
    backtest_args = "--exit-mode ma --ma-col sma20 --no-target --rank-by setup_momentum --min-fill 0.5"

    def detect(self, ctx: StockContext, result: StrategyResult) -> None:
        d, e = ctx.daily, ctx.extras
        n = SQUEEZE_LOOKBACK + SQUEEZE_RECENT
        if len(d) < n + 1:
            result.fail("G2", "insufficient history")
            return
        mid = d["sma20"].astype(float).to_numpy()[-n - 1:]
        sd = d["close_sd20"].astype(float).to_numpy()[-n - 1:]
        close = d["close"].astype(float).to_numpy()[-2:]
        bw = 2 * BB_SD * sd / mid
        upper = mid + BB_SD * sd
        lower_t = float(mid[-1] - BB_SD * sd[-1])
        # the SQUEEZE_RECENT sessions before today: indices -2 .. -1-SQUEEZE_RECENT of the n+1 window
        age, low_bw = None, float("nan")
        for k in range(1, SQUEEZE_RECENT + 1):
            j = len(bw) - 1 - k
            win = bw[j - SQUEEZE_LOOKBACK + 1:j + 1]
            if np.isfinite(win).all() and bw[j] <= win.min():
                age, low_bw = k, float(bw[j])
                break
        vol, vavg = float(d["volume"].iloc[-1]), d["vol_sma50"].iloc[-1]
        vol_vs = vol / float(vavg) if vavg == vavg and vavg else float("nan")
        e.update(bandwidth=float(bw[-1]), squeeze_low_bw=low_bw, squeeze_age=age if age else float("nan"),
                 upper_band=float(upper[-1]), vol_vs_avg=vol_vs, level_entry=float(close[-1]), level_stop=lower_t)
        if age:
            result.ok("G2", f"BandWidth {low_bw:.4f} a {SQUEEZE_LOOKBACK}-session low {age} sessions ago")
        else:
            result.fail("G2", f"no {SQUEEZE_LOOKBACK}-session BandWidth low in the last {SQUEEZE_RECENT} sessions")
        low_vol = bool(vol_vs == vol_vs and vol_vs < 1)
        result.watch_flags[W1] = low_vol
        if low_vol:
            result.watch_notes[W1] = f"volume {vol_vs:.2f}× its 50-day average"
        result.setups[S1] = bool(close[-1] > upper[-1] and close[-2] <= upper[-2])

    def levels(self, ctx, result, cfg):
        e = ctx.extras
        return e["level_entry"], e["level_stop"], None, (
            f"close above the upper band {e['upper_band']:.2f} after a squeeze; stop at the lower band")
