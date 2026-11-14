"""Stock mean reversion — Connors-style RSI(2) dips in single stocks above their 200-day.

Every other per-symbol strategy here buys strength: a breakout, a new high, a trend turning up. This
one buys weakness. A liquid stock in a long-term uptrend (close above its 200-day average) that has
just sold off hard for a few sessions -- RSI(2) under {RSI_ENTRY} -- tends to bounce within days. Buy
the next session's open, sell the first close above the 5-day average, and give up after
{MAX_HOLD_BARS} sessions if the bounce does not come. This is the rule as Connors and Alvarez
published it (Short Term Trading Strategies That Work, 2008); its constants were fixed before the
first run and are not tuned on results.

Why it is here
--------------
Of 31 strategies, 27 are trend/momentum bets and the two mean reversion ones are index-only
(`backtesting/mean_reversion.py`) or a short. Short-term reversal in single stocks is one of the
best-documented anomalies (Jegadeesh 1990; Lehmann 1990), and in a book of trend strategies its
value may lie as much in behaving differently -- low correlation with the momentum strategies --
as in its own return. It is judged on both.

Where the rules live
--------------------
The oversold tests read three columns `core.indicators.enrich_daily` computes for every stock
(`rsi2`, `close_sd20`, `down_streak`) through `setup_flags`, the one implementation the pre-filter
and `evaluate` share. The exit is `--exit-mode revert` in `backtesting/portfolio_sim.py`, which reads
this module's EXIT_SMA, EXIT_ON_RSI, EXIT_RSI and MAX_HOLD_BARS, so a `--const` variant moves the
backtest's exit too.
"""

import pandas as pd

from ..config.base import MarketConfig
from ..core.context import StockContext
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

# ---- the setup (which oversold test buys). SETUP_RULE picks one: 1 RSI(2), 2 Bollinger, 3 lower closes
SETUP_RULE = 1
RSI_ENTRY = 10            # S1: RSI(2) of the close below this
BB_SD = 2                 # S2: the close below the 20-day average minus this many 20-day standard deviations
DOWN_CLOSES = 3           # S3: at least this many lower closes in a row
DROP_BARS = 3             # the drop the ranking switch reads: the close against the close this many sessions ago

# ---- after the scan (signal_exempt_consts): entry, stop, exit, ranking
ENTRY_LIMIT_PCT = 0       # 0: buy the next session's open; > 0: a buy limit this % under the signal close, next session only
CATASTROPHE_ATR = 0       # 0: no stop (the published rule); > 0: a stop this many ATR14 under the signal close
EXIT_SMA = 5              # sell on the first close above the simple average of this many closes
EXIT_ON_RSI = 0           # 1: sell instead on the first close whose RSI(2) is above EXIT_RSI (the average is not used)
EXIT_RSI = 70
MAX_HOLD_BARS = 5         # time stop: sold at the close of this session after the fill session (0 = none)
RANK_BY_DROP = 0          # 0: same-day signals ranked by the lowest RSI(2); 1: by the largest DROP_BARS-day drop
NOMINAL_TARGET_PCT = 100  # a far target for the plan's R column only; the backtest has no target

S1, S2, S3 = "S1", "S2", "S3"
SETUP_BY_RULE = {1: S1, 2: S2, 3: S3}


def setup_flags(row) -> dict:
    """{S1, S2, S3: did this enriched daily row pass that oversold test}. NaN fails every test."""
    def num(k):
        v = row.get(k)
        return float(v) if v is not None and pd.notna(v) else float("nan")
    close, rsi2, sma20, sd20, streak = (num(k) for k in ("close", "rsi2", "sma20", "close_sd20", "down_streak"))
    return {
        S1: bool(rsi2 < RSI_ENTRY),
        S2: bool(close < sma20 - BB_SD * sd20),
        S3: bool(streak >= DOWN_CLOSES),
    }


def entry_setup() -> str:
    """The setup code SETUP_RULE makes the entry."""
    if int(SETUP_RULE) not in SETUP_BY_RULE:
        raise ValueError(f"SETUP_RULE must be one of {sorted(SETUP_BY_RULE)}, not {SETUP_RULE}")
    return SETUP_BY_RULE[int(SETUP_RULE)]


