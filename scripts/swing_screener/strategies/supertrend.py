"""Supertrend — an ATR band that flips with the trend, traded long-only.

Supertrend (Olivier Seban) is a volatility channel around the bar's midpoint, (high + low) / 2
± a multiple of ATR, whose bands only ratchet in the trend's direction. The trend turns up when
a close clears the upper band and down when a close breaks the lower one; in an up-trend the
line drawn is the lower band, which rises and never falls. The Learn guide on price oscillators
lists it with its common default, Supertrend(10, 3).

The trade is the indicator read literally: buy the session after the line turns up, sell at
the close that turns it down. Nothing else decides — no pattern, no volume, no target. It is a
second trend-following experiment beside `donchian`, with an exit that adapts to volatility
instead of a fixed channel length.

One implementation of the line
-----------------------------
`core.indicators.SupertrendState` is the rule. It is a transcription of the chart's Supertrend
study (web/static/studies.js, `st`), including its SMA-seeded ATR, so the chart and the strategy
draw the same line on the same bars. The backtest's exit (`--exit-mode supertrend` in
backtesting/portfolio_sim.py) runs the same function with this module's constants.
"""

import pandas as pd

from ..config.base import MarketConfig
from ..core.context import StockContext
from ..core.indicators import SupertrendState
from ..marketdata import corporate_actions
from .base import (
    tradable_point_in_time,
    DOWNGRADE_MAP,
    LABELS,
    Decision,
    PlanChoice,
    Strategy,
    StrategyResult,
    TradePlan,
)
from .trend_pullback import round_tick

ATR_PERIOD = 10           # the ATR's length; the chart study's and the Learn guide's default
MULTIPLIER = 3            # band distance from the midpoint, in ATRs; ditto
REQUIRE_SMA200 = 1        # 1: G1 (close above the 200-day) is a hard gate; 0: G1 always passes
MAX_STOP_PCT = 20         # a flip whose line is further than this % below the entry is not bought
NOMINAL_TARGET_ATR = 10   # a far target for the plan's R column only; the backtest has no target

S1 = "S1"   # the Supertrend turned up today


# Per-symbol stepping state, so a scan over a growing slice of one history extends the line
# bar by bar instead of recomputing it (the line at a bar depends only on bars up to it).
_CACHE: dict = {}
_cache_max = 6000


def supertrend_rows(symbol: str, daily: pd.DataFrame) -> list[tuple]:
    """(line, dir, upper, lower) for every bar of `daily`, under ATR_PERIOD and MULTIPLIER."""
    key = (symbol, ATR_PERIOD, float(MULTIPLIER))
    n = len(daily)
    c = _CACHE.get(key)
    if c is not None:
        m = len(c["rows"])
        k = min(m, n) - 1
        same = (k >= 0 and c["first"] == daily.index[0] and c["dates"][k] == daily.index[k]
                and c["closes"][k] == float(daily["close"].iat[k]))
        if not same:
            c = None
        elif m >= n:
            return c["rows"][:n]
    if c is None:
        if len(_CACHE) >= _cache_max:
            _CACHE.clear()
        c = _CACHE[key] = {"first": daily.index[0] if n else None, "dates": [], "closes": [], "rows": [],
                           "state": SupertrendState(ATR_PERIOD, MULTIPLIER)}
    st, start = c["state"], len(c["rows"])
    tail = daily.iloc[start:]
    for ts, h, l, cl in zip(tail.index, tail["high"].to_numpy(float), tail["low"].to_numpy(float),
                            tail["close"].to_numpy(float)):
        c["rows"].append(st.step(h, l, cl))
        c["dates"].append(ts)
        c["closes"].append(float(cl))
    return c["rows"]


