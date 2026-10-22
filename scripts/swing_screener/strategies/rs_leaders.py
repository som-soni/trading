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
              "tend to lead the next advance. Ranking by relative strength finds them; waiting for a confirmed "
              "recovery and a base breakout decides when to buy.")
    how_it_works = (
        "Market first: the index must have fallen {CORRECTION_PCT}% from its high, then risen {REBOUND_PCT}% off "
        "its low and closed above its {INDEX_SMA}-day average. That day is the confirmation, and the strategy "
        "trades for {CONFIRM_WINDOW} sessions after it — beyond that it is an ordinary uptrend, not a recovery.",
        "Gates G1-G3 are the Near-highs screen: above the 200-day, the 200-day not falling, and within "
        "{MAX_PCT_BELOW_52W_HIGH}% of the 52-week high.",
        "G4 adds the stacking the guide asks for: close above the 50-day and the 50-day above the 200-day.",
        "G5 is the RS line — the stock divided by the index — within {RS_LINE_TOL_PCT}% of its own 52-week high. "
        "A stock can sit near its price high while losing ground to the index; this is the test that separates them.",
        "The base is {BASE_MIN_DAYS}-{BASE_MAX_DAYS} sessions no deeper than {BASE_MAX_DEPTH_PCT}%, and the pivot "
        "is the highest high of the last {PIVOT_DAYS}.",
        "RS rank {RS_MIN_RANK}+ and an industry group in the top fifth are CROSS-SECTIONAL and applied by the "
        "backtest to the collected signals, because a one-symbol evaluation cannot rank a market.",
    )
    caveats = (
        "**The guide's own evidence is mixed, and leans against the US.** Leaders in strong groups beat the "
        "typical stock in 9 of 13 Indian recoveries over three months, but LAGGED in 6 of 7 US ones. Much of any "
        "edge has to come from the trade management rather than the selection.",
        "**Gap risk is the main danger.** The stop is a level, not a guarantee: on 7 April 2025 several Indian "
        "leaders opened far below theirs, and a backtest on daily bars fills at the open in that case.",
        "**The recovery window is the binding constraint.** Only {CONFIRM_WINDOW} sessions after each "
        "confirmation are tradeable, so this produces signals in bursts and nothing at all for long stretches.",
        "**Group strength is applied from stored group RS**, which starts in 2013 in both markets — a run from "
        "earlier than that has no group filter at all.",
        "**Surveillance and trade-for-trade filters (India) are not modelled**; the guide asks for them and the "
        "stored data does not carry them.",
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
        "G1": "H1: close above the 200-day average.",
        "G2": "H2: the 200-day is not falling.",
        "G3": "H3: close within {MAX_PCT_BELOW_52W_HIGH}% of the 52-week high.",
        "G4": "Close above the 50-day average, and the 50-day above the 200-day.",
        "G5": "The RS line (stock ÷ index) is within {RS_LINE_TOL_PCT}% of its own 52-week high.",
        "G6": "The market is in a confirmed recovery: a {CORRECTION_PCT}% fall, then a {REBOUND_PCT}% rebound "
              "closing above the {INDEX_SMA}-day, within the last {CONFIRM_WINDOW} sessions.",
    }
    watch_docs = {
        "W1": "Breakout volume under {VOL_MULT}x the 50-day average — the guide sells such a fill at the close.",
        "W2": "Closed more than {BUY_RANGE_PCT}% above the pivot: too extended to buy.",
        "W3": "The stop would sit more than {MAX_STOP_PCT}% below entry, so it is capped and the trade risks more "
              "than the base suggests.",
    }
    setup_docs = {
        RSL01: "A flat base of {BASE_MIN_DAYS}-{BASE_MAX_DAYS} sessions no deeper than {BASE_MAX_DEPTH_PCT}%, with "
               "today's close through the pivot — the highest high of the last {PIVOT_DAYS} sessions.",
    }
    entry_rules = (
        "A buy-stop just above the pivot; the fill is the pivot, or the open if the stock gaps through it.",
        "Refused more than {BUY_RANGE_PCT}% above the pivot — wait for the next base instead.",
        "The breakout day must trade at least {VOL_MULT}x its 50-day average volume; a quiet fill is sold at the "
        "next open.",
    )
    exit_rules = (
        "Stop: the lowest low of the {STOP_DAYS} sessions before the breakout, never more than {MAX_STOP_PCT}% "
        "below entry.",
        "A third is sold at +{PARTIAL_GAIN_PCT}% (O'Neil's 20-25% rule of thumb).",
        "The rest goes on the first close below the 50-day average.",
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "Every gate passes and the base broke out on volume, within {BUY_RANGE_PCT}% of "
                                 "the pivot.",
        "TRADE_ON_TRIGGER": "A valid base whose pivot has not been cleared yet: a buy-stop rests above it.",
        "WATCH_WAIT": "A valid setup held back — too extended, light volume, or results due.",
        "AVOID": "A gate failed, or there is no base to trade.",
    }
    param_docs = (
        ("Correction", "CORRECTION_PCT", "How far the index must fall before a recovery can confirm."),
        ("Rebound", "REBOUND_PCT", "How far it must rise off the low, closing above its 50-day."),
        ("Recovery window", "CONFIRM_WINDOW", "Sessions after confirmation in which the strategy trades."),
        ("Base length", "BASE_MIN_DAYS", "Shortest flat base accepted."),
        ("Base length, maximum", "BASE_MAX_DAYS", "Longest flat base accepted."),
        ("Base depth", "BASE_MAX_DEPTH_PCT", "Deepest a base may be, high to low."),
        ("Pivot", "PIVOT_DAYS", "Sessions whose highest high is the pivot."),
        ("Breakout volume", "VOL_MULT", "Multiple of the 50-day average volume required."),
        ("Buy range", "BUY_RANGE_PCT", "Most you may pay above the pivot."),
        ("Stop lookback", "STOP_DAYS", "Sessions whose lowest low sets the stop."),
        ("Maximum stop", "MAX_STOP_PCT", "Widest stop allowed, as a % of entry."),
        ("Partial profit", "PARTIAL_GAIN_PCT", "Gain at which a third is sold."),
        ("RS rank", "RS_MIN_RANK", "Cross-sectional; applied by the backtest's --min-rs."),
        ("Group rank", "GROUP_MIN_RANK", "Cross-sectional; applied by the backtest's --min-group-rs."),
        ("RS line tolerance", "RS_LINE_TOL_PCT", "How far the RS line may sit below its own 52-week high."),
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