class StockReversionStrategy(Strategy):
    selection = "time_series"
    behaviour = "mean_reversion"
    # `pullback` from the existing styles, as the index mean reversion and the parabolic short use:
    # buying a dip inside an uptrend is a pullback entry with a reversion exit.
    style = "pullback"
    horizon = "swing"
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-14",
         "v1 baseline, the published Connors rule fixed before any run: a liquid stock above its 200-day "
         "with RSI(2) under {RSI_ENTRY}, bought at the next open, sold on the first close above the "
         "{EXIT_SMA}-day average or after {MAX_HOLD_BARS} sessions, no stop, equal weight. Switches for "
         "the variants: SETUP_RULE (Bollinger, lower closes), ENTRY_LIMIT_PCT, EXIT_ON_RSI, "
         "CATASTROPHE_ATR, RANK_BY_DROP."),
    )
    key = "stock_reversion"
    name = "Stock mean reversion"
    description = (
        "Buys a short, sharp dip (RSI(2) under {RSI_ENTRY}) in a liquid stock above its 200-day; sells the "
        "first close above the {EXIT_SMA}-day average."
    )
    gate_codes = ("G1",)
    screen_key = "above_200"
    screen_gates = {"G1": "A1"}
    watch_codes = ()
    setup_codes = (S1, S2, S3)
    setup_names = {S1: "RSI(2) oversold", S2: "Close under the lower Bollinger band",
                   S3: "Lower closes in a row"}
    gate_titles = {"G1": "Above the 200-day"}
    nominal_target = True
    min_bars = 220

    needs_ctx_extras = True
    extra_columns = ("rsi2", "bb_lower", "down_streak", "drop_pct", "atr14")
    extra_numeric_columns = extra_columns
    signal_exempt_consts = ("ENTRY_LIMIT_PCT", "CATASTROPHE_ATR", "EXIT_SMA", "EXIT_ON_RSI", "EXIT_RSI",
                            "MAX_HOLD_BARS", "RANK_BY_DROP", "NOMINAL_TARGET_PCT")

    thesis = (
        "A stock in a long-term uptrend that has sold off sharply for a few sessions tends to bounce "
        "within days: short-term overreaction, liquidity demand and the reversal effect documented in "
        "single stocks since Jegadeesh (1990) and Lehmann (1990). Buy the dip, sell the bounce. The trades "
        "are short and many, and they buy weakness where every momentum strategy here buys strength, so "
        "the book should behave differently from theirs."
    )
    how_it_works = (
        "**The idea.** Connors and Alvarez's RSI(2) rule on single stocks: buy a short, sharp dip inside a "
        "long-term uptrend, sell on the first sign of a bounce.",
        "**Qualify.** A liquidity floor, then one hard gate: a close above the 200-day average (G1).",
        "**Signal.** The oversold test SETUP_RULE picks (now {SETUP_RULE}): S1 RSI(2) under {RSI_ENTRY} "
        "(the base rule), S2 a close under the lower 20-day, {BB_SD}-SD Bollinger band, or S3 "
        "{DOWN_CLOSES} or more lower closes in a row. Every session that passes is a signal.",
        "**Buy.** At the next session's open (ENTRY_LIMIT_PCT = {ENTRY_LIMIT_PCT}); with ENTRY_LIMIT_PCT "
        "above 0, a buy limit that % under the signal close, for the next session only.",
        "**Sell.** At the first close above the {EXIT_SMA}-day simple average, the fill session included "
        "(with EXIT_ON_RSI = 1, the first close whose RSI(2) is above {EXIT_RSI} instead), or at the close "
        "of the {MAX_HOLD_BARS}th session after the fill session. No stop in the base rule; "
        "CATASTROPHE_ATR above 0 adds one that many ATR14 under the signal close.",
        "**Size and rank.** Equal weight, one tenth of equity a position (`--equal-alloc 10` with the "
        "market's ten slots). When more signals than free slots arrive on one day, the lowest RSI(2) "
        "goes first (RANK_BY_DROP = 1: the largest {DROP_BARS}-day drop).",
    )
    caveats = (
        "**Measured in-sample only.** See Status for the optimise-stage results; verify has not been run.",
        "**No stop in the base rule.** The published rule has none: a stock that keeps falling is held "
        "until the time stop, {MAX_HOLD_BARS} sessions. A gap down on bad news is taken in full. The "
        "CATASTROPHE_ATR switch tests a {CATASTROPHE_ATR}-ATR stop (3 in the variant run).",
        "**R is not meaningful without a stop.** With no stop the plan's stop is 0, so a trade's R is its "
        "return as a fraction of the price paid; judge it on returns, win rate and hold, not on R.",
        "**Costs matter more here.** Trades last days and the edge per trade is small, so slippage and "
        "costs take a larger share than in a trend strategy.",
        "**Survivorship and the 200-day filter.** The universe is today's stored stocks; a stock that "
        "later delisted after a dip that never bounced is under-represented, which flatters a dip-buyer "
        "more than a momentum strategy.",
        "**Run it with its exit flags.** `--exit-mode revert --no-target --equal-alloc 10` (the page's "
        "backtest command adds them). Without them the default bracket would sell at the nominal target "
        "and size from the (absent) stop.",
        "**The fill session counts.** A position bought at the open whose close that same session is "
        "already above the {EXIT_SMA}-day average is sold at that close.",
        corporate_actions.CAVEAT_TRADED,
    )
    status = (
        "Not yet measured: the optimise-stage runs are queued. Pass criteria, written before any result "
        "(in-sample, optimise stage 2013-2021): excess CAGR above 0 against the benchmark held at the "
        "same exposure, OR a positive CAGR with monthly-return correlation below 0.3 to both Momentum "
        "baseline and Minervini SEPA over the same window, with at least 200 trades."
    )
    gate_docs = {
        "G1": (
            "Close above the 200-day average (the Above-the-200-day screen's A1).\n\n"
            "- **Test:** today's close is strictly above today's 200-day simple moving average of closes.\n"
            "- **Fails:** a close at or below it, or no average yet (fewer than 200 closes).\n\n"
            "Connors' trend filter: buy dips in uptrends, never falling knives in downtrends."
        ),
    }
    watch_docs = {}
    setup_docs = {
        S1: (
            "RSI(2) under {RSI_ENTRY} — the base rule's entry (SETUP_RULE = 1).\n\n"
            "- **RSI(2):** Wilder's RSI over 2 sessions of closes (the average gain and loss smoothed with "
            "alpha 1/2).\n"
            "- **Test:** today's RSI(2) is below {RSI_ENTRY}: two or so sharply lower closes.\n"
            "- **Signal:** the entry only when SETUP_RULE = 1 (now {SETUP_RULE}); otherwise not recorded."
        ),
        S2: (
            "A close under the lower Bollinger band (SETUP_RULE = 2).\n\n"
            "- **Band:** the 20-day simple average minus {BB_SD} × the 20-day standard deviation of closes.\n"
            "- **Test:** today's close is strictly below it.\n"
            "- **Signal:** the entry only when SETUP_RULE = 2."
        ),
        S3: (
            "{DOWN_CLOSES} or more lower closes in a row (SETUP_RULE = 3).\n\n"
            "- **Test:** each of the last {DOWN_CLOSES} closes is below the close before it.\n"
            "- **Signal:** the entry only when SETUP_RULE = 3."
        ),
    }
    entry_rules = (
        "Signal. The SETUP_RULE setup with G1 passing, graded TRADE - HIGH CONFIDENCE.",
        "Order. ENTRY_LIMIT_PCT = 0 (now {ENTRY_LIMIT_PCT}): buy at the next session's open, that session "
        "only. Above 0: a buy limit ENTRY_LIMIT_PCT % under the signal close for the next session only; it "
        "fills at the open if the stock opens at or under it, else at the limit if the session trades down "
        "to it, and is dropped otherwise.",
        "The plan's entry is the signal session's close, a nominal number; the price paid is the fill.",
        "One position per stock (backtest). A signal in a stock already held is ignored.",
    )
    stop_rules = (
        "None in the base rule (CATASTROPHE_ATR = 0, now {CATASTROPHE_ATR}): the plan's stop is 0, which "
        "never triggers.",
        "With CATASTROPHE_ATR above 0: the signal close minus CATASTROPHE_ATR × ATR14, rounded down to the "
        "tick, as a standing sell order from the fill on; a gap through it sells at the open.",
    )
    target_rules = (
        "There is no sell order at the target. The target is entry + {NOMINAL_TARGET_PCT}% so that the "
        "plan has an R column; the backtest runs with `--no-target`.",
    )
    exit_rules = (
        "The bounce (backtest, `--exit-mode revert`). From the fill session on, after the stop if there "
        "is one: a close above the {EXIT_SMA}-day simple average sells the whole position at that close "
        "(MEAN_REVERTED).",
        "The RSI switch. With EXIT_ON_RSI = 1 (now {EXIT_ON_RSI}) the bounce is instead a close whose RSI(2) "
        "is above {EXIT_RSI}; the average is then not used.",
        "The time stop. If neither has happened, the close of the {MAX_HOLD_BARS}th session after the fill "
        "session sells the position (TIME).",
        "Live, the screen lists today's signals; nothing manages an open position.",
    )
    sizing_rules = (
        "Equal weight. Each position is bought for one tenth of equity (`--equal-alloc 10`), whatever its "
        "stop, so the time the book is invested measures how often the rule finds dips.",
        "Cash. When cash cannot buy the full size, the backtest buys what it can.",
        "Slots. At most Position cap positions at once. A next-session order with no free slot is dropped.",
        "Ranking. Same-day signals compete for slots by the lowest RSI(2) (RANK_BY_DROP = 0, now "
        "{RANK_BY_DROP}) or, with RANK_BY_DROP = 1, the largest drop over {DROP_BARS} sessions.",
    )
    filter_rules = (
        "Thin stocks. The 20-day average of close × volume must be at least the Minimum liquidity.",
        "Too little history. At least {min_bars} daily bars and a usable ATR14.",
        "The pre-filter also needs the SETUP_RULE setup on that row, so only oversold sessions are "
        "evaluated (the same test, `setup_flags`, that evaluate() records).",
        "No price floor and no earnings rule, live or in the backtest.",
        "Market regime. Live, a risk-off market lowers every decision one tier. The backtest does not "
        "apply it.",
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "G1 passes and the SETUP_RULE setup fired today. The only tier the backtest buys.",
        "TRADE_ON_TRIGGER": "Only a HIGH CONFIDENCE lowered by a risk-off market.",
        "WATCH_WAIT": "Only a TRADE ON TRIGGER lowered by a risk-off market.",
        "AVOID": "G1 failed, or the plan's risk is not a positive number.",
    }
    param_docs = (
        ("Setup rule", "SETUP_RULE", "Which oversold test is the entry: 1 RSI(2), 2 Bollinger, 3 lower closes."),
        ("RSI entry", "RSI_ENTRY", "S1: RSI(2) below this."),
        ("Band width", "BB_SD", "S2: standard deviations under the 20-day average."),
        ("Lower closes", "DOWN_CLOSES", "S3: lower closes in a row."),
        ("Drop window", "DROP_BARS", "Sessions the ranking switch's drop is measured over."),
        ("Limit entry", "ENTRY_LIMIT_PCT", "0: next open; above 0: a buy limit this % under the signal close."),
        ("Catastrophe stop", "CATASTROPHE_ATR", "0: no stop; above 0: a stop this many ATR14 under the signal close."),
        ("Exit average", "EXIT_SMA", "Sell on the first close above the simple average of this many closes."),
        ("RSI exit", "EXIT_ON_RSI", "1: sell on RSI(2) above EXIT_RSI instead of the average."),
        ("RSI exit level", "EXIT_RSI", "The RSI(2) the RSI exit sells above."),
        ("Time stop", "MAX_HOLD_BARS", "Sessions after the fill session before the position is sold."),
        ("Rank by drop", "RANK_BY_DROP", "0: lowest RSI(2) first; 1: largest drop first."),
        ("Nominal target", "NOMINAL_TARGET_PCT", "Target = entry + this %, for the R column only."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume",
         "Pre-filter: the 20-day average of close × volume must be at least this."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
        ("Tick size", "cfg.tick_size", "A stop is rounded down to this increment."),
        ("Slippage", "cfg.slippage_bps", "Backtest cost per side, in basis points of the fill price."),
    )
    backtest_args = "--exit-mode revert --no-target --equal-alloc 10"

    # ---------- screen ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        ok, why = tradable_point_in_time(cfg, last)
        if not ok:
            return False, why
        if pd.isna(last.get("atr14")) or not last.get("atr14"):
            return False, "no ATR"
        if not setup_flags(last)[entry_setup()]:
            return False, "not oversold"
        return True, "passed"

    # ---------- gates ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        last = ctx.daily.iloc[-1]
        closes = ctx.daily["close"]
        e = ctx.extras
        e["rsi2"] = float(last["rsi2"]) if pd.notna(last.get("rsi2")) else None
        lower = last.get("sma20") - BB_SD * last.get("close_sd20")
        e["bb_lower"] = float(lower) if pd.notna(lower) else None
        e["down_streak"] = float(last["down_streak"]) if pd.notna(last.get("down_streak")) else None
        e["drop_pct"] = (float(closes.iloc[-1] / closes.iloc[-1 - DROP_BARS] - 1) * 100
                         if len(closes) > DROP_BARS else None)
        e["atr14"] = float(last["atr14"]) if pd.notna(last.get("atr14")) else None
        e["close"] = float(last["close"])

        self.apply_screen(ctx, result)
        # only the entry setup is recorded: a cached row rebuilds its result with every setup code as an
        # entry code (backtest._cached_result), so a recorded informational setup would buy
        active = entry_setup()
        flags = setup_flags(last)
        for code in self.setup_codes:
            result.setups[code] = bool(flags[code]) if code == active else False
        result.recompute_first_fail()
        return result

    def setup_quality(self, result: StrategyResult) -> float:
        return 1.0 if result.has_setup else 0.0

    def rank_score(self, extras: dict) -> float:
        """Higher wins a slot: the lowest RSI(2), or (RANK_BY_DROP) the largest drop."""
        if RANK_BY_DROP:
            d = extras.get("drop_pct")
            return -float(d) if d is not None else float("-inf")
        r = extras.get("rsi2")
        return 100.0 - float(r) if r is not None else float("-inf")

    # ---------- entry ----------

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        return result.has_setup

    def build_plans(self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no active setup")
        entry = ctx.extras.get("close") or float(ctx.close)
        atr14 = ctx.extras.get("atr14")
        if CATASTROPHE_ATR:
            if not atr14:
                return PlanChoice(None, None, "missing ATR for the catastrophe stop")
            stop = round_tick(entry - CATASTROPHE_ATR * atr14, cfg.tick_size, "down")
            if stop <= 0:
                stop = 0.0
        else:
            stop = 0.0
        target = entry * (1 + NOMINAL_TARGET_PCT / 100)
        plan = TradePlan(
            plan="MR", setup=result.active_setups[0], entry=entry, stop=stop, target=target,
            risk_per_share=entry - stop, reward_per_share=target - entry,
            r_multiple=(target - entry) / (entry - stop) if entry > stop else float("nan"),
            nearest_overhead_above_entry=None,
        )
        return PlanChoice(plan, None, "oversold above the 200-day")

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        if ENTRY_LIMIT_PCT:
            return {"order": "limit", "limit": round(plan.entry * (1 - ENTRY_LIMIT_PCT / 100), 4)}
        return {"order": "open"}

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
        r2 = ctx.extras.get("rsi2")
        label = "TRADE_HIGH_CONFIDENCE"
        reasons = [f"oversold above the 200-day ({plan.setup}" + (f", RSI(2) {r2:.1f})" if r2 is not None else ")")]
        before = label
        if regime_downgrade_active:
            label = DOWNGRADE_MAP[label]
            reasons.append("market-regime downgrade applied")
        # the slot ranking, read by the portfolio simulator as the signal's quality (--rank-by setup)
        return Decision(LABELS[before], LABELS[label], "; ".join(reasons),
                        risk_pct, plan.r_multiple, self.rank_score(ctx.extras))

    def report_extras(self, ctx: StockContext, result: StrategyResult, plan: TradePlan | None) -> dict:
        e = ctx.extras
        r = lambda v: round(float(v), 2) if v is not None and v == v else None
        return {k: r(e.get(k)) for k in self.extra_columns}

    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The oversold reading the trade was bought on."""
        e = sig.get("extras") or {}
        d = str(sig["date"])
        out: list[dict] = []
        if e.get("bb_lower"):
            out.append({"shape": "level", "bars": 20, "to": d, "price": float(e["bb_lower"]), "role": "support",
                        "label": f"lower Bollinger band {e['bb_lower']:.2f}"})
        bits = []
        if e.get("rsi2") is not None:
            bits.append(f"RSI(2) {e['rsi2']:.1f}")
        if e.get("down_streak") is not None:
            bits.append(f"{int(e['down_streak'])} lower closes")
        if e.get("drop_pct") is not None:
            bits.append(f"{e['drop_pct']:+.1f}% over {DROP_BARS} sessions")
        out.append({"shape": "note", "at": d, "price": e.get("close"),
                    "text": f"Mean reversion entry {d}: oversold above the 200-day ({', '.join(bits)}). "
                            f"Bought next session; sold on the first close above the {EXIT_SMA}-day average "
                            f"or after {MAX_HOLD_BARS} sessions."})
        return out