class SupertrendStrategy(Strategy):
    selection = "time_series"
    version = "1.0"
    changelog = (
        ("1.0", "2026-10-26",
         "v1 baseline: buy the session after Supertrend({ATR_PERIOD}, {MULTIPLIER}) turns up above the "
         "200-day, sell at the close that turns it down."),
    )
    key = "supertrend"
    name = "Supertrend"
    description = (
        "Trend following on an ATR band: buy when Supertrend turns up, sell at the close that "
        "turns it down."
    )
    style = "trend"
    gate_codes = ("G1",)
    screen_key = "above_200"
    screen_gates = {"G1": "A1"}
    watch_codes = ()
    setup_codes = (S1,)
    setup_names = {S1: "Supertrend turns up"}
    gate_titles = {"G1": "Above the 200-day"}
    # the target is only for sizing: the trade ends when the Supertrend turns down
    nominal_target = True
    min_bars = 260

    needs_ctx_extras = True
    extra_columns = ("st_line", "st_upper", "st_prev_upper", "pct_above_line")
    extra_numeric_columns = extra_columns
    signal_exempt_consts = ("MAX_STOP_PCT", "NOMINAL_TARGET_ATR")

    thesis = (
        "Trends persist, and a volatility band that only moves with the trend is a simple way to "
        "stay in one: buy when the band says the trend turned up, hold until it says it turned "
        "down. The edge, if any, is in the few long trends, paid for with many small whipsaws."
    )
    how_it_works = (
        "**The idea.** Read the Supertrend({ATR_PERIOD}, {MULTIPLIER}) line literally on a long-only "
        "stock book: in when it turns up, out when it turns down.",
        "**The line.** The bar's midpoint, (high + low) / 2, plus and minus {MULTIPLIER} × ATR"
        "{ATR_PERIOD}. The upper band only falls and the lower band only rises, until a close "
        "crosses them. The trend turns up on a close above yesterday's upper band and down on a "
        "close below yesterday's lower band. In an up-trend the line is the lower band.",
        "**Qualify.** A liquidity floor, then one hard gate: a close above the 200-day average (G1).",
        "**Signal.** S1, the session the line turns up. Only that session: a stock already in an "
        "up-trend is not bought later.",
        "**Buy.** At the next session's open. The stop is the line on the signal session, and the "
        "trade is skipped if that is more than {MAX_STOP_PCT}% under the price paid.",
        "**Sell.** At the first close that turns the line down. The stop on the signal session "
        "stays as an intraday stop in case of a crash. There is no target.",
        "**What the backtest buys.** Only TRADE - HIGH CONFIDENCE: S1 with G1 passing and a stop no "
        "more than {MAX_STOP_PCT}% under the entry. Ties between same-day signals go to the "
        "stronger 12-1 month momentum.",
    )
    caveats = (
        "**Not yet measured.** No backtest has judged it (see Status).",
        "**Not a futures portfolio.** Trend following's track record is in diversified futures "
        "traded long and short. A long-only, single-market stock book has neither. `donchian`, the "
        "same idea with a channel, showed no edge in-sample.",
        "**A low win rate by design.** A whipsaw is a small loss; judge it on expectancy and the "
        "size of its winners.",
        "**Wide first stop.** At a turn-up the line is {MULTIPLIER} ATR{ATR_PERIOD} under the bar's "
        "midpoint. Measured with the defaults on every turn-up of 96 sampled stocks (2026-10-26, any "
        "date, no other filter): the close sat a median 3.4 ATR14 above the line, 12.6% (US) and 13.6% "
        "(India) of price, and over 20% on 24% (US) and 14% (India) of turn-ups. Risk-based sizing "
        "keeps the loss at 1R, so positions are small; turn-ups with a stop over {MAX_STOP_PCT}% are "
        "not bought.",
        "**Run it with its exit flags.** `--exit-mode supertrend --no-target` (the page's backtest "
        "command adds them). Without them the default bracket sells everything at the nominal target.",
        "**The chart's line is the same line.** The chart's Supertrend study and this strategy use "
        "one definition (SMA-seeded ATR, the same band ratchet and flip tests). Its default inputs, "
        "10 and 3, are this strategy's {ATR_PERIOD} and {MULTIPLIER}; a variant run with other "
        "constants matches the chart only when the study's inputs are set to the same numbers.",
        "**The fill session is never checked.** In the backtest the stop and the flip exit are "
        "first tested on the session after the fill. A line that turns down on the fill session "
        "itself sells at the next session's close, if the line is still down then.",
        "**Long only.** A down-turn only ends a trade; it never opens a short.",
        corporate_actions.CAVEAT_TRADED,
    )

    status = (
        "No demonstrated edge; failed its pass criterion, so verify was not run. Pass criterion, set "
        "before any result: in the optimise stage, the base rules beat the market's benchmark CAGR "
        "with a max drawdown no worse than the benchmark's plus 10 points, and a positive average R, "
        "in at least one market. Optimise stage (2013-2021, in-sample, v1.0, measured 2026-10-27): "
        "India 8.34% CAGR vs 13.54% (max drawdown -27.6% vs -38.3%, 461 trades, win rate 41.7%, "
        "+0.22R a trade); US 0.90% vs 14.01% (max drawdown -34.8% vs -34.1%, 658 trades, 36.6%, "
        "+0.04R). Neither up-front variant beat the index either: MULTIPLIER=2 India 6.36% / US "
        "-1.17%; REQUIRE_SMA200=0 India 7.01% / US 4.18%."
    )
    gate_docs = {
        "G1": (
            "Close above the 200-day average (the Above-the-200-day screen's A1).\n\n"
            "- **Test:** today's close is strictly above today's 200-day simple moving average of closes.\n"
            "- **Fails:** a close at or below it, or no average yet (fewer than 200 closes).\n"
            "- **Off switch:** with REQUIRE_SMA200 = 0 (now {REQUIRE_SMA200}) the gate always passes.\n\n"
            "The one concession to trend in a long-only stock book."
        ),
    }
    watch_docs = {}
    setup_docs = {
        S1: (
            "The Supertrend({ATR_PERIOD}, {MULTIPLIER}) line turns up today.\n\n"
            "- **ATR:** ATR{ATR_PERIOD}, an RMA of the true range seeded with the simple average of its "
            "first {ATR_PERIOD} values.\n"
            "- **Bands:** (high + low) / 2 ± {MULTIPLIER} × ATR. The final upper band takes the new value "
            "only if it is lower, or if yesterday's close was above the old one; the final lower band "
            "only if it is higher, or if yesterday's close was below the old one.\n"
            "- **Test:** yesterday the trend was down and today's close is above yesterday's final "
            "upper band.\n"
            "- **Signal:** the setup is the entry signal (setup quality 2). It fires once per turn, "
            "never on later sessions of the same up-trend."
        ),
    }
    entry_rules = (
        "Signal. An S1 turn-up with G1 passing, graded TRADE - HIGH CONFIDENCE.",
        "Order. Buy at the next session's open, that session only. The plan's entry is the signal "
        "session's close, a nominal number; the price paid is the open.",
        "Stop test at the fill (backtest). If the stop is more than {MAX_STOP_PCT}% under the price "
        "paid, the order is skipped.",
        "One position per stock (backtest). A signal in a stock already held is ignored.",
    )
    stop_rules = (
        "Where it goes. The Supertrend line on the signal session, the final lower band, rounded "
        "down to the tick.",
        "It defines 1R. The distance from the price paid to the stop is the trade's risk.",
        "How far is too far. More than {MAX_STOP_PCT}% under the entry is WATCH - WAIT live and "
        "skipped in the backtest.",
        "How it sells (backtest). A standing sell order: the first session whose low touches it "
        "sells at the stop, or at the open if it opened below it.",
        "It never moves. The line rises with the trend, but it acts on closes: see Exit.",
    )
    target_rules = (
        "There is no sell order at the target. The target is entry + {NOMINAL_TARGET_ATR} × ATR14, "
        "so that the plan has an R column. The backtest runs with `--no-target`.",
    )
    exit_rules = (
        "The turn-down (backtest). Each session after the fill, the stop is checked first. If it "
        "did not sell, a close that turns the Supertrend down -- a close below the previous "
        "session's final lower band -- sells the whole position at that close.",
        "The line is computed over each stock's whole stored history with the same constants "
        "(`--exit-mode supertrend` reads ATR_PERIOD and MULTIPLIER from this strategy).",
        "Live, the screen shows the line; nothing manages an open position.",
        "No other exits. No target, time stop, breakeven or partial sale. A position still open when "
        "the backtest ends is marked at the last close.",
    )
    sizing_rules = (
        "Risk-based. Shares = (equity × Risk per trade) ÷ (price paid − stop), rounded down, capped "
        "at Max position size × equity.",
        "Cash. When cash cannot buy the full size, the backtest buys what it can.",
        "Slots. At most Position cap positions at once. A next-open order with no free slot is "
        "dropped.",
    )
    filter_rules = (
        "Thin stocks. The 20-day average of close × volume must be at least the Minimum liquidity.",
        "Too little history. At least {min_bars} daily bars and a usable ATR14.",
        "No price floor and no earnings rule, live or in the backtest.",
        "Market regime. Live, a risk-off market lowers every decision one tier. The backtest does "
        "not apply it.",
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "G1 passes, the line turned up today (S1), the stop is no more than "
                                 "{MAX_STOP_PCT}% under the entry and one share fits the account. The "
                                 "only tier the backtest buys.",
        "TRADE_ON_TRIGGER": "Only a HIGH CONFIDENCE lowered by a risk-off market.",
        "WATCH_WAIT": "The stop would be more than {MAX_STOP_PCT}% under the entry, or not even one "
                      "share fits the account, or a TRADE ON TRIGGER lowered by a risk-off market.",
        "AVOID": "G1 failed, or the plan's risk is not a positive number.",
    }
    param_docs = (
        ("ATR period", "ATR_PERIOD", "Length of the ATR the bands are built from."),
        ("Multiplier", "MULTIPLIER", "Band distance from the bar's midpoint, in ATRs."),
        ("200-day gate", "REQUIRE_SMA200", "1: G1 is a hard gate; 0: it always passes."),
        ("Maximum stop", "MAX_STOP_PCT", "A turn-up whose line is further than this % under the "
                                         "entry is not bought."),
        ("Nominal target", "NOMINAL_TARGET_ATR", "Target = entry + this × ATR14, for the R column only."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume",
         "Pre-filter: the 20-day average of close × volume must be at least this."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Max position size", "cfg.max_position_pct", "Cap on one position's value as a fraction of equity."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
        ("Tick size", "cfg.tick_size", "The stop is rounded down to this increment."),
        ("Slippage", "cfg.slippage_bps", "Backtest cost per side, in basis points of the fill price."),
    )
    backtest_args = "--exit-mode supertrend --no-target --rank-by setup_momentum"

    # ---------- screen ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        ok, why = tradable_point_in_time(cfg, last)
        if not ok:
            return False, why
        if pd.isna(last.get("atr14")) or not last.get("atr14"):
            return False, "no ATR"
        return True, "passed"

    # ---------- gates ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        rows = supertrend_rows(ctx.symbol, ctx.daily)
        line, direction, upper, _ = rows[-1]
        prev_dir, prev_upper = (rows[-2][1], rows[-2][2]) if len(rows) > 1 else (0, float("nan"))
        ctx.extras["st_line"] = line
        ctx.extras["st_upper"] = upper
        ctx.extras["st_prev_upper"] = prev_upper

        if REQUIRE_SMA200:
            self.apply_screen(ctx, result)
        else:
            result.ok("G1", "200-day gate off")

        result.setups[S1] = bool(prev_dir == -1 and direction == 1)
        result.recompute_first_fail()
        return result

    def setup_quality(self, result: StrategyResult) -> float:
        return 2.0 if result.setups.get(S1) else 0.0

    # ---------- entry ----------

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        return bool(result.setups.get(S1))

    def build_plans(self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no active setup")
        line, atr14 = ctx.extras.get("st_line"), ctx.atr
        if line is None or line != line or pd.isna(atr14) or not atr14:
            return PlanChoice(None, None, "missing Supertrend/ATR")
        entry = float(ctx.close)
        stop = round_tick(float(line), cfg.tick_size, "down")
        target = entry + NOMINAL_TARGET_ATR * atr14
        plan = TradePlan(
            plan="ST", setup=S1, entry=entry, stop=stop, target=target,
            risk_per_share=entry - stop, reward_per_share=target - entry,
            r_multiple=(target - entry) / (entry - stop) if entry > stop else float("nan"),
            nearest_overhead_above_entry=None,
        )
        return PlanChoice(plan, None, f"Supertrend turned up; line {line:.2f}")

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        return {"order": "open", "max_risk_pct": MAX_STOP_PCT / 100}

    # ---------- decision ----------

    def classify(self, ctx, result, plan, sizing_result, earnings_days_away, regime_downgrade_active) -> Decision:
        if not result.hard_gates_passed:
            code = result.first_hard_fail
            return Decision("AVOID", "AVOID", f"fails hard gate {code}: {result.hard_notes.get(code, '')}",
                            float("nan"), float("nan"), 0.0)
        if not plan.is_valid:
            return Decision("AVOID", "AVOID", "degenerate plan (non-positive or undefined risk)",
                            float("nan"), float("nan"), 0.0)
        risk_pct = plan.risk_per_share / plan.entry * 100
        if sizing_result.too_large:
            label, reasons = "WATCH_WAIT", ["too large for account"]
        elif risk_pct > MAX_STOP_PCT:
            label, reasons = "WATCH_WAIT", [f"line is {risk_pct:.1f}% under the entry (> {MAX_STOP_PCT}%)"]
        else:
            label, reasons = "TRADE_HIGH_CONFIDENCE", [f"Supertrend({ATR_PERIOD}, {MULTIPLIER:g}) turned up"]
        before = label
        if regime_downgrade_active and label != "AVOID":
            label = DOWNGRADE_MAP[label]
            reasons.append("market-regime downgrade applied")
        return Decision(LABELS[before], LABELS[label], "; ".join(reasons),
                        risk_pct, plan.r_multiple, self.setup_quality(result))

    def report_extras(self, ctx: StockContext, result: StrategyResult, plan: TradePlan | None) -> dict:
        e = ctx.extras
        r = lambda v: round(float(v), 2) if v is not None and v == v else None
        line = e.get("st_line")
        return {"st_line": r(line), "st_upper": r(e.get("st_upper")), "st_prev_upper": r(e.get("st_prev_upper")),
                "pct_above_line": r((ctx.close / line - 1) * 100) if line and line == line else None}

    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The line the trade was bought on and the band the close cleared."""
        e = sig.get("extras") or {}
        d = str(sig["date"])
        out: list[dict] = []
        if e.get("st_prev_upper"):
            out.append({"shape": "level", "bars": 5, "to": d, "price": float(e["st_prev_upper"]),
                        "role": "pivot", "label": f"upper band {e['st_prev_upper']:g} — a close above turns it up"})
        if e.get("st_line"):
            out.append({"shape": "level", "bars": 5, "to": d, "price": float(e["st_line"]),
                        "role": "support", "label": f"Supertrend {e['st_line']:g} — the stop; a close below "
                                                    f"the rising line sells"})
            out.append({"shape": "note", "at": d, "price": float(e["st_line"]),
                        "text": f"Supertrend entry {d}: the line turned up. No pattern claim — the turn IS the "
                                f"signal; the trade ends at the close that turns it down."})
        return out or super().chart_anatomy(sig)
