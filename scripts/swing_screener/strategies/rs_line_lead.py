"""RS line leads price -- William O'Neil / Investor's Business Daily's relative-strength line at a new high
before the price.

IBD's charts plot the relative-strength line: the stock's price divided by the market index. A line that
reaches a new 52-week high while the price is still under its own high marks a stock already beating
the market in its base; O'Neil's followers watch for the price to follow. Daily-bar version:

  * the Near highs screen: above a 200-day that is not falling, near the 52-week high (G1-G3);
  * G4: today's RS line is the highest of the last RS_BARS sessions, today included;
  * S1: the close is still at least PRICE_LAG_MIN_PCT % under the 52-week high -- the line leads;
  * a buy-stop at the 52-week high for `expiry_bdays` sessions (the price breakout confirms); the stop is
    STOP_PCT % under the entry; sold on a close below the 50-day (`backtest_args`).

The benchmark is the market's configured benchmark (`MarketConfig.benchmark_ticker`), aligned to the
stock's sessions with only same-day or earlier values, read through the stage boundary.
"""

import numpy as np
import pandas as pd

from ..core.context import StockContext
from ..marketdata import corporate_actions
# the Near highs screen's thresholds, named here so the docs render them and the fingerprint covers them
from ..screens.criteria import (NEAR_HIGHS_MAX_PCT_BELOW_52W_HIGH, SMA200_FALLING_PCT,  # noqa: F401
                                SMA200_SLOPE_BARS)
from .base import StrategyResult
from .rs_leaders import _market_of
from .swing_base import PASS_RULE, SwingSetupStrategy

RS_BARS = 252            # G4: the RS line at its highest of this many sessions, today included
PRICE_LAG_MIN_PCT = 3    # S1: the close at least this % under its 52-week high
STOP_PCT = 8             # the stop: this % under the entry
MIN_STOP_PCT = 1.0       # a stop closer than this % below the entry is not bought
MAX_STOP_PCT = 10.0      # nor one further than this %
NOMINAL_TARGET_R = 2     # the plan's target, for the R column only (the backtest runs --no-target)

S1 = "S1"


