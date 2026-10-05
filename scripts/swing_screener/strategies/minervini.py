"""Minervini SEPA — Trend Template gates plus a Volatility Contraction entry.

Mark Minervini's Specific Entry Point Analysis has five parts applied in a
fixed order: screen for stocks already in a Stage-2 uptrend, check the business
behind them, wait for a low-risk entry, control risk tightly, and sell to a
plan — all scaled by the state of the general market.

What is implemented, and what is NOT
------------------------------------
Four of the five parts are price-and-volume rules and are implemented in full.
**Part 2, the fundamental screen, is not implemented here and is absent from
every backtest in this repository.** That is a data limitation, not a design
choice:

- `yfinance` returns **5 quarters** of income statement (measured on both AAPL
  and RELIANCE.NS) and 4-5 annual periods. Judging whether earnings growth is
  *accelerating* needs at least 8 quarters.
- Those figures are the CURRENT restatement. There is no as-of history, so
  ranking a 2015 stock by a 2026 margin is severe lookahead bias.
- The backtest window is ~55 quarters. Five quarters covers 9% of it, all at
  the recent end.

A live screener may legitimately read current fundamentals, because for a
screener "now" IS the as-of date. `marketdata/fundamentals.py` supplies those
as WATCH FLAGS for the daily screen only. Backtesting part 2 needs a
point-in-time vendor (Sharadar/Nasdaq Data Link, Compustat PIT, Capital IQ;
Trendlyne or Screener.in for India).

Relative strength
-----------------
Minervini wants an RS Rating >= 70, i.e. "stronger than 70% of all stocks".
That is inherently cross-sectional, and this architecture evaluates one symbol
at a time. It is handled in two places:

- gate **M8** applies a per-symbol 12-1 momentum floor (a documented proxy);
- `setup_quality` returns 12-1 momentum, so when more signals fire than there
  are open slots the strongest win. That is where "pick the strongest
  candidates" actually bites: the full-universe donchian run declined 63,383
  signals for want of a slot, and switching that ranking from a coarse setup
  score to 12-1 momentum was worth +7.78pp of CAGR in India.

Honest limits
-------------
The Trend Template is a well-known public rule set, which means it has been
mined by many people on this same data; treat an in-sample edge sceptically.
The VCP detector is an interpretation — "each pullback smaller than the last"
has no canonical numeric definition, and the thresholds here were calibrated
for selectivity (20% of US symbols show contraction) rather than fitted to
returns.
"""

import pandas as pd

from ..config.base import MarketConfig
from ..core import swings as sw
from ..core.context import StockContext
from .base import (
    CAP_ORDER,
    DOWNGRADE_MAP,
    LABELS,
    Decision,
    PlanChoice,
    Strategy,
    StrategyResult,
    TradePlan,
)
from .trend_pullback import round_tick

MV01 = "MV-01"  # VCP pivot breakout
MV02 = "MV-02"  # coiled inside the final contraction, pivot not yet taken

# --- Trend Template thresholds (Minervini's own numbers) ---
MIN_PCT_ABOVE_52W_LOW = 30.0   # "at least 30% above the 52-week low"
MAX_PCT_BELOW_52W_HIGH = 25.0  # "within 25% of the 52-week high"
SMA200_RISING_BARS = 21        # "200-day trending up for at least a month"
RS_MIN_MOM = 0.10              # RS proxy: 12-1 momentum floor

# --- VCP shape ---
VCP_LOOKBACK = 120             # bars of base to examine
VCP_MIN_LEGS = 2               # at least two pullbacks to compare
VCP_LEGS_TESTED = 3            # monotonic contraction over the final N legs
VCP_TOLERANCE_PP = 1.0         # a leg may be this much deeper and still count
VCP_TIGHT_PCT = 10.0           # the final contraction should be no deeper.
#                              Kept equal to MAX_STOP_PCT on purpose: a base
#                              whose last contraction is deeper than the
#                              maximum permissible loss cannot be entered at
#                              an acceptable stop, so calling it a setup just
#                              produces rows that build_plans() must refuse.
VCP_IDEAL_TIGHT_PCT = 8.0      # below this is a textbook tight area
VCP_DRY_VOLUME_RATIO = 1.0     # tight-area volume vs its own 50-day average
VCP_PROXIMITY_PCT = 8.0        # MV-02: how close to the pivot still counts
# MV-01 fires when the close is ALREADY through the pivot, so for a live screen
# run days after a breakout the quoted entry sits below the current price --
# you cannot buy at the pivot any more. Minervini's own rule is not to chase a
# breakout more than a few percent past the pivot, so beyond this the entry is
# treated as passed rather than silently quoting an unfillable price.
MAX_PCT_ABOVE_PIVOT = 5.0

