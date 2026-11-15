"""Pocket pivot -- Gil Morales & Chris Kacher's early entry inside a base (Trade Like an O'Neil Disciple,
2010).

Morales and Kacher buy a leading stock before its breakout, on an up day whose volume swamps every down
day's volume of the past two weeks: institutions buying quietly inside the base. Daily-bar version:

  * the Near highs screen: above a 200-day that is not falling, near the 52-week high (G1-G3);
  * G4: the close is above the 50-day average;
  * S1: today is an up day whose volume exceeds the highest volume of any down day among the PP_BARS
    sessions before today, closing above its 10-day simple average and no more than MAX_EXT_PCT % above it;
  * buy that close; the stop is STOP_PCT % under it; sold on a close below the 50-day (`backtest_args`).
"""

import numpy as np

from ..core.context import StockContext
from ..marketdata import corporate_actions
# the Near highs screen's thresholds, named here so the docs render them and the fingerprint covers them
from ..screens.criteria import (NEAR_HIGHS_MAX_PCT_BELOW_52W_HIGH, SMA200_FALLING_PCT,  # noqa: F401
                                SMA200_SLOPE_BARS)
from .base import StrategyResult
from .swing_base import PASS_RULE, SwingSetupStrategy

PP_BARS = 10             # S1: today's volume beats every down day's volume among this many sessions before today
SMA_SHORT = 10           # S1: the close is above its SMA_SHORT-day simple average …
MAX_EXT_PCT = 5          # … and no more than this % above it (not extended)
STOP_PCT = 8             # the stop: this % under the entry
MIN_STOP_PCT = 1.0       # a stop closer than this % below the entry is not bought
MAX_STOP_PCT = 10.0      # nor one further than this %
NOMINAL_TARGET_R = 2     # the plan's target, for the R column only (the backtest runs --no-target)

S1 = "S1"


