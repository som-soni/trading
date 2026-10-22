"""Relative-strength leaders — the strongest stocks in the strongest groups, after a correction.

The Learn guide "Relative-strength leaders" as rules. O'Neil's and Minervini's idea: the next
advance is led by the stocks that held up during the fall, so after a correction confirms, buy
those breaking out of a flat base.

What this strategy does NOT do itself, because a one-symbol evaluation cannot: the RS RANK (80+
across the market) and the GROUP rank (top 20% of industries) are cross-sectional, and the
backtest applies them to the collected signals (`--min-rs`, `--min-group-rs`). The gates here are
the per-stock half.
"""
from __future__ import annotations

import pandas as pd

from ..config.base import MarketConfig
from ..core.context import StockContext
from .base import (LABELS, Decision, PlanChoice, Strategy, StrategyResult, TradePlan,
                   tradable_point_in_time)
from .trend_pullback import round_tick

RSL01 = "S1"   # breakout through the flat base's pivot

# ---- the market condition (guide §3): trade only in a confirmed recovery
CORRECTION_PCT = 10.0        # the index must have fallen this far from its high, closing basis
REBOUND_PCT = 5.0            # and risen this far off its low, closing above its 50-day
CONFIRM_WINDOW = 40          # sessions the window stays open after the confirmation day
INDEX_SMA = 50

# ---- the stock condition
MAX_PCT_BELOW_52W_HIGH = 15.0   # the near_highs screen's H3, restated here for the docs
RS_LINE_TOL_PCT = 2.0           # stock/index ratio within this % of its own 52-week high
RS_MIN_RANK = 80                # cross-sectional, applied by the backtest
GROUP_MIN_RANK = 80             # cross-sectional, applied by the backtest

# ---- the base and the entry
BASE_MIN_DAYS = 15
BASE_MAX_DAYS = 40
BASE_MAX_DEPTH_PCT = 25.0
PIVOT_DAYS = 15                 # the pivot is the highest high of this many sessions
VOL_MULT = 1.4                  # breakout volume against the 50-day average
BUY_RANGE_PCT = 5.0             # never pay more than this above the pivot
STOP_DAYS = 10                  # stop at the lowest low of this many sessions before the breakout
MAX_STOP_PCT = 8.0              # and never further than this below entry
PARTIAL_GAIN_PCT = 22.0         # O'Neil's 20-25%: a third comes off here
PARTIAL_FRAC = 1 / 3


def _market_of(symbol: str) -> str:
    """Which market a symbol belongs to, from the configured ticker suffixes.

    StockContext carries no market and evaluate() needs one to load the index. Read from
    MARKETS rather than hard-coded, so a new country stays a config entry (CLAUDE.md).
    """
    from ..config import MARKETS
    best, blank = None, None
    for k, cfg in MARKETS.items():
        sfx = getattr(cfg, "symbol_suffix", "") or ""
        if not sfx:
            blank = k
        elif symbol.upper().endswith(sfx.upper()):
            best = k
    return best or blank or next(iter(MARKETS))


def _rs_line_ok(ctx: StockContext, bench) -> tuple[bool, str]:
    """Is the stock's RS line (stock / index) within RS_LINE_TOL_PCT of its own 52-week high?

    `bench` is passed in, never stashed on ctx.extras: extras is serialised to JSON for the signal
    cache, so a Series or a set there fails the whole run with "Object of type set is not JSON
    serializable" -- which it did.
    """
    if bench is None:
        return True, "no benchmark stored — RS line not checked"
    # Slice BEFORE aligning. Reindexing the whole benchmark to the whole frame on every bar made
    # this quadratic in bars per symbol and dominated the scan; only the last year is ever read.
    # A margin beyond 252 so the forward fill has something to carry in from.
    d = ctx.daily
    tail = d["close"].iloc[-(252 + 40):]
    ratio = (tail / bench.reindex(tail.index).ffill()).dropna()
    if len(ratio) < 60:
        return True, "insufficient overlap for the RS line"
    window = ratio.iloc[-252:] if len(ratio) >= 252 else ratio
    peak = float(window.max())
    now = float(ratio.iloc[-1])
    if peak <= 0:
        return True, "degenerate RS line"
    off = (1 - now / peak) * 100
    ctx.extras["rs_line_pct_off"] = round(off, 2)
    return off <= RS_LINE_TOL_PCT, f"RS line {off:.1f}% below its 52-week high"