# --- risk control (part 4) ---
MAX_STOP_PCT = 10.0            # his absolute maximum loss
TARGET_STOP_PCT = 7.0          # the average loss he actually aims for
NOMINAL_TARGET_R = 3.0         # sizing/reporting only; the real exit is a rule

# --- climax / extension ---
EXTENDED_ATR_ABOVE_SMA50 = 4.0


class MinerviniStrategy(Strategy):
    key = "minervini"
    name = "Minervini SEPA (trend template + VCP)"
    description = (
        "Stage-2 uptrend by the Trend Template, entered on a volatility "
        "contraction breakout, with a stop tight enough to keep the average "
        "loss near 7%."
    )

    gate_codes = ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8")
    watch_codes = ("V1", "V2", "V3", "V4", "V5", "V6")
    setup_codes = (MV01, MV02)
    extra_columns = (
        "pivot", "pct_from_pivot", "contraction_legs", "last_contraction_pct",
        "tight_volume_ratio", "pct_above_52w_low", "pct_below_52w_high", "rs_mom",
        # SEPA part 2, attached by the LIVE screener only -- these are blank
        # in every backtest, by design (see the module docstring)
        "revenue_yoy_pct", "earnings_yoy_pct", "gross_margin_change_pp",
        "fundamentals_ok",
    )
    extra_numeric_columns = (
        "pivot", "pct_from_pivot", "contraction_legs", "last_contraction_pct",
        "tight_volume_ratio", "pct_above_52w_low", "pct_below_52w_high", "rs_mom",
        "revenue_yoy_pct", "earnings_yoy_pct", "gross_margin_change_pp",
    )
    needs_ctx_extras = True
    wants_live_fundamentals = True
    # 252 bars for the 52-week window + 21 to see the 200-day rising, plus the
    # 252+21 that 12-1 momentum needs: a symbol with less history cannot be
    # judged by this template at all, and admitting it would silently compare
    # a 1-year stock against a 10-year one.
    min_bars = 300

    thesis = (
        "Stocks making large advances are already strong beforehand, so buy "
        "only confirmed Stage-2 uptrends, and buy them at the one moment when "
        "supply has dried up enough that a {MAX_STOP_PCT}%-maximum stop sits "
        "just below support. Small, strictly-capped losses against much "
        "larger winners is the whole arithmetic."
    )
    how_it_works = (
        "Gates M1-M8 are Minervini's Trend Template: price above the 50/150/"
        "200-day averages, those averages stacked in that order, the 200-day "
        "rising for at least {SMA200_RISING_BARS} sessions, price at least "
        "{MIN_PCT_ABOVE_52W_LOW}% above its 52-week low and within "
        "{MAX_PCT_BELOW_52W_HIGH}% of its 52-week high, and relative strength "
        "above a floor.",
        "Inside that, the base is tested for a Volatility Contraction Pattern: "
        "successive pullbacks each shallower than the last over the final "
        "{VCP_LEGS_TESTED} legs, the newest no deeper than {VCP_TIGHT_PCT}%, "
        "and volume in the tight area below its own 50-day average.",
        "The pivot is the high of that final tight area. Entry is a buy-stop "
        "just through it; the protective stop goes below the tight area's low.",
        "If the structural stop would be more than {MAX_STOP_PCT}% below "
        "entry, the trade is refused rather than widened — the risk cap is a "
        "constraint on which trades exist, not a number to stretch.",
        "Ranking among competing signals is 12-1 momentum, standing in for "
        "the cross-sectional RS Rating.",
    )
    caveats = (
        "**The fundamental screen (SEPA part 2) is NOT implemented.** "
        "yfinance carries 5 quarters of current-restatement financials; "
        "measuring growth acceleration needs 8+ quarters of point-in-time "
        "data. The daily screener attaches current fundamentals as watch "
        "flags; no backtest here includes them.",
        "Minervini raises the stop to breakeven once a trade advances. The "
        "portfolio simulator has no breakeven-raise mode, so backtests run a "
        "moving-average exit instead, which is more permissive.",
        "'Sell into strength' (taking partial profits into an unusually fast "
        "advance) is not modelled: positions here are all-or-nothing.",
        "The Trend Template is public and heavily data-mined. An in-sample "
        "edge on the same 13.75 years everything else here uses is weak "
        "evidence.",
        "The VCP thresholds are an interpretation calibrated for selectivity, "
        "not fitted to returns — but they are still choices, and a different "
        "reading of 'contraction' would give different trades.",
    )
    status = "Untested — no backtest has been run on this strategy yet."

    gate_docs = {
        "M1": "Close above the 50-day simple moving average.",
        "M2": "Close above the 150-day simple moving average.",
        "M3": "Close above the 200-day simple moving average.",
        "M4": "The averages stacked for a Stage-2 advance: 50-day above "
              "150-day above 200-day.",
        "M5": "The 200-day average is higher than it was "
              "{SMA200_RISING_BARS} sessions ago — rising for at least a month.",
        "M6": "Close at least {MIN_PCT_ABOVE_52W_LOW}% above the 52-week low, "
              "so the stock has already left its base behind.",
        "M7": "Close within {MAX_PCT_BELOW_52W_HIGH}% of the 52-week high — "
              "near highs, not recovering from a collapse.",
        "M8": "Relative strength proxy: 12-1 month momentum of at least "
              "{RS_MIN_MOM}. Stands in for an RS Rating of 70+, which is "
              "cross-sectional and cannot be computed per symbol.",
    }
    watch_docs = {
        "V1": "The final contraction is deeper than {VCP_IDEAL_TIGHT_PCT}% — "
              "a base, but not a tight one.",
        "V2": "Volume in the tight area has not dried up below its 50-day "
              "average, so sellers may not be exhausted.",
        "V3": "Fewer than {VCP_LEGS_TESTED} contraction legs: the pattern is "
              "present but shallowly evidenced.",
        "V4": "Price is more than {EXTENDED_ATR_ABOVE_SMA50} ATR above the "
              "50-day average — extended, with climax risk.",
        "V5": "Earnings are due inside the holding window, which can gap "
              "price straight through the stop.",
        "V6": "Price has run more than {MAX_PCT_ABOVE_PIVOT}% beyond the "
              "pivot, so the entry level has already passed — taking it now "
              "means chasing, and the stop would no longer sit just below "
              "the tight area.",
    }
    setup_docs = {
        MV01: "Volatility contraction complete and price has closed above the "
              "pivot — the high of the final tight area.",
        MV02: "Volatility contraction complete and price is coiled within "
              "{VCP_PROXIMITY_PCT}% below the pivot, not yet through it.",
    }
    entry_rules = (
        "Entry: a buy-stop at the pivot (the high of the final tight area) "
        "plus one tick.",
        "Stop: just below the low of the final tight area, and never more "
        "than {MAX_STOP_PCT}% below entry — a wider structural stop refuses "
        "the trade instead of stretching the cap.",
        "Target: a nominal {NOMINAL_TARGET_R}R, used only for sizing and "
        "reporting. The real exit is a rule, not a price.",
    )
    exit_rules = (
        "Live: cut at the stop without hesitation; raise the stop toward "
        "breakeven once the trade advances; sell into unusual strength and "
        "out of bad behaviour (heavy-volume declines, a break of key moving "
        "averages).",
        "Backtest: run with a 50-day moving-average exit and no fixed target "
        "(`--exit-mode ma --ma-col sma50 --no-target`), which approximates "
        "'sell into weakness' but models neither the breakeven raise nor "
        "partial profit-taking.",
    )
    param_docs = (
        ("Minimum above 52-week low", "MIN_PCT_ABOVE_52W_LOW", "Stage-2 stocks have left their lows."),
        ("Maximum below 52-week high", "MAX_PCT_BELOW_52W_HIGH", "Buy near highs, not in recovery."),
        ("200-day rising window", "SMA200_RISING_BARS", "Sessions the long average must have risen over."),
        ("RS momentum floor", "RS_MIN_MOM", "Per-symbol proxy for an RS Rating of 70+."),
        ("VCP lookback", "VCP_LOOKBACK", "Bars of base examined for contractions."),
        ("Contraction legs tested", "VCP_LEGS_TESTED", "How many recent pullbacks must shrink in sequence."),
        ("Tight-area ceiling", "VCP_TIGHT_PCT", "Deepest the final contraction may be."),
        ("Volume dry-up ratio", "VCP_DRY_VOLUME_RATIO", "Tight-area volume against its own 50-day average."),
        ("Maximum stop", "MAX_STOP_PCT", "His absolute loss limit; wider structural stops refuse the trade."),
        ("Maximum chase above pivot", "MAX_PCT_ABOVE_PIVOT", "Beyond this the breakout entry has passed."),
        ("Minimum history", "min_bars", "Bars required before the template can judge a symbol."),
    )
    backtest_args = "--strategy minervini --exit-mode ma --ma-col sma50 --no-target"

    # ---------- pre-filter ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        """The Trend Template IS the screen, so it belongs here rather than
        only in the gates: expressing it row-wise is what lets the backtest
        apply it as of each simulated bar instead of against today's row."""
        if cfg.screener.min_price and last["close"] < cfg.screener.min_price:
            return False, f"price {last['close']:.2f} < {cfg.screener.min_price}"
        if cfg.screener.min_dollar_volume:
            dv = last.get("dollar_vol_sma20")
            if pd.isna(dv) or dv < cfg.screener.min_dollar_volume:
                return False, f"liquidity below {cfg.screener.min_dollar_volume:,.0f}"

        close = float(last["close"])
        s50, s150, s200 = last.get("sma50"), last.get("sma150"), last.get("sma200")
        s200_prev = last.get("sma200_21d_ago")
        lo52, hi52 = last.get("low_252"), last.get("high_252")
        mom = last.get("mom_12_1")
        if any(pd.isna(v) for v in (s50, s150, s200, s200_prev, lo52, hi52, mom)):
            return False, "insufficient history for the trend template"

        if not (close > s50 and close > s150 and close > s200):
            return False, "price below one of the 50/150/200-day averages"
        if not (s50 > s150 > s200):
            return False, "moving averages not stacked 50 > 150 > 200"
        if not s200 > s200_prev:
            return False, "200-day average not rising"
        if lo52 <= 0 or close < lo52 * (1 + MIN_PCT_ABOVE_52W_LOW / 100):
            return False, f"less than {MIN_PCT_ABOVE_52W_LOW:g}% above the 52-week low"
        if hi52 <= 0 or close < hi52 * (1 - MAX_PCT_BELOW_52W_HIGH / 100):
            return False, f"more than {MAX_PCT_BELOW_52W_HIGH:g}% below the 52-week high"
        if mom < RS_MIN_MOM:
            return False, f"12-1 momentum {mom:.2f} below {RS_MIN_MOM}"
        return True, "passed"

    # ---------- gates ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        d = ctx.daily
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        last = ctx.last
        close = ctx.close

        s50 = float(last["sma50"]); s150 = float(last["sma150"])
        s200 = float(last["sma200"]); s200_prev = float(last["sma200_21d_ago"])
        lo52 = float(last["low_252"]); hi52 = float(last["high_252"])
        mom = float(last["mom_12_1"]) if pd.notna(last.get("mom_12_1")) else float("nan")

        # --- Trend Template ---
        _g(result, "M1", close > s50, f"close {close:.2f} vs SMA50 {s50:.2f}")
        _g(result, "M2", close > s150, f"close {close:.2f} vs SMA150 {s150:.2f}")
        _g(result, "M3", close > s200, f"close {close:.2f} vs SMA200 {s200:.2f}")
        _g(result, "M4", s50 > s150 > s200,
           f"SMA50 {s50:.2f} / SMA150 {s150:.2f} / SMA200 {s200:.2f}")
        _g(result, "M5", s200 > s200_prev,
           f"SMA200 {s200:.2f} vs {s200_prev:.2f} {SMA200_RISING_BARS} bars ago")

        pct_above_low = (close / lo52 - 1) * 100 if lo52 > 0 else float("nan")
        _g(result, "M6", pct_above_low >= MIN_PCT_ABOVE_52W_LOW,
           f"{pct_above_low:.1f}% above the 52-week low")
        pct_below_high = (1 - close / hi52) * 100 if hi52 > 0 else float("nan")
        _g(result, "M7", pct_below_high <= MAX_PCT_BELOW_52W_HIGH,
           f"{pct_below_high:.1f}% below the 52-week high")
        _g(result, "M8", pd.notna(mom) and mom >= RS_MIN_MOM,
           f"12-1 momentum {mom:.3f}")

        ctx.extras["pct_above_52w_low"] = pct_above_low
        ctx.extras["pct_below_52w_high"] = pct_below_high
        ctx.extras["rs_mom"] = mom

        # --- VCP structure ---
        contractions = sw.volatility_contractions(d, lookback=VCP_LOOKBACK)
        contracting = sw.is_contracting(
            contractions, min_legs=VCP_MIN_LEGS,
            tolerance=VCP_TOLERANCE_PP, last_n=VCP_LEGS_TESTED,
        )
        legs = len(contractions)
        last_depth = contractions[-1][1] if contractions else float("nan")
        pivot = contractions[-1][2] if contractions else None
        trough_ts = contractions[-1][0] if contractions else None

        # tight-area low and volume: the bars from the final trough to now
        tight_low = float("nan")
        vol_ratio = float("nan")
        if trough_ts is not None and trough_ts in d.index:
            tight = d.loc[trough_ts:]
            if not tight.empty:
                tight_low = float(tight["low"].min())
                vsma = float(d["vol_sma50"].iloc[-1])
                if vsma > 0:
                    vol_ratio = float(tight["volume"].mean()) / vsma

        ctx.extras["pivot"] = float(pivot) if pivot else None
        ctx.extras["tight_low"] = tight_low
        ctx.extras["contraction_legs"] = legs
        ctx.extras["last_contraction_pct"] = last_depth
        ctx.extras["tight_volume_ratio"] = vol_ratio

        tight_enough = pd.notna(last_depth) and last_depth <= VCP_TIGHT_PCT
        base_ok = bool(contracting and tight_enough and pivot and pivot > 0)

        if base_ok:
            through = close > float(pivot)
            near = (not through) and close >= float(pivot) * (1 - VCP_PROXIMITY_PCT / 100)
            result.setups[MV01] = bool(through)
            result.setups[MV02] = bool(near)
        else:
            result.setups[MV01] = False
            result.setups[MV02] = False

        self._watch_flags(ctx, result, last_depth, vol_ratio, legs, s50)
        result.recompute_first_fail()
        return result

    def _watch_flags(self, ctx, result, last_depth, vol_ratio, legs, s50) -> None:
        atr14 = ctx.atr
        result.watch_flags["V1"] = bool(
            pd.notna(last_depth) and last_depth > VCP_IDEAL_TIGHT_PCT
        )
        if result.watch_flags["V1"]:
            result.watch_notes["V1"] = f"final contraction {last_depth:.1f}%"
        result.watch_flags["V2"] = bool(
            pd.notna(vol_ratio) and vol_ratio > VCP_DRY_VOLUME_RATIO
        )
        if result.watch_flags["V2"]:
            result.watch_notes["V2"] = f"tight-area volume {vol_ratio:.2f}x its 50-day average"
        result.watch_flags["V3"] = bool(legs < VCP_LEGS_TESTED)
        if result.watch_flags["V3"]:
            result.watch_notes["V3"] = f"{legs} contraction leg(s)"
        extended = (
            pd.notna(atr14) and atr14 > 0
            and (ctx.close - s50) / atr14 > EXTENDED_ATR_ABOVE_SMA50
        )
        result.watch_flags["V4"] = bool(extended)
        if extended:
            result.watch_notes["V4"] = (
                f"{(ctx.close - s50) / atr14:.1f} ATR above SMA50"
            )
        ed = ctx.earnings_days_away
        result.watch_flags["V5"] = bool(ed is not None and 0 <= ed <= 10)
        if result.watch_flags["V5"]:
            result.watch_notes["V5"] = f"earnings in {ed} days"

        pivot = ctx.extras.get("pivot")
        past = bool(
            pivot and pivot > 0
            and (ctx.close / float(pivot) - 1) * 100 > MAX_PCT_ABOVE_PIVOT
        )
        result.watch_flags["V6"] = past
        if past:
            result.watch_notes["V6"] = (
                f"{(ctx.close / float(pivot) - 1) * 100:.1f}% above the pivot"
            )

    def watch_cap(self, result: StrategyResult) -> str:
        """V2 and V4 cap the tier: volume that never dried up means the base
        was not finished, and an extended entry is the one Minervini warns
        against most often. V1/V3 are informational."""
        caps = ["TRADE_HIGH_CONFIDENCE"]
        if result.watch_flags.get("V2"):
            caps.append("TRADE_ON_TRIGGER")
        if result.watch_flags.get("V4"):
            caps.append("WATCH_WAIT")
        if result.watch_flags.get("V6"):
            caps.append("WATCH_WAIT")
        return min(caps, key=CAP_ORDER.index)

    def setup_quality(self, result: StrategyResult) -> float:
        """Orders the daily report and breaks ties among setups.

        This deliberately does NOT carry relative strength: `setup_quality`
        receives only the StrategyResult, with no access to the price frame,
        so it cannot see momentum. Cross-sectional RS is applied where it
        belongs instead -- at slot competition, via the backtest's
        `--rank-by momentum`, which scores every signal point-in-time. Using a
        coarse setup score there was measured as costing 7.78pp of CAGR.
        """
        score = 2.0 if result.setups.get(MV01) else (1.0 if result.setups.get(MV02) else 0.0)
        if result.watch_flags.get("V2"):
            score -= 0.5   # volume never dried up
        if result.watch_flags.get("V4"):
            score -= 0.5   # extended entry
        return score

    # ---------- entry ----------

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        """MV-01 means the close is already through the pivot."""
        return bool(result.setups.get(MV01))

    def build_plans(
        self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig
    ) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no active setup")
        pivot = ctx.extras.get("pivot")
        tight_low = ctx.extras.get("tight_low")
        if not pivot or pivot <= 0 or tight_low is None or pd.isna(tight_low):
            return PlanChoice(None, None, "missing pivot / tight-area low")

        setup = MV01 if result.setups.get(MV01) else MV02
        # The pivot itself is where a resting buy-stop fills. Using today's
        # high instead would put the entry above a level price may already
        # have rejected intraday.
        entry = round_tick(float(pivot) * 1.001, cfg.tick_size, "up")

        # Structural stop: below the tight area. One tick under its low, so a
        # touch of the low is not already a stop-out.
        structural = round_tick(float(tight_low) - cfg.tick_size, cfg.tick_size, "down")
        if structural <= 0 or structural >= entry:
            return PlanChoice(None, None, "degenerate stop")

        stop_pct = (entry - structural) / entry * 100
        if stop_pct > MAX_STOP_PCT:
            # Part 4 is a constraint on WHICH trades exist, not a number to
            # stretch: a base whose support sits more than MAX_STOP_PCT below
            # the pivot cannot be bought at an acceptable loss, so it is
            # refused rather than entered on a clamped stop that no longer
            # corresponds to anything structural.
            return PlanChoice(
                None, None,
                f"structural stop {stop_pct:.1f}% exceeds the "
                f"{MAX_STOP_PCT:g}% maximum loss",
            )

        stop = structural
        target = entry + NOMINAL_TARGET_R * (entry - stop)
        plan = TradePlan(
            plan="MV", setup=setup, entry=entry, stop=stop, target=target,
            risk_per_share=entry - stop, reward_per_share=target - entry,
            r_multiple=NOMINAL_TARGET_R,
            nearest_overhead_above_entry=None,
        )
        return PlanChoice(
            plan, None,
            f"{setup}: pivot {pivot:.2f}, stop {stop_pct:.1f}% below entry",
        )

    # ---------- decision ----------

    def classify(
        self,
        ctx: StockContext,
        result: StrategyResult,
        plan: TradePlan,
        sizing_result,
        earnings_days_away: int | None,
        regime_downgrade_active: bool,
    ) -> Decision:
        reasons: list[str] = []
        if not result.hard_gates_passed:
            return Decision(
                LABELS["AVOID"], LABELS["AVOID"],
                f"fails trend template gate {result.first_hard_fail}: "
                f"{result.hard_notes.get(result.first_hard_fail, '')}",
                0.0, 0.0, self.setup_quality(result),
            )
        if plan is None or not plan.is_valid:
            return Decision(
                LABELS["AVOID"], LABELS["AVOID"], "no valid entry plan",
                0.0, 0.0, self.setup_quality(result),
            )

        label = "TRADE_HIGH_CONFIDENCE" if result.setups.get(MV01) else "WATCH_WAIT"
        if label == "TRADE_HIGH_CONFIDENCE":
            reasons.append("closed through the pivot")
        else:
            reasons.append("coiled below the pivot, waiting for the breakout")

        cap = self.watch_cap(result)
        if CAP_ORDER.index(cap) < CAP_ORDER.index(label):
            label = cap
            reasons.append(
                "capped by " + ",".join(
                    f for f in ("V2", "V4", "V6") if result.watch_flags.get(f)
                )
            )

        # `risk_pct` is the stop distance as a percentage of entry, computed
        # from the plan -- SizingResult has no such field, and reading it off
        # there with a getattr default silently reported 0.0 for every row.
        risk_pct = plan.risk_per_share / plan.entry * 100 if plan.entry else float("nan")
        if getattr(sizing_result, "shares", 0) < 1:
            label = min([label, "WATCH_WAIT"], key=CAP_ORDER.index)
            reasons.append("position would be smaller than one share")

        label_before = label
        if regime_downgrade_active:
            # Part of SEPA: trade smaller, or not at all, when the general
            # market is not supporting breakouts.
            #
            # But only ACTIONABLE tiers are downgraded. Demoting WATCH_WAIT
            # to AVOID removed every coiling base from the watchlist, which
            # is backwards: a weak tape is precisely when you want the list
            # of what is setting up, ready for the turn. A watchlist entry
            # carries no risk, so there is nothing to reduce.
            if label in ("TRADE_HIGH_CONFIDENCE", "TRADE_ON_TRIGGER"):
                label = DOWNGRADE_MAP[label]
                reasons.append("general market not supporting breakouts")
            else:
                reasons.append(
                    "general market not supporting breakouts (watchlist only)"
                )

        return Decision(
            LABELS[label_before], LABELS[label], "; ".join(reasons),
            risk_pct, plan.r_multiple, self.setup_quality(result),
        )

    def report_extras(
        self, ctx: StockContext, result: StrategyResult, plan: TradePlan | None
    ) -> dict:
        e = ctx.extras
        pivot = e.get("pivot")
        close = ctx.close
        return {
            "pivot": round(pivot, 2) if pivot else None,
            "pct_from_pivot": (
                round((close / pivot - 1) * 100, 2) if pivot else None
            ),
            "contraction_legs": e.get("contraction_legs"),
            "last_contraction_pct": (
                round(e["last_contraction_pct"], 2)
                if pd.notna(e.get("last_contraction_pct", float("nan"))) else None
            ),
            "tight_volume_ratio": (
                round(e["tight_volume_ratio"], 2)
                if pd.notna(e.get("tight_volume_ratio", float("nan"))) else None
            ),
            "pct_above_52w_low": (
                round(e["pct_above_52w_low"], 1)
                if pd.notna(e.get("pct_above_52w_low", float("nan"))) else None
            ),
            "pct_below_52w_high": (
                round(e["pct_below_52w_high"], 1)
                if pd.notna(e.get("pct_below_52w_high", float("nan"))) else None
            ),
            "rs_mom": (
                round(e["rs_mom"], 3)
                if pd.notna(e.get("rs_mom", float("nan"))) else None
            ),
        }


def _g(result: StrategyResult, code: str, passed: bool, note: str) -> None:
    (result.ok if passed else result.fail)(code, note)