class PocketPivotStrategy(SwingSetupStrategy):
    key = "pocket_pivot"
    name = "Pocket pivot"
    description = ("Morales & Kacher's pocket pivot: in a leader near its highs, an up day whose volume beats "
                   "every down day of the past two weeks, bought at the close while still near the 10-day.")
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "v1: the pocket pivot in a Near highs stock above its 50-day -- an up day on more volume than any down "
         "day of the {PP_BARS} sessions before, closing 0-{MAX_EXT_PCT}% above the {SMA_SHORT}-day; bought at the "
         "close, stop {STOP_PCT}% under, sold on a close below the 50-day."),
    )
    behaviour = "trend_momentum"
    style = "breakout"
    gate_codes = ("G1", "G2", "G3", "G4")
    screen_key = "near_highs"
    screen_gates = {"G1": "H1", "G2": "H2", "G3": "H3"}
    setup_codes = (S1,)
    setup_names = {S1: "Pocket pivot"}
    gate_titles = {"G1": "Above the 200-day", "G2": "200-day not falling", "G3": "Near the 52-week high",
                   "G4": "Above the 50-day"}
    order = "close"
    plan_code = "PPV"
    extra_columns = ("vol_vs_down_max", "ext_vs_sma10_pct", "up_pct", "level_entry", "level_stop")
    extra_numeric_columns = extra_columns

    thesis = (
        "Institutions build positions over days and cannot hide their size: an up day whose volume dwarfs every "
        "recent down day's volume shows demand stepping in while the stock is still inside its base, before the "
        "breakout crowd arrives, and buying there gives a lower-risk entry than the breakout itself. Gil Morales "
        "& Chris Kacher, *Trade Like an O'Neil Disciple* (2010), named it the pocket pivot. The catalogue grades "
        "it D (the authors' own trading record and examples; no published test), credibility 2."
    )
    how_it_works = (
        "**Qualify (the Near highs screen).** The close is above the 200-day average (G1), the 200-day is not "
        "falling (G2), and the close is within {NEAR_HIGHS_MAX_PCT_BELOW_52W_HIGH}% of the 52-week high (G3): the "
        "authors buy pocket pivots only in leading stocks in an uptrend.",
        "**Constructive (G4).** The close is above the 50-day average.",
        "**The pocket pivot (S1).** Today closes above yesterday's close, on more volume than the heaviest down "
        "day (a close under its own prior close) among the {PP_BARS} sessions before today -- when there was no "
        "down day, any up day passes the volume test. Today's close is above its {SMA_SHORT}-day simple average "
        "and no more than {MAX_EXT_PCT}% above it: not extended.",
        "**Buy, stop, exit.** Buy today's close; the stop is {STOP_PCT}% under it. No target: the position is "
        "sold on a close below the 50-day average, or at the stop.",
    )
    caveats = (
        "**The book's sell rules are discretionary.** Morales and Kacher sell on a violation of the 10-day or "
        "50-day line judged by the stock's character, and into climactic strength; a close below the 50-day "
        "is this backtest's single stand-in.",
        "**No base-quality test.** The authors buy pocket pivots out of a constructive base, judged by eye; "
        "the Near highs screen and the 50-day are this version's proxy.",
        "**A fixed {STOP_PCT}% stop.** The book allows a tighter stop under the pocket pivot's low; the "
        "O'Neil-style percentage cut is used so every trade risks the same distance.",
        "**Run it with its exit flags** (`backtest_args`); the default bracket would sell at the nominal target.",
        corporate_actions.CAVEAT_TRADED,
    )
    status = ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (breakout group, grade D, "
              "credibility 2); optimise-stage runs queued in both markets. " + PASS_RULE)
    gate_docs = {
        "G1": ("The close is above the 200-day simple average (the Near highs screen's H1).\n\n"
               "- **Fails:** a close at or below it, or no 200-day yet."),
        "G2": ("The 200-day is not falling (the Near highs screen's H2).\n\n"
               "- **Test:** it is not more than {SMA200_FALLING_PCT}% below its value {SMA200_SLOPE_BARS} sessions "
               "ago."),
        "G3": ("Near the highs (the Near highs screen's H3).\n\n"
               "- **Test:** the close is within {NEAR_HIGHS_MAX_PCT_BELOW_52W_HIGH}% of the 52-week high (the "
               "highest high of the last 252 sessions, today included)."),
        "G4": ("Above the 50-day.\n\n- **Test:** today's close is above the 50-day simple average.\n"
               "- **Fails:** a close at or below it, or no 50-day yet."),
    }
    watch_docs: dict = {}
    setup_docs = {
        S1: ("Pocket pivot.\n\n- **Test:** today's close is above yesterday's; today's volume is above the "
             "highest volume of any down day among the {PP_BARS} sessions before today; and today's close is "
             "above its {SMA_SHORT}-day simple average by at most {MAX_EXT_PCT}%.\n- **Signal:** buy today's "
             "close; the stop is {STOP_PCT}% under it."),
    }
    entry_rules = (
        "Signal. G1-G4 and S1 on today's close, with a stop between {MIN_STOP_PCT}% and {MAX_STOP_PCT}% below the "
        "entry, graded TRADE - HIGH CONFIDENCE.",
        "Order. Bought at today's close.",
        "One position per stock.",
    )
    stop_rules = ("Where it goes. The entry × (1 − {STOP_PCT}%), rounded down to the tick. It defines 1R and does "
                  "not move.",)
    target_rules = ("No target. The plan's target is entry + {NOMINAL_TARGET_R} R for the R column only; the "
                    "backtest runs with `--no-target`.",)
    exit_rules = (
        "Each session after the entry (backtest, `--exit-mode ma --ma-col sma50 --no-target`):",
        "1. The stop, at its price or at the open if the stock gaps under it.",
        "2. A close below the 50-day simple average: sold at that close.",
    )
    param_docs = (
        ("Near-high ceiling", "NEAR_HIGHS_MAX_PCT_BELOW_52W_HIGH", "G3: how far below the 52-week high, %, at "
                                                                   "most (the Near highs screen's)."),
        ("200-day falling", "SMA200_FALLING_PCT", "G2: the 200-day fails if this % below its earlier value."),
        ("200-day slope window", "SMA200_SLOPE_BARS", "G2: sessions back for that comparison."),
        ("Down-day window", "PP_BARS", "S1: sessions before today whose down-day volumes today must beat."),
        ("Short average", "SMA_SHORT", "S1: the simple average the close must be above."),
        ("Extension", "MAX_EXT_PCT", "S1: the close above that average, %, at most."),
        ("Stop", "STOP_PCT", "The stop, % under the entry."),
        ("Minimum stop", "MIN_STOP_PCT", "A stop closer than this % below the entry is not bought."),
        ("Maximum stop", "MAX_STOP_PCT", "A stop further than this % below the entry is not bought."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × R, for the R column only."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume", "The 20-day average of close × volume, at least."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
    )
    backtest_args = "--exit-mode ma --ma-col sma50 --no-target --rank-by setup_momentum --min-fill 0.5"

    def detect(self, ctx: StockContext, result: StrategyResult) -> None:
        d, e = ctx.daily, ctx.extras
        n = max(PP_BARS, SMA_SHORT) + 2
        if len(d) < n:
            result.fail("G4", "insufficient history")
            return
        cl = d["close"].astype(float).to_numpy()[-n:]
        vol = d["volume"].astype(float).to_numpy()[-n:]
        close = float(cl[-1])
        s50 = d["sma50"].iloc[-1]
        if s50 == s50 and close > float(s50):
            result.ok("G4", f"close {close:.2f} above the 50-day {float(s50):.2f}")
        else:
            result.fail("G4", "close not above the 50-day")
        prior_cl, prior_prev = cl[-PP_BARS - 1:-1], cl[-PP_BARS - 2:-2]
        down_vol = vol[-PP_BARS - 1:-1][prior_cl < prior_prev]
        down_max = float(down_vol.max()) if len(down_vol) else 0.0
        sma10 = float(np.mean(cl[-SMA_SHORT:]))
        ext = (close / sma10 - 1) * 100
        up = (close / cl[-2] - 1) * 100
        e.update(vol_vs_down_max=vol[-1] / down_max if down_max > 0 else float("nan"), ext_vs_sma10_pct=ext,
                 up_pct=up, level_entry=close, level_stop=close * (1 - STOP_PCT / 100))
        result.setups[S1] = bool(close > cl[-2] and vol[-1] > down_max and 0 < ext <= MAX_EXT_PCT)

    def levels(self, ctx, result, cfg):
        e = ctx.extras
        return e["level_entry"], e["level_stop"], None, (
            f"pocket pivot: up {e['up_pct']:.1f}% on volume above every recent down day, "
            f"{e['ext_vs_sma10_pct']:.1f}% over the {SMA_SHORT}-day")