class RsLeadersStrategy(Strategy):
    """Buy the leaders out of a flat base once a correction has confirmed."""

    selection = "time_series"
    family = "rs_leaders"
    version = "1.0"
    changelog = (("1.0", "2026-10-17",
                  "First version, from the Learn guide: a confirmed-recovery market gate, the per-stock "
                  "leadership tests, a flat base with a pivot, a buy-stop entry on volume, a 10-day/8% stop, "
                  "a third off at +22% and the rest on a close below the 50-day. The RS rank and group rank "
                  "are cross-sectional and applied by the backtest, not by these gates."),)
    key = "rs_leaders"
    name = "RS leaders"
    description = ("After a correction confirms, buy the strongest stocks in the strongest industry groups as "
                   "they break out of a flat base, with a tight stop.")
    style = "breakout"
    behaviour = "trend_momentum"

    screen_key = "near_highs"
    screen_gates = {"G1": "H1", "G2": "H2", "G3": "H3"}
    gate_codes = ("G1", "G2", "G3", "G4", "G5", "G6")
    gate_titles = {"G1": "Above the 200-day", "G2": "200-day not falling", "G3": "Near the 52-week high",
                   "G4": "Trend stacked", "G5": "RS line near its high", "G6": "Confirmed recovery"}
    watch_codes = ("W1", "W2", "W3")
    setup_codes = (RSL01,)
    setup_names = {RSL01: "Flat-base breakout"}
    min_bars = 300
    needs_ctx_extras = True
    extra_columns = ("pivot", "base_days", "base_depth_pct", "rs_line_pct_off", "stop_low", "vol_ratio")
    extra_numeric_columns = extra_columns

    thesis = ("The stocks that hold up during a fall are the ones institutions are unwilling to sell, and they "
              "tend to lead the next advance. So the strategy waits for the market to fall and then recover, "
              "keeps only stocks that stayed near their highs and kept pace with the index, and buys them as they "
              "break out of a short flat base, with a stop under the base's last ten sessions.")
    how_it_works = (
        "The idea. After a correction, buy the stocks that held up best, as they break out of a short flat base. "
        "The rules come from the Learn guide \"Relative-strength leaders\"; it has no numbered spec.",
        "Step 1, the market (G6). Trade only in the {CONFIRM_WINDOW} sessions after the index confirms a "
        "recovery from a {CORRECTION_PCT}% correction. Outside that window nothing is bought.",
        "Step 2, the stock (G1-G5). An uptrend near the 52-week high, averages stacked, and an RS line near its own "
        "high. The backtest then keeps only stocks rated {RS_MIN_RANK}+ in groups rated {GROUP_MIN_RANK}+ (see When "
        "no new trade is taken).",
        "Step 3, the setup (S1). A close through the pivot of a {BASE_MIN_DAYS}-{BASE_MAX_DAYS}-session base no "
        "deeper than {BASE_MAX_DEPTH_PCT}%, on volume and not extended (W1, W2).",
        "Step 4, the trade. Bought at the next open (Entry); stopped under the {STOP_DAYS}-session low (Stop); no "
        "target order (Target); sold on the first close below the 50-day (Exit).",
        "Timing. Everything is decided on daily closes; the buy happens the next morning.",
    )
    caveats = (
        "**The guide's own evidence is mixed, and leans against the US.** Leaders in strong groups beat the "
        "typical stock in 9 of 13 Indian recoveries over three months, but LAGGED in 6 of 7 US ones. Much of any "
        "edge has to come from the trade management rather than the selection.",
        "**Gap risk is the main danger.** The stop is a level, not a guarantee: on 7 April 2025 several Indian "
        "leaders opened far below theirs, and a backtest on daily bars fills at the open in that case, for a loss "
        "larger than 1R.",
        "**The recovery window is the binding constraint.** Only {CONFIRM_WINDOW} sessions after each "
        "confirmation are tradeable, so this produces signals in bursts and nothing at all for long stretches.",
        "**The partial profit is not traded.** The guide sells a third at +20-25% and the first version's "
        "changelog says the same, but the backtest runs `--exit-mode ma --no-target` with no partial sale, so the "
        "+{PARTIAL_GAIN_PCT}% level is only the plan's reported target. Every share leaves on the stop or the "
        "50-day exit.",
        "**The buy is not the guide's buy-stop.** The guide rests a buy-stop just above the pivot. The code waits "
        "for a close through the pivot and buys at the next open, which pays any overnight gap, and refuses the "
        "trade if that open is beyond the buy range or puts the stop too far away.",
        "**The live screen is wider than the backtest.** The daily screen applies neither the RS-rating nor the "
        "group filter, so it lists breakouts the backtest would drop.",
        "**Group strength is applied from stored group RS**, which starts in 2013 in both markets — a run from "
        "earlier than that has no group filter at all. The group is today's industry classification, and a group "
        "too small to rate is kept rather than dropped.",
        "**Surveillance and trade-for-trade filters (India) are not modelled**; the guide asks for them and the "
        "stored data does not carry them. Neither are results dates: nothing stops a buy just before a "
        "results announcement.",
    )
    status = (
        "MEASURED in India from 2020, and the headline misreads it. CAGR 3.80% against the Nifty 500's 12.63% "
        "-- a -8.84 excess -- on 64 trades with a 37.5% win rate and a -13.2% maximum drawdown. But it is "
        "invested only 17.3% of the time, because the recovery window is open for {CONFIRM_WINDOW} sessions "
        "after each confirmation and nothing else. Against the index held at THAT exposure it is +1.39, which "
        "is the best selection figure of any per-symbol strategy here (minervini India is +0.86 and the rest are "
        "negative). The whole shortfall is idle capital: parking it in the index would have returned 14.16%. "
        "So the recovery gate appears to improve what gets picked and guarantees the result cannot compound -- "
        "and +1.39 over 64 trades is still inside the noise. "
        "US 2020 says the same thing more faintly: CAGR 3.76% against SPY's 13.41% (-9.65), 69 trades, 42.0% "
        "win rate, 18.9% invested, selection +0.28 -- positive but indistinguishable from zero, which matches "
        "the guide's own finding that leaders LAGGED in 6 of 7 US recoveries. Both markets agree on the shape: "
        "the gate picks a little better and trades far too rarely to compound."
    )

    gate_docs = {
        "G1": "H1: the close is above the 200-day average.\n\n"
              "- **Test:** today's close is strictly above the 200-day simple average of daily closes. A stock "
              "without 200 sessions of history fails.",
        "G2": "H2: the 200-day average is not falling.\n\n"
              "- **Test:** the 200-day average is not more than the Near-highs screen's limit (0.5% today) below "
              "its own value 20 sessions earlier. Flat passes, so does rising.\n"
              "- **Where the numbers live:** the screen's constants; its page shows the live values.",
        "G3": "H3: the close is within {MAX_PCT_BELOW_52W_HIGH}% of the 52-week high.\n\n"
              "- **Test:** (1 − close ÷ highest daily high of the last 252 sessions) × 100 is at most the limit.\n"
              "- **Two copies of the number:** the gate reads the Near-highs screen's own limit; the strategy's "
              "pre-filter applies {MAX_PCT_BELOW_52W_HIGH}% again. They agree today.",
        "G4": "The averages are stacked: close above the 50-day, and the 50-day above the 200-day.\n\n"
              "- **Test:** close > 50-day simple average > 200-day simple average, all on today's daily bar.",
        "G5": "The RS line is within {RS_LINE_TOL_PCT}% of its own 52-week high.\n\n"
              "- **RS line:** the stock's daily close divided by the index's close on the same day (the index "
              "carried forward over a missing day).\n"
              "- **Test:** today's RS line is no more than {RS_LINE_TOL_PCT}% below the highest RS line of the "
              "last 252 sessions, today included. A new RS high passes.\n"
              "- **Not checked (passes with a note):** no index stored, or fewer than 60 sessions where both "
              "prices exist.",
        "G6": "The market is inside a confirmed-recovery window.\n\n"
              "- **Correction:** the index closes more than {CORRECTION_PCT}% below its highest close in the "
              "stored history to that day.\n"
              "- **Confirmation day:** the first session after that on which the index closes at least "
              "{REBOUND_PCT}% above its lowest close since the correction began AND above its own {INDEX_SMA}-day "
              "average.\n"
              "- **Window:** {CONFIRM_WINDOW} sessions, counted from and including the confirmation day. Today "
              "must be one of them.\n"
              "- **One confirmation per drawdown:** after a confirmation, a new correction can only be declared "
              "once the index has closed back within {CORRECTION_PCT}% of its high. A long bear market therefore "
              "confirms once, not every time it bounces.\n"
              "- **Not checked (passes with a note):** no index stored.",
    }
    watch_docs = {
        "W1": "The breakout came on light volume: under {VOL_MULT}x the 50-day average volume.\n\n"
              "- **Test:** on the signal session, volume ÷ its 50-day average volume is below {VOL_MULT}.\n"
              "- **Effect:** the decision drops to WATCH, so the stock is not bought (the backtest buys only HIGH "
              "CONFIDENCE).",
        "W2": "The breakout closed more than {BUY_RANGE_PCT}% above the pivot: too extended to buy.\n\n"
              "- **Test:** close > pivot × (1 + {BUY_RANGE_PCT}%).\n"
              "- **Effect:** the decision drops to WATCH, so the stock is not bought. The guide says to wait for "
              "the next base.",
        "W3": "The stop was capped: the {STOP_DAYS}-session low sits more than {MAX_STOP_PCT}% below the signal "
              "close.\n\n"
              "- **Test:** the lowest low of the {STOP_DAYS} sessions before the signal < close × (1 − "
              "{MAX_STOP_PCT}%).\n"
              "- **Effect:** the stop is raised to {MAX_STOP_PCT}% below the close instead. The decision does not "
              "change, but at the fill the risk is re-checked, so in a backtest such a trade fills only if the "
              "next open is below the signal close (see Entry).",
    }
    setup_docs = {
        RSL01: "Flat-base breakout: today's close clears the pivot of a base of {BASE_MIN_DAYS}-{BASE_MAX_DAYS} "
               "sessions no deeper than {BASE_MAX_DEPTH_PCT}%.\n\n"
               "- **Base:** the sessions up to yesterday. The strategy tries every length from {BASE_MAX_DAYS} "
               "down to {BASE_MIN_DAYS} sessions and keeps the longest whose highest high and lowest low are within "
               "{BASE_MAX_DEPTH_PCT}% of the high: (high − low) ÷ high × 100 ≤ {BASE_MAX_DEPTH_PCT}. Depth is the "
               "only test; there is no separate test that the range is sideways.\n"
               "- **Pivot:** the highest high of the {PIVOT_DAYS} sessions up to yesterday. It can sit below the "
               "base's own high when that high is older than {PIVOT_DAYS} sessions.\n"
               "- **Breakout:** yesterday's close was at or below the pivot and today's close is above it.\n\n"
               "Volume and distance from the pivot are not part of the setup: a breakout that misses them still "
               "counts, and shows as W1 or W2.",
    }
    entry_rules = (
        "Signal on the close. A stock that passes every gate and closes through the pivot (S1), on at least "
        "{VOL_MULT}x its 50-day volume (W1 clear) and no more than {BUY_RANGE_PCT}% above the pivot (W2 clear), is a "
        "HIGH CONFIDENCE buy signal on that session's close. Nothing else is bought: a backtest takes only HIGH "
        "CONFIDENCE signals.",
        "Bought at the next session's open. The order is a market order at the open of the session after the "
        "signal, valid for that one session. It is not a buy-stop resting at the pivot, as the guide describes. "
        "The plan shown live uses the signal close as its entry price.",
        "Skipped above the buy range. If that open is more than {BUY_RANGE_PCT}% above the pivot, the buy is "
        "cancelled.",
        "Skipped when the stop ends up too far away. The stop was set from the signal close; if the price "
        "actually paid puts it more than {MAX_STOP_PCT}% below, the buy is cancelled. A stop already capped at "
        "{MAX_STOP_PCT}% (W3) therefore only fills on an open below the signal close.",
        "No ranking among same-day signals. Every signal carries the same setup quality, so when more stocks "
        "trigger than there are free position slots, strength does not decide which ones are bought.",
    )
    stop_rules = (
        "Where it goes. At the lowest low of the {STOP_DAYS} sessions before the signal session (the signal "
        "session's own low is not included), rounded down to the price tick.",
        "Never more than {MAX_STOP_PCT}% away. If that low is more than {MAX_STOP_PCT}% below the signal close, the "
        "stop is raised to {MAX_STOP_PCT}% below the close and W3 is noted.",
        "It defines the risk. The distance from the price paid to the stop is the trade's risk, 1R. Results are "
        "counted in R.",
        "How it sells. The stop is a standing sell order: it sells during the session the moment the low touches "
        "it, at the stop price. If the stock opens below the stop, it sells at that open, so a gap can lose more "
        "than 1R.",
        "It never moves. There is no move to breakeven and no trailing; the guide's rule to raise the stop to the "
        "entry at +2R is not modelled.",
    )
    target_rules = (
        "No sell order at the target. The plan's target is +{PARTIAL_GAIN_PCT}% above the signal close, the level "
        "at which the guide sells a third. The backtest runs with `--no-target` and no partial sale, so nothing is "
        "sold there; the level is reported only, and it sets the plan's reward-to-risk figure.",
        "No reward-to-risk minimum. A trade is never refused for a low reward-to-risk ratio.",
    )
    exit_rules = (
        "Each session after the buy, the stop is checked first (see Stop). The session of the buy itself is not "
        "checked.",
        "Trend exit. The first daily close below the 50-day simple average sells the whole position at that "
        "close.",
        "That is the only sell besides the stop. The guide's partial sale at +{PARTIAL_GAIN_PCT}%, its optional "
        "time stop, its RS-line invalidation and its rule to close new positions when the index breaks its "
        "correction low are not modelled.",
    )
    sizing_rules = (
        "Risk per trade. Shares = the risk budget ÷ (price paid − stop). The budget is the market config's risk "
        "per trade (1% of current equity in both markets today), so a stop-out loses about the same amount "
        "whatever the stop's width, unless it gaps.",
        "Caps. No position larger than the market config's maximum share of equity (25% today); at most the "
        "config's number of open positions (10 today); a buy is scaled down to the cash available rather than "
        "skipped.",
        "Not modelled. The guide's limit of two positions per industry group and its advice to start with a few "
        "positions after the confirmation day.",
    )
    filter_rules = (
        "Outside a recovery window (G6). No new buy unless today falls in the {CONFIRM_WINDOW} sessions from a "
        "confirmation day. Positions already held are kept.",
        "RS rating below {RS_MIN_RANK} (backtest only, `--min-rs`). The RS score adds up the stock's 3-, 6-, 9- and "
        "12-month returns, counting the latest 3 months twice; the rating ranks it from 1 to 99 across the "
        "tradable market on the signal date. Signals rated below {RS_MIN_RANK}, or from stocks outside the rated "
        "universe that day, are dropped.",
        "Weak industry group (backtest only, `--min-group-rs`). Signals whose industry group was rated below "
        "{GROUP_MIN_RANK} on the signal date are dropped. A group too small to be rated is kept.",
        "Too thin. A stock whose 20-day average traded value is under the market's liquidity floor is not "
        "evaluated.",
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "Every gate passes, the close broke through the pivot today on at least "
                                 "{VOL_MULT}x volume, and within {BUY_RANGE_PCT}% of the pivot. Buy at the next "
                                 "open.",
        "TRADE_ON_TRIGGER": "Not used. The setup only exists on the breakout session itself, so no buy-stop is "
                            "ever left resting under a pivot.",
        "WATCH_WAIT": "A breakout held back: light volume (W1), more than {BUY_RANGE_PCT}% above the pivot (W2), "
                      "or the market regime (see the note below). Not bought.",
        "AVOID": "A gate failed, or no breakout today (no base, or the close did not cross the pivot).",
    }
    regime_note = (
        "Live only. When the latest stored index session is outside a confirmed-recovery window (or, with no "
        "index stored, when the shared market regime is risk-off), a HIGH CONFIDENCE breakout becomes WATCH with "
        "the reason 'outside a confirmed recovery: no new buys'. WATCH and AVOID are untouched. In practice G6 "
        "usually fails the stock first, which makes it AVOID."
    )
    param_docs = (
        ("Correction", "CORRECTION_PCT", "How far below its highest close the index must close before a recovery "
                                         "can confirm."),
        ("Rebound", "REBOUND_PCT", "How far above its lowest close since then the index must close (and above its "
                                   "average) to confirm."),
        ("Index average", "INDEX_SMA", "Days in the index's simple average the confirmation close must be above."),
        ("Recovery window", "CONFIRM_WINDOW", "Sessions, from the confirmation day, in which new buys are allowed."),
        ("Near the high", "MAX_PCT_BELOW_52W_HIGH", "Most the close may sit below the 52-week high (pre-filter; "
                                                    "the screen's H3 uses its own equal limit)."),
        ("RS line tolerance", "RS_LINE_TOL_PCT", "How far the RS line may sit below its own 52-week high."),
        ("Base length", "BASE_MIN_DAYS", "Shortest base accepted, in sessions."),
        ("Base length, maximum", "BASE_MAX_DAYS", "Longest base the search starts from, in sessions."),
        ("Base depth", "BASE_MAX_DEPTH_PCT", "Deepest a base may be: (highest high − lowest low) ÷ highest high."),
        ("Pivot", "PIVOT_DAYS", "Sessions before today whose highest high is the pivot."),
        ("Breakout volume", "VOL_MULT", "Signal-day volume against its 50-day average; below it is W1."),
        ("Buy range", "BUY_RANGE_PCT", "Most the close (W2) or the next open (skipped) may be above the pivot."),
        ("Stop lookback", "STOP_DAYS", "Sessions before the signal whose lowest low is the stop."),
        ("Maximum stop", "MAX_STOP_PCT", "Widest stop, as a % of the signal close (capped) and of the fill "
                                         "(skipped)."),
        ("Reported target", "PARTIAL_GAIN_PCT", "The plan's target above the signal close; never sold in a "
                                                "backtest."),
        ("RS rank", "RS_MIN_RANK", "Minimum RS rating, 1-99; applied by the backtest's --min-rs."),
        ("Group rank", "GROUP_MIN_RANK", "Minimum industry-group rating; applied by the backtest's --min-group-rs."),
    )
    backtest_args = f"--min-rs {RS_MIN_RANK} --min-group-rs {GROUP_MIN_RANK} --exit-mode ma --no-target"

    # ---------- screen ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        """The guide's universe filters, as of one row: tradable, and near its high in an uptrend.

        The cross-sectional halves (RS rank, group rank) are NOT here -- a row cannot rank a market,
        and the backtest applies them to the collected signals.
        """
        ok, why = tradable_point_in_time(cfg, last)
        if not ok:
            return False, why
        close, hi52 = last.get("close"), last.get("high_252")
        s50, s200 = last.get("sma50"), last.get("sma200")
        if any(pd.isna(v) for v in (close, hi52, s50, s200)):
            return False, "insufficient history"
        if hi52 <= 0 or float(close) < float(hi52) * (1 - MAX_PCT_BELOW_52W_HIGH / 100):
            return False, f"more than {MAX_PCT_BELOW_52W_HIGH:g}% below the 52-week high"
        if not (float(close) > float(s50) > float(s200)):
            return False, "not stacked: close > 50-day > 200-day"
        return True, "passed"

    # ---------- market ----------

    _recovery: dict = {}

    @classmethod
    def _recovery_days(cls, market_key: str):
        """Dates on which the market is in a confirmed recovery, computed once per market.

        Cached on the class because every symbol on every bar asks the same question of the same
        index series, and recomputing it per row dominated the scan.
        """
        if market_key in cls._recovery:
            return cls._recovery[market_key]
        from ..config import MARKETS
        from ..marketdata import cache
        cfg = MARKETS[market_key]
        b = cache.load_cached(market_key, cfg.benchmark_ticker)
        if b is None or b.empty:
            cls._recovery[market_key] = None
            return None
        c = b["close"].astype(float)
        sma = c.rolling(INDEX_SMA).mean()
        peak = c.cummax()
        in_corr = c < peak * (1 - CORRECTION_PCT / 100)
        # A state machine, not a per-bar test. India sits more than CORRECTION_PCT below its running
        # peak on 40% of sessions, so "arm whenever in correction" re-armed every bar and one long
        # drawdown confirmed dozens of times -- 2,254 recovery days out of 5,178. A correction has
        # to HEAL (price back above the correction threshold) before another one can be declared.
        ok, confirms = set(), []
        state, trough = "normal", None
        for d, px in c.items():
            corr = bool(in_corr.get(d, False))
            if state == "normal":
                if corr:
                    state, trough = "correcting", px
            elif state == "correcting":
                trough = min(trough, px)
                rebounded = px >= trough * (1 + REBOUND_PCT / 100)
                above = pd.notna(sma.get(d)) and px > sma[d]
                if rebounded and above:
                    i = c.index.get_loc(d)
                    for dd in c.index[i : i + CONFIRM_WINDOW]:
                        ok.add(dd)
                    confirms.append(d)
                    state, trough = "healing", None
            elif state == "healing" and not corr:
                state = "normal"          # the drawdown closed; a fresh fall can arm again
        cls._recovery[market_key] = ok
        cls._confirmations = getattr(cls, "_confirmations", {})
        cls._confirmations[market_key] = confirms
        return ok

    _bench_cache: dict = {}

    @classmethod
    def _bench_close(cls, market_key: str):
        if market_key not in cls._bench_cache:
            from ..config import MARKETS
            from ..marketdata import cache
            b = cache.load_cached(market_key, MARKETS[market_key].benchmark_ticker)
            cls._bench_cache[market_key] = b["close"].astype(float) if b is not None and len(b) else None
        return cls._bench_cache[market_key]

    def market_risk_off(self, market_key: str, default: bool) -> bool:
        """Live: outside a confirmed recovery window there are no new buys."""
        days = self._recovery_days(market_key)
        if days is None:
            return default
        from ..marketdata import cache
        from ..config import MARKETS
        b = cache.load_cached(market_key, MARKETS[market_key].benchmark_ticker)
        return b is None or b.empty or b.index[-1] not in days

    # ---------- evaluation ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        d = ctx.daily
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        self.apply_screen(ctx, result)
        # The index-derived inputs, resolved once per symbol and cached on the class: both the
        # recovery window and the RS line need the benchmark, which the context does not carry.
        mkt = _market_of(ctx.symbol)
        recovery = self._recovery_days(mkt)      # class-cached; never put on ctx.extras (JSON)
        bench = self._bench_close(mkt)
        last = d.iloc[-1]
        close = ctx.close

        s50, s200 = last.get("sma50"), last.get("sma200")
        if pd.isna(s50) or pd.isna(s200):
            result.fail("G4", "insufficient history for the averages")
        elif close > float(s50) and float(s50) > float(s200):
            result.ok("G4", f"close {close:.2f} > 50-day {float(s50):.2f} > 200-day {float(s200):.2f}")
        else:
            result.fail("G4", "not stacked: close > 50-day > 200-day")

        ok5, why5 = _rs_line_ok(ctx, bench)
        (result.ok if ok5 else result.fail)("G5", why5)

        days = recovery
        if days is None:
            result.ok("G6", "no benchmark stored — recovery window not checked")
        elif d.index[-1] in days:
            result.ok("G6", "inside a confirmed recovery window")
        else:
            result.fail("G6", f"not within {CONFIRM_WINDOW} sessions of a confirmed recovery")

        # ---- the flat base and its pivot
        pivot = float(d["high"].iloc[-(PIVOT_DAYS + 1):-1].max()) if len(d) > PIVOT_DAYS else float("nan")
        base_days, depth = 0, float("nan")
        for n in range(BASE_MAX_DAYS, BASE_MIN_DAYS - 1, -1):
            if len(d) <= n + 1:
                continue
            w = d.iloc[-(n + 1):-1]
            hi, lo = float(w["high"].max()), float(w["low"].min())
            if hi > 0 and (hi - lo) / hi * 100 <= BASE_MAX_DEPTH_PCT:
                base_days, depth = n, (hi - lo) / hi * 100
                break
        vol = float(last["volume"]); v50 = float(last.get("vol_sma50") or float("nan"))
        vol_ratio = vol / v50 if v50 == v50 and v50 else float("nan")
        prev_close = float(d["close"].iloc[-2])
        broke = bool(base_days and pivot == pivot and prev_close <= pivot < close)

        result.setups[RSL01] = broke
        result.watch_flags["W1"] = bool(broke and not (vol_ratio >= VOL_MULT))
        result.watch_flags["W2"] = bool(broke and pivot and close > pivot * (1 + BUY_RANGE_PCT / 100))
        if result.watch_flags["W1"]:
            result.watch_notes["W1"] = f"volume {vol_ratio:.2f}x its 50-day average"
        if result.watch_flags["W2"]:
            result.watch_notes["W2"] = f"{(close / pivot - 1) * 100:.1f}% above the pivot"

        stop_low = float(d["low"].iloc[-(STOP_DAYS + 1):-1].min()) if len(d) > STOP_DAYS else float("nan")
        ctx.extras.update(pivot=pivot if pivot == pivot else None, base_days=base_days or None,
                          base_depth_pct=round(depth, 2) if depth == depth else None,
                          stop_low=stop_low if stop_low == stop_low else None,
                          vol_ratio=round(vol_ratio, 2) if vol_ratio == vol_ratio else None)
        result.recompute_first_fail()
        return result

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        return result.has_setup

    def setup_quality(self, result: StrategyResult) -> float:
        return 1.0 if result.setups.get(RSL01) else 0.0

    # ---------- plan ----------

    def setup_shapes(self, ctx: StockContext, result: StrategyResult, sig: dict) -> list[dict]:
        """For the chart's Trade setups layer (strategies/live_setups.py), the flat base the breakout left,
        from the same windows evaluate() reads: the longest window of {BASE_MIN_DAYS}-{BASE_MAX_DAYS}
        sessions within {BASE_MAX_DEPTH_PCT}%, and the pivot -- the highest high of {PIVOT_DAYS}
        sessions -- the close has to clear. Drawing only: no rule reads it."""
        d, e = ctx.daily, ctx.extras
        day = lambda ts: str(pd.Timestamp(ts).date())
        out: list[dict] = []
        n, pivot = e.get("base_days"), e.get("pivot")
        if n and len(d) > n + 1:
            w = d.iloc[-(n + 1):-1]
            hi, lo = float(w["high"].max()), float(w["low"].min())
            out.append({"shape": "box", "from": day(w.index[0]), "to": day(w.index[-1]), "top": hi, "bottom": lo, "role": "base",
                        "label": f"flat base · {n} days · {(hi - lo) / hi * 100:.0f}% deep"})
        if pivot and len(d) > PIVOT_DAYS:
            win = d.iloc[-(PIVOT_DAYS + 1):-1]
            out.append({"shape": "level", "from": day(win["high"].idxmax()), "to": day(d.index[-1]), "price": float(pivot),
                        "role": "pivot", "label": f"pivot {pivot:,.2f} · {PIVOT_DAYS}-day high"})
        return out

    def build_plans(self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no base breakout")
        e = ctx.extras
        pivot, stop_low = e.get("pivot"), e.get("stop_low")
        if not pivot or stop_low is None:
            return PlanChoice(None, None, "missing pivot / stop level")
        entry = float(ctx.close)
        floor_ = entry * (1 - MAX_STOP_PCT / 100)
        stop = round_tick(max(float(stop_low), floor_), cfg.tick_size, "down")
        result.watch_flags["W3"] = bool(float(stop_low) < floor_)
        if stop <= 0 or stop >= entry:
            return PlanChoice(None, None, "degenerate stop")
        risk = entry - stop
        # The guide sets no price target: a third comes off at a GAIN and the rest on the trend exit.
        # Reporting a target anyway would invent a number the rules never use, so the nominal is the
        # partial-profit level and nothing is projected beyond it.
        target = entry * (1 + PARTIAL_GAIN_PCT / 100)
        r = (target - entry) / risk
        ctx.extras["structural_r"] = round(r, 2)
        from ..core import swings as sw
        plan = TradePlan(plan="RSL", setup=RSL01, entry=entry, stop=stop, target=target,
                         risk_per_share=risk, reward_per_share=target - entry, r_multiple=round(r, 2),
                         nearest_overhead_above_entry=sw.nearest_overhead_above(entry, ctx.overhead))
        return PlanChoice(plan, None, f"pivot {pivot:.2f}, stop {(entry - stop) / entry * 100:.1f}% below entry")

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        e = ctx.extras
        return {"pivot": float(e["pivot"]), "tight_low": float(e["stop_low"]),
                "max_fill": float(e["pivot"]) * (1 + BUY_RANGE_PCT / 100),
                "max_risk_pct": MAX_STOP_PCT / 100, "order": "open",
                "min_breakout_vol": VOL_MULT}

    # ---------- decision ----------

    def classify(self, ctx, result, plan, sizing_result, earnings_days_away, regime_downgrade_active) -> Decision:
        q = self.setup_quality(result)
        if not result.hard_gates_passed:
            return Decision(LABELS["AVOID"], LABELS["AVOID"],
                            f"fails {result.first_hard_fail}: {result.hard_notes.get(result.first_hard_fail, '')}",
                            0.0, 0.0, q)
        if plan is None or not plan.is_valid:
            return Decision(LABELS["AVOID"], LABELS["AVOID"], "no valid entry plan", 0.0, 0.0, q)
        risk_pct = plan.risk_per_share / plan.entry * 100
        label, reasons = "TRADE_HIGH_CONFIDENCE", ["flat-base breakout in a confirmed recovery"]
        if result.watch_flags.get("W1"):
            label = "WATCH_WAIT"; reasons.append("breakout volume below the threshold")
        if result.watch_flags.get("W2"):
            label = "WATCH_WAIT"; reasons.append("extended beyond the buy range")
        before = label
        if regime_downgrade_active and label.startswith("TRADE"):
            label = "WATCH_WAIT"; reasons.append("outside a confirmed recovery: no new buys")
        return Decision(LABELS[before], LABELS[label], "; ".join(reasons), risk_pct, plan.r_multiple, q)