class RsLineLeadStrategy(SwingSetupStrategy):
    key = "rs_line_lead"
    name = "RS line leads price"
    description = ("O'Neil's relative-strength line at a new 52-week high while the price is still under its "
                   "own: a buy-stop at the price's 52-week high waits for the price to follow.")
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "v1: in a Near highs stock, the RS line (close ÷ the market benchmark) at its highest of {RS_BARS} "
         "sessions while the close is {PRICE_LAG_MIN_PCT}%+ under the 52-week high; a buy-stop at that high for "
         "{expiry_bdays} sessions, stop {STOP_PCT}% under, sold on a close below the 50-day."),
    )
    behaviour = "trend_momentum"
    style = "rank"
    gate_codes = ("G1", "G2", "G3", "G4")
    screen_key = "near_highs"
    screen_gates = {"G1": "H1", "G2": "H2", "G3": "H3"}
    setup_codes = (S1,)
    setup_names = {S1: "RS line leads"}
    gate_titles = {"G1": "Above the 200-day", "G2": "200-day not falling", "G3": "Near the 52-week high",
                   "G4": "RS line at a {RS_BARS}-session high"}
    order = ""
    expiry_bdays = 15
    plan_code = "RSL"
    extra_columns = ("rs_line", "rs_vs_high_pct", "price_lag_pct", "level_entry", "level_stop")
    extra_numeric_columns = extra_columns

    _bench: dict = {}

    thesis = (
        "Leadership shows in relative performance before it shows in price: a stock whose ratio to the market "
        "reaches a new high while its price is still basing has been falling less and rising more than the "
        "market, the footprint of persistent buying. William O'Neil and *Investor's Business Daily* made the "
        "RS line at a new high ahead of the price one of their signature tells. The catalogue grades it D (the "
        "publisher's examples; no published test of the rule alone), credibility 2."
    )
    how_it_works = (
        "**Qualify (the Near highs screen).** The close is above the 200-day average (G1), the 200-day is not "
        "falling (G2), and the close is within {NEAR_HIGHS_MAX_PCT_BELOW_52W_HIGH}% of the 52-week high (G3).",
        "**The RS line (G4).** Each session, the stock's close divided by the market benchmark's close on that "
        "date (the S&P 500 ETF in the US, the Nifty 500 in India; a benchmark date missing from the stock's "
        "calendar takes the benchmark's latest earlier close). Today's value is the highest of the last "
        "{RS_BARS} sessions, today included.",
        "**The line leads (S1).** Today's close is still at least {PRICE_LAG_MIN_PCT}% under the 52-week high "
        "(the highest high of the last 252 sessions): the ratio has broken out, the price has not.",
        "**The order.** A buy-stop at the 52-week high for the next {expiry_bdays} sessions: the price breakout "
        "confirms the line. It fills when a session trades through it, at the open if one gaps above; an order "
        "whose stop is hit first is cancelled.",
        "**Stop and exit.** The stop is {STOP_PCT}% under the entry. No target: the position is sold on a close "
        "below the 50-day average, or at the stop.",
    )
    caveats = (
        "**IBD's line uses the S&P 500 for every stock.** Here each market's own benchmark is used, so an Indian "
        "stock is measured against the Nifty 500.",
        "**The sell rules are a stand-in.** O'Neil sells at 20-25% profit, on climax signs or a break of the "
        "50-day on heavy volume, by judgement; a close below the 50-day is this backtest's single rule.",
        "**No base-quality test.** O'Neil wants the line's new high inside a proper base; the Near highs screen "
        "and the {PRICE_LAG_MIN_PCT}% lag are this version's proxy.",
        "**Run it with its exit flags** (`backtest_args`); the default bracket would sell at the nominal target.",
        corporate_actions.CAVEAT_TRADED,
    )
    status = ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (rank group, grade D, "
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
        "G4": ("The RS line at a new high.\n\n- **Test:** today's close ÷ the benchmark's close is at least its "
               "value on each of the last {RS_BARS} sessions.\n- **Fails:** a lower line, no stored benchmark, or "
               "too little shared history."),
    }
    watch_docs: dict = {}
    setup_docs = {
        S1: ("RS line leads.\n\n- **Test:** today's close is at least {PRICE_LAG_MIN_PCT}% under the 52-week "
             "high.\n- **Signal:** a buy-stop at the 52-week high for {expiry_bdays} sessions; the stop is "
             "{STOP_PCT}% under it."),
    }
    entry_rules = (
        "Signal. G1-G4 and S1 on today's close, with a stop between {MIN_STOP_PCT}% and {MAX_STOP_PCT}% below the "
        "entry, graded TRADE - HIGH CONFIDENCE.",
        "Order. A buy-stop at the 52-week high for {expiry_bdays} sessions (backtest: fills when a session's high "
        "reaches it, at the open if it gaps above).",
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
        ("RS window", "RS_BARS", "G4: sessions, today included, whose highest RS line today must match."),
        ("Price lag", "PRICE_LAG_MIN_PCT", "S1: the close under its 52-week high, %, at least."),
        ("Order life", "expiry_bdays", "Sessions the buy-stop at the 52-week high stays open."),
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

    @classmethod
    def _bench_arrays(cls, market_key: str):
        """(dates as int64 ns, closes) of the market's benchmark, or None. Cached per market AND stage
        boundary: the loader honours the boundary, so a cache keyed on the market alone would hand an
        optimise run's series to a full run in the same process."""
        from ..config import MARKETS
        from ..marketdata import asof, cache
        key = (market_key, asof.end_date())
        if key not in cls._bench:
            b = cache.load_cached(market_key, MARKETS[market_key].benchmark_ticker)
            if b is None or b.empty:
                cls._bench[key] = None
            else:
                c = b["close"].astype(float).dropna().sort_index()
                cls._bench[key] = (pd.DatetimeIndex(c.index).tz_localize(None).asi8
                                   if pd.DatetimeIndex(c.index).tz is not None
                                   else pd.DatetimeIndex(c.index).asi8, c.to_numpy())
        return cls._bench[key]

    def detect(self, ctx: StockContext, result: StrategyResult) -> None:
        d, e = ctx.daily, ctx.extras
        if len(d) < RS_BARS:
            result.fail("G4", "insufficient history")
            return
        bench = self._bench_arrays(_market_of(ctx.symbol))
        close = float(d["close"].iloc[-1])
        h252 = float(d["high_252"].iloc[-1])
        lag = (1 - close / h252) * 100 if h252 > 0 else float("nan")
        e.update(price_lag_pct=lag, level_entry=h252, level_stop=h252 * (1 - STOP_PCT / 100))
        result.setups[S1] = bool(lag >= PRICE_LAG_MIN_PCT)
        if bench is None:
            result.fail("G4", "no stored benchmark")
            return
        idx = pd.DatetimeIndex(d.index[-RS_BARS:])
        days = (idx.tz_localize(None) if idx.tz is not None else idx).asi8
        bdays, bclose = bench
        pos = np.searchsorted(bdays, days, side="right") - 1      # the benchmark's close on or before each date
        if pos[0] < 0:
            result.fail("G4", "benchmark history starts too late")
            return
        rs = d["close"].astype(float).to_numpy()[-RS_BARS:] / bclose[pos]
        top = float(np.nanmax(rs))
        e.update(rs_line=float(rs[-1]), rs_vs_high_pct=(rs[-1] / top - 1) * 100)
        if rs[-1] >= top:
            result.ok("G4", f"RS line at its {RS_BARS}-session high")
        else:
            result.fail("G4", f"RS line {(1 - rs[-1] / top) * 100:.1f}% under its {RS_BARS}-session high")

    def levels(self, ctx, result, cfg):
        e = ctx.extras
        return e["level_entry"], e["level_stop"], None, (
            f"RS line at a new high, price {e['price_lag_pct']:.1f}% under its 52-week high {e['level_entry']:.2f}")
